"""
Qlib 股票预测服务

基于 predict_stocks.py 实现真实的 Qlib 预测逻辑
"""

import os
import sys
import pickle
import tempfile
from typing import List, Dict
from multiprocessing import Pool, cpu_count
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np

# 添加当前目录到 path
CUR_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CUR_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent.parent.parent  # 指向 /Users/samlty/code/qlib

# 添加项目路径
sys.path.insert(0, str(CUR_DIR))
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(PROJECT_DIR))

# 导入 Qlib 相关模块
from loguru import logger
import qlib
from qlib.constant import REG_CN
from qlib.utils import init_instance_by_config
from qlib.data import D

# 导入模型配置
# 直接定义 MODEL_CONFIG，避免导入路径问题
MODEL_CONFIG = {
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


class QlibPredictor:
    """Qlib 股票预测服务"""

    def __init__(
        self,
        provider_uri: str = "~/.qlib/tencent_data/qlib_data",
        experiment_name: str = "stock_prediction_api"
    ):
        """
        初始化预测器

        Args:
            provider_uri: Qlib 数据路径
            experiment_name: 实验名称
        """
        self.provider_uri = os.path.expanduser(provider_uri)
        self.experiment_name = experiment_name
        self._qlib_initialized = False

    def _init_qlib(self):
        """初始化 Qlib（延迟初始化）"""
        if not self._qlib_initialized:
            qlib.init(provider_uri=self.provider_uri, region=REG_CN)
            self._qlib_initialized = True
            logger.info(f"Qlib initialized with provider_uri: {self.provider_uri}")

    def determine_train_end_date(self, predict_date: str) -> str:
        """
        根据预测日期确定训练数据截止日期

        Args:
            predict_date: 预测日期 (YYYY-MM-DD)

        Returns:
            str: 训练截止日期
        """
        predict_dt = pd.to_datetime(predict_date)

        # 训练截止日期：预测日期的前一天
        train_end_dt = predict_dt - pd.Timedelta(days=1)

        # 查找这个日期之前的最后一个交易日
        calendar = D.calendar()

        train_end_date = None
        for date in reversed(calendar):
            if pd.to_datetime(date) < predict_dt:
                train_end_date = date
                break

        if train_end_date is None:
            raise ValueError(f"No trading day available before {predict_date}")

        logger.info(f"Training data will end at {train_end_date} (before prediction date {predict_date})")
        return train_end_date

    def train_model(
        self,
        stock_list: List[str],
        train_end_date: str
    ):
        """
        训练模型用于预测

        Args:
            stock_list: 股票代码列表
            train_end_date: 训练数据截止日期

        Returns:
            model: 训练好的模型
        """
        logger.info("Training model for prediction...")
        logger.info(f"Training data will end at: {train_end_date}")

        if MODEL_CONFIG is None:
            raise ValueError("MODEL_CONFIG is not available")

        # 创建数据集
        dataset_config = {
            "class": "DatasetH",
            "module_path": "qlib.data.dataset",
            "kwargs": {
                "handler": {
                    "class": "Alpha158",
                    "module_path": "qlib.contrib.data.handler",
                    "kwargs": {
                        "start_time": "2020-01-01",
                        "end_time": train_end_date,
                        "fit_start_time": "2020-01-01",
                        "fit_end_time": train_end_date,
                        "instruments": stock_list,
                    },
                },
                "instruments": stock_list,
                "segments": {
                    "train": ["2020-01-01", train_end_date],
                },
            },
        }

        dataset = init_instance_by_config(dataset_config)

        # 创建并训练模型
        model_config = MODEL_CONFIG.copy()
        model = init_instance_by_config(model_config)
        model.fit(dataset)

        logger.info(f"Model trained successfully using data until {train_end_date}")
        return model

    def predict_stocks_sequential(
        self,
        model,
        stock_list: List[str],
        predict_date: str
    ) -> pd.DataFrame:
        """
        顺序预测（单进程）

        Args:
            model: 训练好的模型
            stock_list: 股票代码列表
            predict_date: 预测日期

        Returns:
            pd.DataFrame: 预测结果
        """
        logger.info("Starting sequential prediction")
        logger.info(f"Total stocks: {len(stock_list)}, Date: {predict_date}")

        predict_dataset_config = {
            "class": "DatasetH",
            "module_path": "qlib.data.dataset",
            "kwargs": {
                "handler": {
                    "class": "Alpha158",
                    "module_path": "qlib.contrib.data.handler",
                    "kwargs": {
                        "start_time": predict_date,
                        "end_time": predict_date,
                        "instruments": stock_list,
                    },
                },
                "segments": {
                    "test": (predict_date, predict_date),
                },
            },
        }

        predict_dataset = init_instance_by_config(predict_dataset_config)

        # 执行预测
        predictions = model.predict(predict_dataset, segment='test')

        # 解析预测结果
        results = []
        for (date, stock_code), prediction in zip(predictions.index, predictions):
            results.append({
                'date': date,
                'stock_code': stock_code,
                'prediction': float(prediction)
            })

        result_df = pd.DataFrame(results)

        # 排序
        if not result_df.empty:
            result_df['date'] = pd.to_datetime(result_df['date'])
            result_df = result_df.sort_values(['date', 'stock_code'])

        logger.info(f"Sequential prediction completed: {len(result_df)} total predictions")
        return result_df

    def predict(
        self,
        predict_date: str,
        stock_codes: List[str],
        stock_names_map: Dict[str, str] = None
    ) -> Dict:
        """
        执行预测

        Args:
            predict_date: 预测日期 (YYYY-MM-DD)
            stock_codes: 股票代码列表
            stock_names_map: 股票代码到名称的映射

        Returns:
            Dict: {
                'predictions': [{'code': 'sh600000', 'score': 0.5234, 'name': '浦发银行'}],
                'execution_timestamp': '2025-01-05 14:30:00',
                'data_date': '2025-01-05',
                'total_count': 500,
                'success_count': 500
            }
        """
        self._init_qlib()

        execution_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        logger.info(f"Starting prediction for date: {predict_date}")
        logger.info(f"Stock codes: {len(stock_codes)} stocks")

        try:
            # 1. 确定训练截止日期
            train_end_date = self.determine_train_end_date(predict_date)

            # 2. 训练模型
            model = self.train_model(stock_codes, train_end_date)

            # 3. 执行预测（使用单进程）
            result_df = self.predict_stocks_sequential(model, stock_codes, predict_date)

            # 4. 转换预测结果
            predictions = []
            outliers = []

            for _, row in result_df.iterrows():
                prediction_value = float(row['prediction'])
                stock_code = row['stock_code']

                # 获取股票名称
                stock_name = stock_names_map.get(stock_code, 'Unknown') if stock_names_map else 'Unknown'

                # 检测异常值
                if abs(prediction_value) > 0.99:
                    outliers.append(stock_code)
                    logger.warning(f"Detected outlier for {stock_code}: {prediction_value}")

                predictions.append({
                    'code': stock_code,
                    'score': prediction_value,
                    'name': stock_name
                })

            # 5. 返回结果
            result = {
                'predictions': predictions,
                'execution_timestamp': execution_timestamp,
                'data_date': predict_date,
                'total_count': len(stock_codes),
                'success_count': len(predictions),
                'outliers': outliers
            }

            logger.info(f"Prediction completed: {len(predictions)} predictions")
            if outliers:
                logger.warning(f"Found {len(outliers)} outliers: {outliers}")

            return result

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise

    def detect_outliers(self, predictions: List[Dict]) -> List[str]:
        """
        检测异常值

        Args:
            predictions: 预测结果列表

        Returns:
            List[str]: 异常值的股票代码列表
        """
        outliers = []
        for pred in predictions:
            if abs(pred['score']) > 0.99:
                outliers.append(pred['code'])

        return outliers
