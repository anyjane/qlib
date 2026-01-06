"""Task worker implementation for process pool"""
import logging
import os
import sys
import signal
from typing import Dict, Any
from datetime import datetime, timedelta

# 添加项目路径到 sys.path，确保能够导入 qlib
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入 qlib 相关模块
try:
    import qlib
    from qlib.data import D
    from qlib.workflow import R
    from qlib.config import REG_CN
except ImportError as e:
    logging.warning(f"Qlib import warning: {e}")

logger = logging.getLogger(__name__)

# 导入配置 - 统一从 config 模块获取
from config import settings

# 全局变量，用于存储 Qlib 是否已初始化
_qlib_initialized = False


def init_worker_process():
    """
    工作进程初始化函数
    在进程池创建时调用，每个工作进程只调用一次
    """
    # 忽略 SIGINT 信号，让主进程处理
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    global _qlib_initialized

    if _qlib_initialized:
        logger.info("Qlib already initialized in this worker process")
        return

    try:
        # 使用配置中的 provider_uri 和 region
        provider_uri = settings.QLIB_PROVIDER_URI
        region = settings.QLIB_REGION.upper()

        # 如果 region 是 'cn'，则使用 REG_CN，否则直接使用字符串
        region_config = REG_CN if region == "CN" else region

        qlib.init(provider_uri=provider_uri, region=region_config)
        _qlib_initialized = True

        logger.info(f"Worker process {os.getpid()} initialized Qlib successfully with provider_uri={provider_uri}, region={region}")
    except Exception as e:
        logger.error(f"Failed to initialize Qlib in worker process: {e}")
        raise


def execute_data_download_task(task_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行数据下载任务（使用多线程并行下载）
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    task_type = task_params.get("task_type")
    task_id = task_params.get("task_id")
    start_date = task_params.get("start_date", "2015-01-01")
    end_date = task_params.get("end_date")
    stocks = task_params.get("stocks", [])
    
    # 并行下载的线程数
    max_workers = 16

    logger.info(f"Executing data download task {task_id} with {max_workers} parallel workers")

    try:
        from services.data_service import TencentDataService

        logger.info(f"Task {task_id}: Starting parallel data download for {len(stocks)} stocks...")

        # 标准化股票代码
        standardized_stocks = TencentDataService.standardize_stock_codes(stocks)
        
        # 定义单个股票下载函数
        def download_single_stock(code: str) -> tuple:
            """下载单个股票数据，返回 (code, result_dict)"""
            try:
                result = TencentDataService.download_from_tencent(
                    stocks=[code],
                    start=start_date,
                    end=end_date
                )
                return (code, result.get(code, {"count": 0}))
            except Exception as e:
                logger.error(f"Failed to download {code}: {e}")
                return (code, {"count": 0, "error": str(e)})
        
        # 使用线程池并行下载
        all_results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有下载任务
            future_to_code = {
                executor.submit(download_single_stock, code): code 
                for code in standardized_stocks
            }
            
            # 收集结果
            completed = 0
            total = len(standardized_stocks)
            for future in as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    result_code, result_data = future.result()
                    all_results[result_code] = result_data
                    completed += 1
                    logger.info(f"Task {task_id}: Downloaded {completed}/{total}: {code}")
                except Exception as e:
                    logger.error(f"Task {task_id}: Exception for {code}: {e}")
                    all_results[code] = {"count": 0, "error": str(e)}
                    completed += 1

        logger.info(f"Task {task_id}: All downloads completed, saving to Qlib format...")

        # 保存数据到 Qlib 格式
        save_result = TencentDataService.save_data_to_qlib_format(
            data_dict=all_results,
            download_ranges=start_date,
            end_date=end_date,
            use_update_mode=False
        )

        logger.info(f"Task {task_id}: Data download completed")

        # 解析结果，提取成功和失败的股票
        downloaded_stocks = []
        failed_stocks = []
        for code, data in all_results.items():
            if data.get("count", 0) > 0:
                downloaded_stocks.append(code)
            else:
                failed_stocks.append(code)

        return {
            "task_id": task_id,
            "task_type": task_type,
            "status": "completed",
            "progress": 100.0,
            "message": f"Data download completed: {len(downloaded_stocks)} success, {len(failed_stocks)} failed",
            "downloaded_stocks": downloaded_stocks,
            "failed_stocks": failed_stocks,
            "completed_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Data download task {task_id} failed: {e}")
        return {
            "task_id": task_id,
            "task_type": task_type,
            "status": "failed",
            "progress": 0.0,
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        }


def execute_data_update_task(task_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行数据更新任务（使用多线程并行下载）
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    task_type = task_params.get("task_type")
    task_id = task_params.get("task_id")
    stocks = task_params.get("stocks", [])
    
    # 并行下载的线程数
    max_workers = 16

    logger.info(f"Executing data update task {task_id} with {max_workers} parallel workers")

    try:
        from services.data_service import TencentDataService

        logger.info(f"Task {task_id}: Starting parallel data update for {len(stocks)} stocks...")

        # 更新任务默认获取最近 90 天的数据
        end_date = datetime.now().strftime("%Y-%m-%d")
        default_start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

        # 标准化股票代码
        standardized_stocks = TencentDataService.standardize_stock_codes(stocks)
        
        # 添加基准指数 (沪深300, 中证500)
        benchmarks = ["sh000300", "sh000905"]
        for benchmark in benchmarks:
            if benchmark not in standardized_stocks:
                standardized_stocks.append(benchmark)
                logger.info(f"Added benchmark index {benchmark} to download list")

        # 定义单个股票下载函数
        def download_single_stock(code: str) -> tuple:
            """下载单个股票数据，返回 (code, result_dict, stock_start_date)"""
            try:
                # 获取该股票已有的数据信息
                stock_info = TencentDataService.get_stock_data_info(code)

                # 如果有数据，从最后一个交易日开始下载以覆盖该日数据
                if stock_info.get("has_data") and stock_info.get("end_date"):
                    stock_start_date = stock_info["end_date"]
                    logger.info(f"[{code}] 已有数据，从最后一个交易日 {stock_start_date} 开始更新（覆盖该日）")
                else:
                    stock_start_date = default_start_date
                    logger.info(f"[{code}] 无已有数据，从默认日期 {stock_start_date} 开始下载")

                result = TencentDataService.download_from_tencent(
                    stocks=[code],
                    start=stock_start_date,
                    end=end_date
                )
                return (code, result.get(code, {"count": 0}), stock_start_date)
            except Exception as e:
                logger.error(f"Failed to update {code}: {e}")
                return (code, {"count": 0, "error": str(e)}, default_start_date)
        
        # 使用线程池并行下载
        all_results = {}
        download_ranges = {}  # 记录每只股票的下载起始日期
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有下载任务
            future_to_code = {
                executor.submit(download_single_stock, code): code
                for code in standardized_stocks
            }

            # 收集结果
            completed = 0
            total = len(standardized_stocks)
            for future in as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    result_code, result_data, stock_start_date = future.result()
                    all_results[result_code] = result_data
                    download_ranges[result_code] = stock_start_date
                    completed += 1
                    logger.info(f"Task {task_id}: Updated {completed}/{total}: {code}")
                except Exception as e:
                    logger.error(f"Task {task_id}: Exception for {code}: {e}")
                    all_results[code] = {"count": 0, "error": str(e)}
                    download_ranges[code] = default_start_date
                    completed += 1

        logger.info(f"Task {task_id}: All updates completed, saving to Qlib format...")

        # 保存数据到 Qlib 格式（使用更新模式）
        save_result = TencentDataService.save_data_to_qlib_format(
            data_dict=all_results,
            download_ranges=download_ranges,  # 使用每只股票单独的起始日期
            end_date=end_date,
            use_update_mode=True
        )

        logger.info(f"Task {task_id}: Data update completed")

        # 解析结果，提取成功和失败的股票
        updated_stocks = []
        failed_stocks = []
        for code, data in all_results.items():
            if data.get("count", 0) > 0:
                updated_stocks.append(code)
            else:
                failed_stocks.append(code)

        return {
            "task_id": task_id,
            "task_type": task_type,
            "status": "completed",
            "progress": 100.0,
            "message": f"Data update completed: {len(updated_stocks)} success, {len(failed_stocks)} failed",
            "updated_stocks": updated_stocks,
            "failed_stocks": failed_stocks,
            "completed_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Data update task {task_id} failed: {e}")
        return {
            "task_id": task_id,
            "task_type": task_type,
            "status": "failed",
            "progress": 0.0,
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        }


def execute_prediction_task(task_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行预测任务
    """
    task_type = task_params.get("task_type")
    task_id = task_params.get("task_id")
    predict_date = task_params.get("predict_date")
    stocks = task_params.get("stocks")

    logger.info(f"Executing prediction task {task_id}")

    try:
        from services.qlib_predictor import QlibPredictor

        logger.info(f"Task {task_id}: Initializing predictor...")

        # 使用配置中的 provider_uri 创建预测器
        predictor = QlibPredictor(
            provider_uri=settings.QLIB_PROVIDER_URI,
            experiment_name=f"prediction_{task_id}"
        )

        logger.info(f"Task {task_id}: Generating predictions...")

        result = predictor.predict(
            predict_date=predict_date,
            stock_codes=stocks
        )

        logger.info(f"Task {task_id}: Prediction completed, saving to database...")

        # 使用同步 pymongo 保存预测结果到数据库
        from pymongo import MongoClient
        
        mongo_client = MongoClient(settings.MONGODB_URL)
        db = mongo_client[settings.MONGODB_DB_NAME]
        
        # 转换预测结果格式并添加 task_id
        predictions_to_save = []
        for pred in result.get("predictions", []):
            predictions_to_save.append({
                "task_id": task_id,
                "date": predict_date,
                "code": pred["code"],
                "name": pred.get("name", "Unknown"),
                "score": pred["score"],
                "execution_timestamp": result.get("execution_timestamp"),
                "data_date": result.get("data_date"),
                "created_at": datetime.now()
            })
        
        if predictions_to_save:
            db.predictions.insert_many(predictions_to_save)
            logger.info(f"Task {task_id}: Saved {len(predictions_to_save)} predictions to database")
        
        # 更新任务状态
        db.prediction_tasks.update_one(
            {"task_id": task_id},
            {"$set": {
                "status": "completed",
                "progress": 100,
                "predicted_count": len(predictions_to_save),
                "updated_at": datetime.now()
            }}
        )
        
        mongo_client.close()
        logger.info(f"Task {task_id}: Database update completed")

        return {
            "task_id": task_id,
            "task_type": task_type,
            "status": "completed",
            "progress": 100.0,
            "message": "Prediction completed successfully",
            "predictions": result.get("predictions", []),
            "total_predictions": len(result.get("predictions", [])),
            "completed_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Prediction task {task_id} failed: {e}")
        return {
            "task_id": task_id,
            "task_type": task_type,
            "status": "failed",
            "progress": 0.0,
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        }


def execute_backtest_task(task_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行回测任务
    """
    task_type = task_params.get("task_type")
    task_id = task_params.get("task_id")
    market = task_params.get("market", "all")
    train_start = task_params.get("train_start", "2020-01-01")
    train_end = task_params.get("train_end", "2024-12-31")
    test_start = task_params.get("test_start", "2025-01-01")
    test_end = task_params.get("test_end", "2025-12-31")
    experiment_name = task_params.get("experiment_name", f"backtest_{task_id}")
    provider_uri = task_params.get("provider_uri", settings.QLIB_PROVIDER_URI)

    logger.info(f"Executing backtest task {task_id}")
    logger.info(f"Market: {market}, Train: {train_start} ~ {train_end}, Test: {test_start} ~ {test_end}")

    try:
        from services.backtest_service import BacktestService
        from pymongo import MongoClient
        
        # 更新任务状态为运行中
        mongo_client = MongoClient(settings.MONGODB_URL)
        db = mongo_client[settings.MONGODB_DB_NAME]
        db.backtest_tasks.update_one(
            {"task_id": task_id},
            {"$set": {"status": "running", "updated_at": datetime.now()}}
        )
        
        # 执行回测
        results = BacktestService.run_backtest(
            provider_uri=provider_uri,
            market=market,
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
            experiment_name=experiment_name,
        )
        
        # 保存结果到数据库
        # 保存结果到数据库
        results_doc = {
            "task_id": task_id,
            "metrics": results.get("metrics", {}),
            "trade_logs": results.get("trade_logs", []),
            "created_at": datetime.now(),
        }
        db.backtest_results.insert_one(results_doc)
        
        # 更新任务状态为完成
        db.backtest_tasks.update_one(
            {"task_id": task_id},
            {"$set": {"status": "completed", "updated_at": datetime.now()}}
        )
        
        mongo_client.close()
        logger.info(f"Backtest task {task_id} completed successfully")

        return {
            "task_id": task_id,
            "task_type": task_type,
            "status": "completed",
            "progress": 100.0,
            "message": "Backtest completed successfully",
            "results": results,
            "completed_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Backtest task {task_id} failed: {e}")
        
        # 更新任务状态为失败
        try:
            from pymongo import MongoClient
            mongo_client = MongoClient(settings.MONGODB_URL)
            db = mongo_client[settings.MONGODB_DB_NAME]
            db.backtest_tasks.update_one(
                {"task_id": task_id},
                {"$set": {"status": "failed", "error": str(e), "updated_at": datetime.now()}}
            )
            mongo_client.close()
        except Exception:
            pass
        
        return {
            "task_id": task_id,
            "task_type": task_type,
            "status": "failed",
            "progress": 0.0,
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        }


# 任务类型映射字典
TASK_EXECUTORS = {
    "data_download": execute_data_download_task,
    "data_update": execute_data_update_task,
    "prediction": execute_prediction_task,
    "backtest": execute_backtest_task,
}


def worker_main(task_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    工作进程主函数
    根据任务类型分发到对应的执行函数
    
    Args:
        task_params: 任务参数字典
        
    Returns:
        任务执行结果字典
    """
    task_type = task_params.get("task_type")
    task_id = task_params.get("task_id")
    
    logger.info(f"Worker {os.getpid()} received task {task_id} of type {task_type}")
    
    # 确保使用全局的 _qlib_initialized 标志
    # 每个任务执行前检查 Qlib 是否已初始化
    global _qlib_initialized
    if not _qlib_initialized:
        logger.warning(f"Qlib not initialized in worker process {os.getpid()}, initializing now...")
        init_worker_process()
    
    # 根据任务类型分发任务
    executor = TASK_EXECUTORS.get(task_type)
    if not executor:
        logger.error(f"Unknown task type: {task_type}")
        return {
            "task_id": task_id,
            "status": "failed",
            "error": f"Unknown task type: {task_type}",
            "completed_at": datetime.now().isoformat()
        }
    
    # 执行任务
    return executor(task_params)
