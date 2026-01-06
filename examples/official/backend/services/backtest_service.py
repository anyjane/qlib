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
        "learning_rate": 0.2,
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
            "fit_start_time": train_start,
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
        logger.info(f"Annual Return (no cost): {results.get('annual_return_no_cost', 'N/A')}")
        logger.info(f"Sharpe Ratio (no cost): {results.get('sharpe_ratio_no_cost', 'N/A')}")
        logger.info(f"Annual Return (with cost): {results.get('annual_return_with_cost', 'N/A')}")
        logger.info(f"Sharpe Ratio (with cost): {results.get('sharpe_ratio_with_cost', 'N/A')}")
        logger.info("=" * 80)
        
        return results

    @staticmethod
    def extract_results(recorder) -> Dict:
        """
        从 recorder 中提取回测结果
        
        Args:
            recorder: Qlib recorder
            
        Returns:
            结果字典
        """
        results = {}
        
        try:
            # 加载组合分析结果
            port_analysis = recorder.load_object("portfolio_analysis/port_analysis_1day.pkl")
            
            # 提取无成本超额收益指标
            excess_no_cost = port_analysis.loc["excess_return_without_cost", "risk"]
            results["annual_return_no_cost"] = float(excess_no_cost.loc["annualized_return"])
            results["sharpe_ratio_no_cost"] = float(excess_no_cost.loc["information_ratio"])
            results["max_drawdown_no_cost"] = float(excess_no_cost.loc["max_drawdown"])
            
            # 提取有成本超额收益指标
            excess_with_cost = port_analysis.loc["excess_return_with_cost", "risk"]
            results["annual_return_with_cost"] = float(excess_with_cost.loc["annualized_return"])
            results["sharpe_ratio_with_cost"] = float(excess_with_cost.loc["information_ratio"])
            results["max_drawdown_with_cost"] = float(excess_with_cost.loc["max_drawdown"])
            
            logger.info("Results extracted successfully")
            
        except Exception as e:
            logger.error(f"Failed to extract results: {e}")
            results["error"] = str(e)
        
        return results
