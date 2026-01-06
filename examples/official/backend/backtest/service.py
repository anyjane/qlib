"""回测服务"""
from typing import Optional, List
import pandas as pd
import numpy as np
from pathlib import Path
from loguru import logger

import qlib
from qlib.constant import REG_CN
from qlib.data import D
from qlib.backtest import backtest
from qlib.backtest.signal import ModelSignal
from qlib.contrib.model.gbdt import LGBModel

from .data_loader import FeaturesDataLoader
from .trade_logger import TradeLogger
from .strategies import create_strategy
from .type_defs import (
    StrategyType,
    BacktestConfig,
    BacktestResult,
    BacktestMetrics,
    EquityPoint,
)


class BacktestService:
    """回测服务"""

    def __init__(self, data_dir: str):
        """
        初始化回测服务

        Args:
            data_dir: Qlib 数据目录
        """
        self.data_dir = Path(data_dir).expanduser()
        self.data_loader = FeaturesDataLoader(str(self.data_dir))
        self.trade_logger = TradeLogger()

        # Qlib 初始化状态
        self._qlib_initialized = False

    def _init_qlib(self):
        """初始化 Qlib"""
        if not self._qlib_initialized:
            qlib.init(provider_uri=str(self.data_dir), region=REG_CN)
            self._qlib_initialized = True
            logger.info(f"Qlib initialized with data_dir: {self.data_dir}")

    def run_backtest(
        self,
        config: BacktestConfig,
        task_id: str,
        experiment_name: str,
    ) -> BacktestResult:
        """
        执行回测

        Args:
            config: 回测配置
            task_id: 任务ID
            experiment_name: 实验名称

        Returns:
            回测结果
        """
        # 初始化 Qlib
        self._init_qlib()

        logger.info("=" * 80)
        logger.info(f"STARTING BACKTEST - {task_id}")
        logger.info("=" * 80)

        # 清空日志
        self.trade_logger.clear()

        # 加载数据
        self._load_data(config)

        # 创建模型
        model = self._create_model(config)

        # 创建数据集
        dataset = self._create_dataset(config)

        # 训练模型
        logger.info("Training model...")
        model.fit(dataset)
        logger.info("Model training completed")

        # 创建预测信号
        signal = ModelSignal(model, dataset)

        # 准备回测配置
        initial_cash = config.initial_capital * 10000  # 转换为元

        # 决定使用哪个策略
        if config.strategy_type == StrategyType.TOPK_REALLOCATION:
            # 使用自定义策略（需要继承自 Qlib 的 TopkDropoutStrategy）
            # 暂时使用标准策略，因为自定义策略需要更多适配
            logger.warning("TopkReallocationStrategy not fully integrated, using TopkDropoutStrategy")
            strategy_config = {
                "class": "TopkDropoutStrategy",
                "module_path": "qlib.contrib.strategy",
                "kwargs": {
                    "signal": signal,
                    "topk": config.topk,
                    "n_drop": config.n_drop,
                    "method_sell": config.method_sell.value,
                    "method_buy": config.method_buy.value,
                    "hold_thresh": config.hold_thresh,
                    "only_tradable": config.only_tradable,
                    "forbid_all_trade_at_limit": config.forbid_all_trade_at_limit,
                }
            }
        else:
            # 使用标准 TopkDropoutStrategy
            strategy_config = {
                "class": "TopkDropoutStrategy",
                "module_path": "qlib.contrib.strategy",
                "kwargs": {
                    "signal": signal,
                    "topk": config.topk,
                    "n_drop": config.n_drop,
                    "method_sell": config.method_sell.value,
                    "method_buy": config.method_buy.value,
                    "hold_thresh": config.hold_thresh,
                    "only_tradable": config.only_tradable,
                    "forbid_all_trade_at_limit": config.forbid_all_trade_at_limit,
                }
            }

        # 基准配置
        benchmark_map = {
            "all": "SH000300",
            "csi300": "SH000300",
            "csi500": "SH000905",
        }
        benchmark = benchmark_map.get(config.market, "SH000300")

        # Exchange 配置
        exchange_kwargs = {
            "freq": "day",
            "start_time": config.test_start,
            "end_time": config.test_end,
            "codes": config.market if config.market != "all" else None,
            "deal_price": config.deal_price,
            "limit_threshold": config.limit_threshold,
            "open_cost": config.buy_rate,
            "close_cost": config.sell_rate,
            "min_cost": config.min_commission,
            "trade_unit": 100,
        }

        # 执行回测
        logger.info("Running backtest...")
        try:
            # 使用 Qlib 标准回测函数
            portfolio_dict, indicator_dict = backtest(
                start_time=config.test_start,
                end_time=config.test_end,
                strategy=strategy_config,
                executor={
                    "class": "SimulatorExecutor",
                    "module_path": "qlib.backtest.executor",
                    "kwargs": {
                        "time_per_step": "day",
                        "generate_portfolio_metrics": True,
                    }
                },
                benchmark=benchmark,
                account=initial_cash,
                exchange_kwargs=exchange_kwargs,
                pos_type="Position",
            )

            # 提取结果
            metrics = self._extract_metrics(portfolio_dict, indicator_dict, config)
            equity_curve = self._extract_equity_curve(portfolio_dict)

            # 创建结果
            result = BacktestResult(
                task_id=task_id,
                experiment_name=experiment_name,
                config=config,
                metrics=metrics,
                trade_logs=self.trade_logger.get_trade_logs(),
                equity_curve=equity_curve,
            )

            logger.info("=" * 80)
            logger.info("BACKTEST COMPLETED")
            logger.info("=" * 80)
            logger.info(f"Total Return: {metrics.total_return:.2%}")
            logger.info(f"Annual Return (with cost): {metrics.annual_return_with_cost:.2%}")
            logger.info(f"Sharpe Ratio (with cost): {metrics.sharpe_ratio_with_cost:.4f}")
            logger.info(f"Max Drawdown (with cost): {metrics.max_drawdown_with_cost:.2%}")
            logger.info("=" * 80)

            return result

        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            raise

    def _load_data(self, config: BacktestConfig):
        """
        加载数据

        Args:
            config: 回测配置
        """
        logger.info("Loading data...")

        # 加载交易日历
        calendar = self.data_loader.load_calendar()

        # 加载股票池
        instruments = self.data_loader.load_instruments(config.market)
        logger.info(f"Loaded {len(instruments)} instruments for market: {config.market}")

        # 计算日期范围
        try:
            start_idx = calendar.index(config.test_start)
            end_idx = calendar.index(config.test_end)
            logger.info(f"Test period: {config.test_start} to {config.test_end}")
            logger.info(f"Trading days: {end_idx - start_idx + 1}")
        except ValueError as e:
            logger.error(f"Invalid date range: {e}")
            raise

    def _create_model(self, config: BacktestConfig):
        """
        创建模型

        Args:
            config: 回测配置

        Returns:
            模型实例
        """
        model = LGBModel(
            loss="mse",
            colsample_bytree=0.8879,
            learning_rate=0.2,
            subsample=0.8789,
            lambda_l1=205.6999,
            lambda_l2=580.9768,
            max_depth=8,
            num_leaves=210,
            num_threads=20,
        )
        return model

    def _create_dataset(self, config: BacktestConfig):
        """
        创建数据集

        Args:
            config: 回测配置

        Returns:
            数据集实例
        """
        from qlib.data.dataset import DatasetH
        from qlib.contrib.data.handler import Alpha158

        data_handler_config = {
            "start_time": config.train_start,
            "end_time": config.test_end,
            "fit_start_time": config.train_start,
            "fit_end_time": config.train_end,
            "instruments": config.market if config.market != "all" else None,
        }

        dataset_config = {
            "class": "DatasetH",
            "module_path": "qlib.data.dataset",
            "kwargs": {
                "handler": {
                    "class": "Alpha158",
                    "module_path": "qlib.contrib.data.handler",
                    "kwargs": data_handler_config,
                },
                "segments": {
                    "train": [config.train_start, config.train_end],
                    "valid": [config.test_start, config.test_end],
                    "test": [config.test_start, config.test_end],
                },
            },
        }

        from qlib.utils import init_instance_by_config
        dataset = init_instance_by_config(dataset_config)
        return dataset

    def _extract_metrics(
        self,
        portfolio_dict,
        indicator_dict,
        config: BacktestConfig
    ) -> BacktestMetrics:
        """
        提取回测指标

        Args:
            portfolio_dict: 组合指标字典
            indicator_dict: 指标字典
            config: 回测配置

        Returns:
            回测指标
        """
        initial_capital = config.initial_capital * 10000
        final_capital = initial_capital

        # 从 portfolio_dict 中提取指标
        # portfolio_dict 格式: {"1day": (report_df, positions_df)}
        for freq, (report_df, positions_df) in portfolio_dict.items():
            if "return" in report_df.columns and len(report_df) > 0:
                # 计算总收益率
                total_return = report_df["return"].iloc[-1]
                final_capital = initial_capital * (1 + total_return)

        # 从 indicator_dict 中提取指标
        annual_return_with_cost = 0.0
        sharpe_ratio_with_cost = 0.0
        max_drawdown_with_cost = 0.0

        if indicator_dict:
            # 提取收益率
            if "return" in indicator_dict:
                return_dict = indicator_dict["return"]
                if "1day" in return_dict:
                    return_value = return_dict["1day"]
                    if isinstance(return_value, (float, int)):
                        annual_return_with_cost = return_value

            # 提取夏普比率
            if "sharpe" in indicator_dict:
                sharpe_dict = indicator_dict["sharpe"]
                if "1day" in sharpe_dict:
                    sharpe_ratio_with_cost = sharpe_dict["1day"]

            # 提取最大回撤
            if "max_drawdown" in indicator_dict:
                drawdown_dict = indicator_dict["max_drawdown"]
                if "1day" in drawdown_dict:
                    max_drawdown_with_cost = drawdown_dict["1day"]

        # 计算交易统计
        summary = self.trade_logger.get_summary()

        # 计算交易费用
        total_commission = 0.0
        for log in self.trade_logger.get_trade_logs():
            for buy in log.buys:
                total_commission += buy.commission
            for sell in log.sells:
                total_commission += sell.commission

        total_return = (final_capital - initial_capital) / initial_capital

        metrics = BacktestMetrics(
            # 无成本指标（暂时使用有成本的值）
            annual_return_no_cost=annual_return_with_cost,
            sharpe_ratio_no_cost=sharpe_ratio_with_cost,
            max_drawdown_no_cost=max_drawdown_with_cost,

            # 有成本指标
            annual_return_with_cost=annual_return_with_cost,
            sharpe_ratio_with_cost=sharpe_ratio_with_cost,
            max_drawdown_with_cost=max_drawdown_with_cost,

            # 交易统计
            total_trades=summary["total_trades"],
            buy_trades=summary["total_buys"],
            sell_trades=summary["total_sells"],
            total_commission=total_commission,

            # 资金统计
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return=total_return,
        )

        return metrics

    def _extract_equity_curve(self, portfolio_dict) -> List[EquityPoint]:
        """
        提取资金曲线

        Args:
            portfolio_dict: 组合指标字典

        Returns:
            资金曲线点列表
        """
        equity_points = []

        # 从 portfolio_dict 中提取资金曲线
        # portfolio_dict 格式: {"1day": (report_df, positions_df)}
        for freq, (report_df, positions_df) in portfolio_dict.items():
            if "return" in report_df.columns and len(report_df) > 0:
                # 计算累计收益率
                cumulative_return = (1 + report_df["return"]).cumprod()

                for date, ret in cumulative_return.items():
                    equity_points.append(EquityPoint(
                        date=date.strftime("%Y-%m-%d"),
                        cash=0.0,  # 暂时不记录现金和持仓价值
                        stock_value=0.0,
                        total_value=ret * 10000,  # 标准化到10000初始资金
                    ))

        # 如果没有从回测结果中提取到数据，使用交易日志中的数据
        if not equity_points:
            equity_points = self.trade_logger.get_equity_curve()

        return equity_points
