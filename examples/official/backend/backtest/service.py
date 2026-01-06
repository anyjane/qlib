"""回测服务"""
from typing import Optional
import pandas as pd
import numpy as np
from pathlib import Path
from loguru import logger

import qlib
from qlib.constant import REG_CN
from qlib.data import D
from qlib.backtest.executor import Executor
from qlib.backtest.decision import Order
from qlib.backtest.signal import ModelSignal
from qlib.contrib.model.gbdt import LGBModel

from .data_loader import FeaturesDataLoader
from .trade_logger import TradeLogger
from .strategies import create_strategy, StrategyType
from .types import (
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

        # 初始化策略
        strategy = create_strategy(
            strategy_type=config.strategy_type,
            topk=config.topk,
            n_drop=config.n_drop,
            method_sell=config.method_sell.value,
            method_buy=config.method_buy.value,
            hold_thresh=config.hold_thresh,
            only_tradable=config.only_tradable,
            forbid_all_trade_at_limit=config.forbid_all_trade_at_limit,
            verbose=config.verbose,
            max_reallocation_rounds=config.max_reallocation_rounds,
            log_prediction_details=config.log_prediction_details,
        )

        # 创建模型（用于生成预测信号）
        model = self._create_model(config)

        # 创建数据集
        dataset = self._create_dataset(config)

        # 训练模型
        logger.info("Training model...")
        model.fit(dataset)
        logger.info("Model training completed")

        # 创建预测信号
        signal = ModelSignal(model, dataset)

        # 创建 Exchange
        from qlib.backtest.exchange import Exchange

        exchange = Exchange(
            freq="day",
            start_time=config.train_start,
            end_time=config.test_end,
            codes=config.market if config.market != "all" else None,
            deal_price=config.deal_price,
            limit_threshold=config.limit_threshold,
            open_cost=config.buy_rate,
            close_cost=config.sell_rate,
            min_cost=config.min_commission,
            trade_unit=100,
        )

        # 设置策略依赖
        from qlib.backtest.position import Position
        from qlib.backtest.calendar import Calendar

        calendar = Calendar(
            freq="day",
            start_time=config.test_start,
            end_time=config.test_end,
        )

        # 创建初始持仓
        initial_cash = config.initial_capital * 10000  # 转换为元

        # 创建 Position 对象
        position = Position(cash=initial_cash)

        # 设置策略
        strategy.setup(
            exchange=exchange,
            calendar=calendar,
            position=position,
            signal=signal,
        )

        # 创建 Executor
        executor = Executor(
            time_per_step="day",
            generate_executor_fn=lambda x: strategy,
            exchange=exchange,
        )

        # 运行回测
        logger.info("Running backtest...")
        try:
            portfolio = executor.run()

            # 提取结果
            metrics = self._extract_metrics(portfolio, config)
            equity_curve = self._extract_equity_curve(portfolio)

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

    def _extract_metrics(self, portfolio, config: BacktestConfig) -> BacktestMetrics:
        """
        提取回测指标

        Args:
            portfolio: 组合对象
            config: 回测配置

        Returns:
            回测指标
        """
        # 这里需要从 portfolio 提取实际指标
        # 暂时使用占位值
        initial_capital = config.initial_capital * 10000

        # 获取最终资金
        final_value = portfolio.get_total_value() if hasattr(portfolio, 'get_total_value') else initial_capital

        total_return = (final_value - initial_capital) / initial_capital

        # 计算交易统计
        summary = self.trade_logger.get_summary()

        # 计算交易费用
        total_commission = 0.0
        for log in self.trade_logger.get_trade_logs():
            for buy in log.buys:
                total_commission += buy.commission
            for sell in log.sells:
                total_commission += sell.commission

        metrics = BacktestMetrics(
            # 无成本指标（暂用占位值）
            annual_return_no_cost=total_return,
            sharpe_ratio_no_cost=1.0,
            max_drawdown_no_cost=0.1,

            # 有成本指标
            annual_return_with_cost=total_return,
            sharpe_ratio_with_cost=0.9,
            max_drawdown_with_cost=0.15,

            # 交易统计
            total_trades=summary["total_trades"],
            buy_trades=summary["total_buys"],
            sell_trades=summary["total_sells"],
            total_commission=total_commission,

            # 资金统计
            initial_capital=initial_capital,
            final_capital=final_value,
            total_return=total_return,
        )

        return metrics

    def _extract_equity_curve(self, portfolio) -> List[EquityPoint]:
        """
        提取资金曲线

        Args:
            portfolio: 组合对象

        Returns:
            资金曲线点列表
        """
        # 返回交易日志中的资金曲线
        return self.trade_logger.get_equity_curve()
