# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Stock prediction function with support for multiple dates and multi-processing
"""

import os
import sys
import pickle
import tempfile
from typing import List, Dict
from functools import partial
from multiprocessing import Pool, cpu_count
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
import fire

# Add current directory to path
CUR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CUR_DIR))
sys.path.insert(0, str(CUR_DIR.parent))

from loguru import logger
import qlib
from qlib.constant import REG_CN
from qlib.utils import init_instance_by_config
from qlib.data import D

# 配置日志输出
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f"pred_{timestamp}.log"

# 添加文件处理器
logger.add(
    log_file,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="100 MB",
    retention="30 days",
    compression="zip",
    encoding="utf-8",
)

# 添加控制台处理器
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True,
)

logger.info(f"日志配置完成，日志文件: {log_file}")

# Import configuration
from config import MODEL_CONFIG


def load_stock_list_from_csv(csv_path: str = "a500.csv") -> List[str]:
    """
    从 a500.csv 读取股票代码列表

    Returns:
        List[str]: 标准化后的股票代码列表（sh600000, sz000001 格式）
    """
    logger.info(f"Loading stock list from {csv_path}")

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)
    stock_codes = df['成份券代码Constituent Code'].tolist()

    # 标准化股票代码格式
    # Qlib 需要 sh600000 或 sz000001 格式
    standardized_codes = []
    for code in stock_codes:
        code_str = str(code).zfill(6)  # 补零到6位
        if code_str.startswith('6'):
            # Shanghai stocks (main board starts with 60, STAR market starts with 688)
            standardized_codes.append(f'sh{code_str}')
        elif code_str.startswith('00') or code_str.startswith('30'):
            # Shenzhen stocks (main board 00, SME 002, ChiNext 30)
            standardized_codes.append(f'sz{code_str}')
        else:
            logger.warning(f"Unknown stock code format: {code_str}")
            continue

    logger.info(f"Loaded {len(standardized_codes)} stocks from {csv_path}")
    return standardized_codes


def load_stock_names_map(csv_path: str = "a500.csv") -> Dict[str, str]:
    """
    从 a500.csv 加载股票代码到名称的映射

    Returns:
        Dict[str, str]: {stock_code: stock_name}
    """
    logger.info(f"Loading stock names map from {csv_path}")

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    stock_names_map = {}
    for _, row in df.iterrows():
        code = str(row['成份券代码Constituent Code']).zfill(6)
        name = row['成份券名称Constituent Name']

        # 标准化代码格式
        if code.startswith('60'):
            standardized_code = f'sh{code}'
        elif code.startswith('00') or code.startswith('30'):
            standardized_code = f'sz{code}'
        else:
            continue

        stock_names_map[standardized_code] = name

    logger.info(f"Loaded {len(stock_names_map)} stock names from {csv_path}")
    return stock_names_map


def parse_prediction_dates(
    provider_uri: str,
    dates: str = None,
    start_date: str = None,
    end_date: str = None,
    last_n_days: int = None
) -> List[str]:
    """
    解析日期参数，返回日期列表

    支持四种模式：
    1. 单个日期：dates="2024-12-31"
    2. 多个日期：dates="2024-12-30,2024-12-31,2025-01-02"
    3. 日期段：start_date="2024-12-01", end_date="2024-12-31"
    4. 最近N天：last_n_days=5

    Returns:
        List[str]: 日期列表，格式为 'YYYY-MM-DD'
    """
    # 初始化 qlib 以获取 calendar
    qlib.init(provider_uri=provider_uri, region=REG_CN)
    calendar = D.calendar()  # 交易日期列表

    if dates is not None:
        # 模式1/2：单个或多个日期
        date_list = dates.split(',')
        date_list = [d.strip() for d in date_list]

        # 验证日期是否在 calendar 中
        valid_dates = []
        for d in date_list:
            if d in calendar:
                valid_dates.append(d)
            else:
                logger.warning(f"Date {d} is not a trading day, skipping")

        if not valid_dates:
            raise ValueError(f"No valid dates provided. Dates must be trading days in calendar.")

        logger.info(f"Predicting for {len(valid_dates)} specific dates: {valid_dates}")
        return sorted(valid_dates)

    elif start_date is not None and end_date is not None:
        # 模式3：日期段
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        # 获取日期段内的所有交易日
        date_list = [
            d for d in calendar
            if start_dt <= pd.to_datetime(d) <= end_dt
        ]

        if not date_list:
            raise ValueError(f"No trading days in date range {start_date} to {end_date}")

        logger.info(f"Predicting for date range {start_date} to {end_date}: {len(date_list)} days")
        return date_list

    elif last_n_days is not None:
        # 模式4：最近N个交易日
        if last_n_days <= 0:
            raise ValueError("last_n_days must be positive")

        date_list = calendar[-last_n_days:]

        logger.info(f"Predicting for last {last_n_days} trading days")
        return date_list

    else:
        # 默认：最后一天
        logger.info("No date specified, using last trading day")
        return [calendar[-1]]


def determine_train_end_date(predict_dates: List[str], provider_uri: str) -> str:
    """
    根据预测日期列表确定训练数据截止日期

    关键：训练数据应该早于最早的预测日期
    """
    earliest_predict_date = min(predict_dates)
    earliest_dt = pd.to_datetime(earliest_predict_date)

    # 训练截止日期：最早预测日期的前一天
    train_end_dt = earliest_dt - pd.Timedelta(days=1)

    # 查找这个日期之前的最后一个交易日
    calendar = D.calendar()

    train_end_date = None
    for date in reversed(calendar):
        if pd.to_datetime(date) < earliest_dt:
            train_end_date = date
            break

    if train_end_date is None:
        raise ValueError(f"No trading day available before {earliest_predict_date}")

    logger.info(f"Training data will end at {train_end_date} (before earliest prediction date {earliest_predict_date})")
    return train_end_date


def train_model_for_prediction(
    provider_uri: str,
    stock_list: List[str],
    train_end_date: str
):
    """
    训练模型用于预测

    关键点：
    1. 训练数据不包含任何预测日期
    2. 使用所有预测股票的历史数据训练
    3. 训练截止到 train_end_date（早于最早的预测日期）
    """
    logger.info("Training model for prediction...")
    logger.info(f"Training data will end at: {train_end_date}")

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
                    "end_time": train_end_date,  # 关键：不包含任何预测日
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


def split_into_batches(items: List, num_batches: int) -> List[List]:
    """
    将列表分成多个批次

    确保每个批次尽可能均衡
    """
    if not items:
        return []

    batch_size = len(items) // num_batches
    if batch_size == 0:
        batch_size = 1

    batches = []
    for i in range(num_batches):
        start_idx = i * batch_size
        end_idx = (i + 1) * batch_size if i < num_batches - 1 else len(items)
        batch = items[start_idx:end_idx]
        if batch:
            batches.append(batch)

    return batches


def get_optimal_num_processes(num_processes: int = 8) -> int:
    """
    获取最优进程数

    考虑因素：
    1. 用户指定的进程数
    2. CPU 核心数
    3. 内存限制
    """
    if num_processes == 'auto':
        num_processes = cpu_count()

    cpu_count_actual = cpu_count()

    # 不超过 CPU 核心数
    if num_processes > cpu_count_actual:
        logger.warning(
            f"Requested {num_processes} processes but only {cpu_count_actual} CPUs available. "
            f"Using {cpu_count_actual} processes."
        )
        return cpu_count_actual

    # 至少使用 1 个进程
    if num_processes < 1:
        logger.warning(f"num_processes must be >= 1. Using 1 process.")
        return 1

    return num_processes


def _predict_batch(args):
    """
    进程内执行的预测函数（用于多进程）

    注意：不能在进程间传递 qlib 对象或 dataset
    因此需要在每个进程中重新初始化
    """
    stock_batch, predict_dates, provider_uri, model_pickle_path = args

    try:
        # 在子进程中重新初始化 qlib
        import qlib as qlib_child
        from qlib.constant import REG_CN as REG_CN_CHILD
        from qlib.utils import init_instance_by_config as init_instance

        qlib_child.init(provider_uri=provider_uri, region=REG_CN_CHILD)

        # 加载模型（从 pickle 文件）
        with open(model_pickle_path, 'rb') as f:
            model = pickle.load(f)

        # 为批次中的股票创建 dataset
        min_date = min(predict_dates)
        max_date = max(predict_dates)

        predict_dataset_config = {
            "class": "DatasetH",
            "module_path": "qlib.data.dataset",
            "kwargs": {
                "handler": {
                    "class": "Alpha158",
                    "module_path": "qlib.contrib.data.handler",
                    "kwargs": {
                        "start_time": min_date,
                        "end_time": max_date,
                        "fit_start_time": min_date,
                        "fit_end_time": max_date,
                        "instruments": stock_batch,
                    },
                },
                "segments": {
                    "test": (min_date, max_date),
                },
            },
        }

        predict_dataset = init_instance(predict_dataset_config)

        # Debug: log the type of predict_dataset
        logger.debug(f"predict_dataset type: {type(predict_dataset)}")
        logger.debug(f"predict_dataset: {predict_dataset}")

        # 直接使用 dataset 进行预测（不要先 prepare）
        # LGBModel.predict() 方法会自己调用 dataset.prepare()
        logger.debug(f"model type: {type(model)}")
        logger.debug(f"Calling model.predict()...")
        predictions = model.predict(predict_dataset, segment='test')
        logger.debug(f"predictions type: {type(predictions)}, shape: {predictions.shape if hasattr(predictions, 'shape') else 'N/A'}")

        # 解析预测结果
        results = []
        for (date, stock_code), prediction in zip(predictions.index, predictions):
            results.append({
                'date': date,
                'stock_code': stock_code,
                'prediction': prediction
            })

        return results

    except Exception as e:
        import traceback
        logger.error(f"Error in prediction batch: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []


def predict_stocks_parallel(
    model,
    stock_list: List[str],
    predict_dates: List[str],
    provider_uri: str,
    num_processes: int = 8
) -> pd.DataFrame:
    """
    多进程预测

    策略：
    1. 将股票列表分成多个批次
    2. 每个进程处理一个批次的股票
    3. 合并所有结果

    关键点：
    - 模型需要序列化到文件
    - 每个进程独立初始化 qlib
    - 避免共享资源冲突
    """
    logger.info(f"Starting parallel prediction with {num_processes} processes")
    logger.info(f"Total stocks: {len(stock_list)}, Total dates: {len(predict_dates)}")

    # 1. 保存模型到临时文件（序列化）
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pkl') as f:
        model_pickle_path = f.name
        pickle.dump(model, f)

    try:
        # 2. 将股票列表分成多个批次
        batches = split_into_batches(stock_list, num_processes)

        logger.info(f"Split into {len(batches)} batches: {[len(b) for b in batches]}")

        # 3. 创建进程池
        with Pool(processes=num_processes) as pool:
            # 准备参数
            args_list = [
                (batch, predict_dates, provider_uri, model_pickle_path)
                for batch in batches
            ]

            # 并行执行
            results_list = pool.map(_predict_batch, args_list)

        # 4. 合并结果
        all_results = []
        for results in results_list:
            all_results.extend(results)

        result_df = pd.DataFrame(all_results)

        # 只保留用户请求的日期
        if not result_df.empty:
            result_df = result_df[result_df['date'].isin(predict_dates)]

            # 排序：按日期和股票代码
            result_df['date'] = pd.to_datetime(result_df['date'])
            result_df = result_df.sort_values(['date', 'stock_code'])

        logger.info(f"Parallel prediction completed: {len(result_df)} total predictions")
        return result_df

    finally:
        # 5. 清理临时文件
        if os.path.exists(model_pickle_path):
            os.remove(model_pickle_path)
            logger.info("Cleaned up temporary model file")


def predict_stocks_sequential(
    model,
    stock_list: List[str],
    predict_dates: List[str]
) -> pd.DataFrame:
    """
    顺序预测（单进程）

    策略：
    1. 创建包含所有预测日期和股票的 dataset
    2. 一次性预测所有数据
    3. 解析结果

    适用于：
    - 股票数量较少
    - 日期数量较少
    - 调试模式
    """
    logger.info("Starting sequential prediction")
    logger.info(f"Total stocks: {len(stock_list)}, Total dates: {len(predict_dates)}")

    # 创建包含所有预测日期的 dataset
    min_date = min(predict_dates)
    max_date = max(predict_dates)

    predict_dataset_config = {
        "class": "DatasetH",
        "module_path": "qlib.data.dataset",
        "kwargs": {
            "handler": {
                "class": "Alpha158",
                "module_path": "qlib.contrib.data.handler",
                "kwargs": {
                    "start_time": min_date,
                    "end_time": max_date,
                    "fit_start_time": min_date,
                    "fit_end_time": max_date,
                    "instruments": stock_list,
                },
            },
            "segments": {
                "test": (min_date, max_date),
            },
        },
    }

    predict_dataset = init_instance_by_config(predict_dataset_config)

    # 直接使用 dataset 进行预测（不要先 prepare）
    # LGBModel.predict() 方法会自己调用 dataset.prepare()
    predictions = model.predict(predict_dataset, segment='test')

    # 解析预测结果
    results = []
    for (date, stock_code), prediction in zip(predictions.index, predictions):
        results.append({
            'date': date,
            'stock_code': stock_code,
            'prediction': prediction
        })

    result_df = pd.DataFrame(results)

    # 只保留用户请求的日期
    if not result_df.empty:
        result_df = result_df[result_df['date'].isin(predict_dates)]

        # 排序：按日期和股票代码
        result_df['date'] = pd.to_datetime(result_df['date'])
        result_df = result_df.sort_values(['date', 'stock_code'])

    logger.info(f"Sequential prediction completed: {len(result_df)} total predictions")
    return result_df


def save_predictions(predictions: pd.DataFrame, output_path: str, stock_names_map: Dict[str, str] = None):
    """
    保存预测结果到 CSV 文件

    Parameters:
        predictions: 预测结果 DataFrame
        output_path: 输出文件路径
        stock_names_map: 股票代码到名称的映射
    """
    logger.info(f"Saving predictions to {output_path}")

    if predictions.empty:
        logger.warning("No predictions to save")
        return

    # 添加股票名称（如果提供了映射）
    if stock_names_map:
        predictions['stock_name'] = predictions['stock_code'].map(stock_names_map)
        predictions['stock_name'] = predictions['stock_name'].fillna('Unknown')

    # 保存为 CSV
    predictions.to_csv(output_path, index=False, encoding='utf-8-sig')
    logger.info(f"Predictions saved successfully to {output_path}")


def main(
    csv_path: str = "a500.csv",
    dates: str = None,              # 单个或多个日期
    start_date: str = None,          # 日期段开始
    end_date: str = None,            # 日期段结束
    last_n_days: int = None,         # 最近N天
    num_processes: int = 8,          # 进程数（默认8）
    output_path: str = "predictions.csv",
    provider_uri: str = "~/.qlib/tencent_data/qlib_data",
    experiment_name: str = "stock_prediction"
):
    """
    主入口函数

    集成所有步骤：
    1. 加载股票列表
    2. 解析预测日期
    3. 确定训练数据截止日期
    4. 训练模型
    5. 多进程预测
    6. 保存结果
    """
    logger.info("=" * 80)
    logger.info("STOCK PREDICTION FUNCTION")
    logger.info("=" * 80)

    # 1. 加载股票列表和名称映射
    stock_list = load_stock_list_from_csv(csv_path)
    stock_names_map = load_stock_names_map(csv_path)

    # 2. 解析预测日期
    predict_dates = parse_prediction_dates(
        provider_uri=provider_uri,
        dates=dates,
        start_date=start_date,
        end_date=end_date,
        last_n_days=last_n_days
    )

    # 3. 确定训练数据截止日期
    train_end_date = determine_train_end_date(predict_dates, provider_uri)

    # 4. 训练模型
    model = train_model_for_prediction(
        provider_uri=provider_uri,
        stock_list=stock_list,
        train_end_date=train_end_date
    )

    # 5. 优化进程数
    num_processes = get_optimal_num_processes(num_processes)

    # 6. 执行预测
    if num_processes == 1:
        # 单进程顺序预测
        predictions = predict_stocks_sequential(
            model=model,
            stock_list=stock_list,
            predict_dates=predict_dates
        )
    else:
        # 多进程并行预测
        predictions = predict_stocks_parallel(
            model=model,
            stock_list=stock_list,
            predict_dates=predict_dates,
            provider_uri=provider_uri,
            num_processes=num_processes
        )

    # 7. 保存结果
    save_predictions(predictions, output_path, stock_names_map)

    logger.info("=" * 80)
    logger.info("PREDICTION COMPLETED SUCCESSFULLY")
    logger.info(f"Total predictions: {len(predictions)}")
    logger.info(f"Output file: {output_path}")
    logger.info("=" * 80)


if __name__ == "__main__":
    fire.Fire(main)
