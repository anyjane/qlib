"""Backtest Service - 量化回测执行服务

基于 TencentDataSource/workflow.py 的回测逻辑，在进程池中执行。
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

import pandas as pd
import yaml

import qlib
from qlib.constant import REG_CN
from qlib.utils import init_instance_by_config, flatten_dict
from qlib.workflow import R
from qlib.workflow.record_temp import SignalRecord, PortAnaRecord, SigAnaRecord
from loguru import logger


# 默认配置
DEFAULT_MODEL_CONFIG = {
    "class": "LGBModel",
    "module_path": "qlib.contrib.model.gbdt",
    "kwargs": {
        "loss": "mse",
        "colsample_bytree": 0.8879,
        "learning_rate": 0.05,  # Reduced from 0.2 to 0.05 for better stability
        "subsample": 0.8789,
        "lambda_l1": 205.6999,
        "lambda_l2": 580.9768,
        "max_depth": 8,
        "num_leaves": 210,
        "num_threads": 20,
    },
}

DEFAULT_PORT_ANALYSIS_CONFIG = {
    "strategy": {
        "class": "TopkDropoutStrategy",
        "module_path": "qlib.contrib.strategy",
        "kwargs": {
            "signal": "<PRED>",
            "topk": 50,
            "n_drop": 5,
        },
    },
    "backtest": {
        "account": 100000000,
        "exchange_kwargs": {
            "limit_threshold": 0.095,
            "deal_price": "close",
            "open_cost": 0.0005,
            "close_cost": 0.0015,
            "min_cost": 5,
        },
    },
}


class BacktestService:
    """回测服务"""

    @staticmethod
    def create_workflow_config(
        provider_uri: str,
        market: str,
        train_start: str,
        train_end: str,
        test_start: str,
        test_end: str,
    ) -> Dict:
        """
        创建工作流配置
        
        Args:
            provider_uri: Qlib 数据目录
            market: 市场（all, csi300, csi500）
            train_start: 训练开始日期
            train_end: 训练结束日期
            test_start: 测试开始日期
            test_end: 测试结束日期
            
        Returns:
            工作流配置字典
        """
        logger.info(f"Creating workflow config: market={market}")
        
        # 市场对应的基准指数
        benchmark_map = {
            "all": "SH000300",  # 使用沪深300作为全市场基准
            "csi300": "SH000300",
            "csi500": "SH000905",
        }
        benchmark = benchmark_map.get(market, "SH000300")
        
        # 数据处理器配置
        data_handler_config = {
            "start_time": train_start,
            "end_time": test_end,
            "fit_end_time": train_end,
            "instruments": market if market != "all" else None,
        }
        
        # 如果是 all 市场，从元数据目录获取股票列表
        if market == "all":
            metadata_dir = Path(provider_uri).expanduser() / "metadata"
            if metadata_dir.exists():
                instruments = [f.stem for f in metadata_dir.glob("*.json")]
                data_handler_config["instruments"] = instruments
                logger.info(f"Using {len(instruments)} instruments from metadata")
            else:
                # 降级到 csi300
                data_handler_config["instruments"] = "csi300"
                logger.warning("No metadata found, falling back to csi300")
        
        # 数据集配置
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
                    "train": [train_start, train_end],
                    "valid": [test_start, test_end],
                    "test": [test_start, test_end],
                },
            },
        }
        
        # 组合分析配置
        port_analysis_config = DEFAULT_PORT_ANALYSIS_CONFIG.copy()
        port_analysis_config["backtest"]["start_time"] = test_start
        port_analysis_config["backtest"]["end_time"] = test_end
        port_analysis_config["backtest"]["benchmark"] = benchmark
        
        # 记录配置
        record_config = [
            {
                "class": "SignalRecord",
                "module_path": "qlib.workflow.record_temp",
                "kwargs": {
                    "model": "<MODEL>",
                    "dataset": "<DATASET>",
                },
            },
            {
                "class": "SigAnaRecord",
                "module_path": "qlib.workflow.record_temp",
                "kwargs": {
                    "ana_long_short": False,
                    "ann_scaler": 252,
                },
            },
            {
                "class": "PortAnaRecord",
                "module_path": "qlib.workflow.record_temp",
                "kwargs": {
                    "config": port_analysis_config,
                },
            },
        ]
        
        return {
            "qlib_init": {
                "provider_uri": provider_uri,
                "region": REG_CN,
            },
            "market": market,
            "benchmark": benchmark,
            "port_analysis_config": port_analysis_config,
            "task": {
                "model": DEFAULT_MODEL_CONFIG,
                "dataset": dataset_config,
                "record": record_config,
            },
        }

    @staticmethod
    def run_backtest(
        provider_uri: str,
        market: str,
        train_start: str,
        train_end: str,
        test_start: str,
        test_end: str,
        experiment_name: str,
    ) -> Dict:
        """
        执行回测
        
        Args:
            provider_uri: Qlib 数据目录
            market: 市场
            train_start: 训练开始日期
            train_end: 训练结束日期
            test_start: 测试开始日期
            test_end: 测试结束日期
            experiment_name: 实验名称
            
        Returns:
            回测结果字典
        """
        logger.info("=" * 80)
        logger.info("STARTING BACKTEST")
        logger.info("=" * 80)
        logger.info(f"Provider URI: {provider_uri}")
        logger.info(f"Market: {market}")
        logger.info(f"Train period: {train_start} to {train_end}")
        logger.info(f"Test period: {test_start} to {test_end}")
        logger.info(f"Experiment: {experiment_name}")
        logger.info("=" * 80)
        
        # 初始化 Qlib
        logger.info("Initializing Qlib...")
        qlib.init(provider_uri=provider_uri, region=REG_CN)
        logger.info("Qlib initialized")
        
        # 获取配置
        config = BacktestService.create_workflow_config(
            provider_uri=provider_uri,
            market=market,
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
        )
        
        # 创建模型
        logger.info("Creating model...")
        model = init_instance_by_config(config["task"]["model"])
        logger.info(f"Model created: {model.__class__.__name__}")
        
        # 创建数据集
        logger.info("Creating dataset...")
        dataset = init_instance_by_config(config["task"]["dataset"])
        logger.info("Dataset created")
        
        # 运行实验
        logger.info(f"Starting experiment: {experiment_name}")
        with R.start(experiment_name=experiment_name):
            # 记录参数
            R.log_params(**flatten_dict(config["task"]))
            
            # 训练模型
            logger.info("Training model...")
            model.fit(dataset)
            logger.info("Model training completed")
            
            # 保存模型
            R.save_objects(**{"params.pkl": model})
            
            # 生成预测
            logger.info("Generating predictions...")
            recorder = R.get_recorder()
            sr = SignalRecord(model, dataset, recorder)
            sr.generate()
            logger.info("Predictions generated")
            
            # 信号分析
            logger.info("Performing signal analysis...")
            sar = SigAnaRecord(recorder)
            sar.generate()
            logger.info("Signal analysis completed")
            
            # 回测和组合分析
            logger.info("Running backtest and portfolio analysis...")
            par = PortAnaRecord(recorder, config["port_analysis_config"], "day")
            par.generate()
            logger.info("Portfolio analysis completed")
            
            # 提取结果
            logger.info("Extracting results...")
            results = BacktestService.extract_results(recorder)
        
        logger.info("=" * 80)
        logger.info("BACKTEST COMPLETED")
        logger.info("=" * 80)
        
        metrics = results.get("metrics", {})
        logger.info(f"Annual Return (no cost): {metrics.get('annual_return_no_cost', 'N/A')}")
        logger.info(f"Sharpe Ratio (no cost): {metrics.get('sharpe_ratio_no_cost', 'N/A')}")
        logger.info(f"Annual Return (with cost): {metrics.get('annual_return_with_cost', 'N/A')}")
        logger.info(f"Sharpe Ratio (with cost): {metrics.get('sharpe_ratio_with_cost', 'N/A')}")
        logger.info("=" * 80)
        
        return results

    @staticmethod
    def extract_results(recorder) -> Dict:
        """
        从 recorder 中提取回测结果 (包含详细交易记录)
        
        Args:
            recorder: Qlib recorder
            
        Returns:
            结果字典
        """
        results = {"metrics": {}, "trade_logs": []}
        
        try:
            # 1. 加载组合分析结果 (Metrics)
            port_analysis = recorder.load_object("portfolio_analysis/port_analysis_1day.pkl")
            
            # 提取无成本超额收益指标
            excess_no_cost = port_analysis.loc["excess_return_without_cost", "risk"]
            results["metrics"]["annual_return_no_cost"] = float(excess_no_cost.loc["annualized_return"])
            results["metrics"]["sharpe_ratio_no_cost"] = float(excess_no_cost.loc["information_ratio"])
            results["metrics"]["max_drawdown_no_cost"] = float(excess_no_cost.loc["max_drawdown"])
            
            # 提取有成本超额收益指标
            excess_with_cost = port_analysis.loc["excess_return_with_cost", "risk"]
            results["metrics"]["annual_return_with_cost"] = float(excess_with_cost.loc["annualized_return"])
            results["metrics"]["sharpe_ratio_with_cost"] = float(excess_with_cost.loc["information_ratio"])
            results["metrics"]["max_drawdown_with_cost"] = float(excess_with_cost.loc["max_drawdown"])
            
            # 2. 加载详细报告和持仓 (Trade Logs)
            report_df = recorder.load_object("portfolio_analysis/report_normal_1day.pkl")
            positions_dict = recorder.load_object("portfolio_analysis/positions_normal_1day.pkl")
            pred_df = recorder.load_object("pred.pkl")
            
            # 确保 pred_df 索引正确 (datetime, instrument)
            if not isinstance(pred_df.index, pd.MultiIndex):
                # 尝试修复索引，如果可能
                pass

            # 初始化变量
            trade_logs = []
            prev_positions = {}
            total_trades = 0
            total_commission = 0.0
            
            # 遍历每一个交易日
            for date in report_df.index:
                date_str = date.strftime("%Y-%m-%d")
                
                # 获取当日账户信息
                account_info = report_df.loc[date]
                total_value = float(account_info["account"])
                cash = float(account_info["cash"]) if "cash" in account_info else 0.0
                # report_df 通常包含: account, return, turnover, cost, risk
                # Qlib 的 report_normal_1day.pkl 结构可能只有 account, return, turnover, cost, risk
                # cash 需要通过 account - market_value 计算，或者从 positions 中获取 cash
                
                # 获取当日持仓
                current_positions = positions_dict.get(date, {})
                # positions_dict values can be Qlib Position objects or dicts
                
                current_cash = 0.0
                current_stock_positions = {}
                
                if hasattr(current_positions, "position") and isinstance(current_positions.position, dict):
                    # It's likely a Qlib Position object with a .position dict
                    raw_pos = current_positions.position
                    current_cash = raw_pos.get("cash", 0.0)
                    
                    # Robustly extract stock positions
                    current_stock_positions = {}
                    for k, v in raw_pos.items():
                        if k == "cash": 
                            continue
                        if isinstance(v, (int, float)):
                            if v > 0:
                                current_stock_positions[k] = v
                        elif isinstance(v, dict) and "amount" in v:
                            # Handle nested position info if present
                            amt = v.get("amount", 0)
                            if isinstance(amt, (int, float)) and amt > 0:
                                current_stock_positions[k] = amt
                        else:
                            # logging unexpected types for debugging but avoiding crash
                            # logger.warning(f"Unexpected position value for {k}: {type(v)}")
                            pass

                elif isinstance(current_positions, dict):
                    # It's a plain dictionary
                    current_cash = current_positions.get("cash", 0.0)
                    
                    current_stock_positions = {}
                    for k, v in current_positions.items():
                        if k == "cash":
                            continue
                        if isinstance(v, (int, float)) and v > 0:
                            current_stock_positions[k] = v
                else:
                    # Try accessing standard Qlib Position methods if .position is not available/public
                    # But typically .position is accessible or we might need inspect
                    try:
                        # Fallback: check if we can convert to dict
                        raw_pos = dict(current_positions)
                        current_cash = raw_pos.get("cash", 0.0)
                        
                        current_stock_positions = {}
                        for k, v in raw_pos.items():
                            if k == "cash":
                                continue
                            if isinstance(v, (int, float)) and v > 0:
                                current_stock_positions[k] = v
                    except:
                        logger.warning(f"Unknown position format for date {date}: {type(current_positions)}")
                        continue
                
                # 获取当日预测分 (Top predictions)
                top_predictions = []
                try:
                    if isinstance(pred_df.index, pd.MultiIndex):
                        if date in pred_df.index.get_level_values(0):
                            daily_preds = pred_df.loc[date]
                            # daily_preds 是 Series 或 DataFrame
                            if isinstance(daily_preds, pd.DataFrame):
                                daily_preds = daily_preds.iloc[:, 0]
                            
                            # 排序并取 Top 20
                            sorted_preds = daily_preds.sort_values(ascending=False).head(20)
                            for code, score in sorted_preds.items():
                                top_predictions.append({
                                    "code": code,
                                    "prediction_score": float(score)  # Ensure python float
                                })
                except Exception as e:
                    logger.warning(f"Failed to get predictions for {date}: {e}")

                # 获取当日价格数据 (用于估算成交价)
                prices = {}
                try:
                    # 使用 Qlib 数据接口获取当日收盘价
                    # 注意: extract_results 是静态方法，且要在 recorder 上下文中
                    # 这里尝试使用 D.features 获取价格，字段为 $close
                    # 需确保 imported D
                    from qlib.data import D
                    # query for this date only
                    price_df = D.features(
                        instruments=list(set(list(prev_positions.keys()) + list(current_stock_positions.keys()))),
                        fields=["$close"],
                        start_time=date_str,
                        end_time=date_str
                    )
                    if not price_df.empty:
                        # price_df index is (instrument, datetime)
                        for (instrument, _), row in price_df.iterrows():
                            prices[instrument] = float(row["$close"])  # Ensure python float
                except Exception as e:
                    logger.warning(f"Failed to fetch prices for {date_str}: {e}")

                # 初始化交易列表
                buys = []
                sells = []

                # 检查卖出 (昨日有，今日无 或 减少)
                for code, prev_amount in prev_positions.items():
                    curr_amount = current_stock_positions.get(code, 0)
                    if curr_amount < prev_amount:
                        amount_diff = prev_amount - curr_amount
                        estimated_price = prices.get(code, 0.0)
                        
                        sells.append({
                            "code": code,
                            "amount": amount_diff,
                            "price": estimated_price,
                            "value": amount_diff * estimated_price,
                            "commission": 0.0, # 简化的手续费计算
                            "actual_received": amount_diff * estimated_price  # 简化的实际到账
                        })
                        total_trades += 1
                
                # 检查买入 (今日有，昨日无 或 增加)
                for code, curr_amount in current_stock_positions.items():
                    prev_amount = prev_positions.get(code, 0)
                    if curr_amount > prev_amount:
                        amount_diff = curr_amount - prev_amount
                        estimated_price = prices.get(code, 0.0)
                        
                        buys.append({
                            "code": code,
                            "amount": amount_diff,
                            "price": estimated_price,
                            "value": amount_diff * estimated_price,
                            "commission": 0.0
                        })
                        total_trades += 1
                
                # 构建持仓列表 (带预测分)
                holdings_list = []
                for code, amount in current_stock_positions.items():
                    score = 0.0
                    # 尝试查找分数
                    for p in top_predictions:
                        if p["code"] == code:
                            score = p["prediction_score"]
                            break
                    
                    holdings_list.append({
                        "code": code,
                        "amount": amount,
                        "prediction_score": score
                    })

                # 记录日志
                trade_log = {
                    "trade_date": date_str,
                    "cash_before": 0.0, # 难以获取期初现金，暂略
                    "total_value": total_value,
                    "top_stocks": top_predictions,
                    "current_positions": holdings_list,
                    "buys": buys,
                    "sells": sells
                }
                trade_logs.append(trade_log)
                
                # 更新昨日持仓
                prev_positions = current_stock_positions.copy()
            
            results["trade_logs"] = trade_logs
            
            # 补充 Metrics
            if trade_logs:
                last_log = trade_logs[-1]
                results["metrics"]["final_capital"] = last_log["total_value"]
            else:
                results["metrics"]["final_capital"] = 0.0
                
            results["metrics"]["total_trades"] = total_trades
            results["metrics"]["total_commission"] = total_commission # 需要更精确的计算
            
            logger.info(f"Results extracted successfully with {len(trade_logs)} trade logs")
            
        except Exception as e:
            logger.error(f"Failed to extract results: {e}")
            import traceback
            logger.error(traceback.format_exc())
            results["error"] = str(e)
            # 确保至少有基本结构
            if "metrics" not in results: results["metrics"] = {}
            if "trade_logs" not in results: results["trade_logs"] = []
        
        return results
