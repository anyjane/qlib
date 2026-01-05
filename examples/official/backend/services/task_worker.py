"""Task worker implementation for process pool"""
import logging
import os
import sys
from typing import Dict, Any
from datetime import datetime

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

# 全局变量，用于存储 Qlib 是否已初始化
_qlib_initialized = False

# 导入配置
try:
    from config import settings
except ImportError:
    logger.warning("Failed to import config, using default Qlib settings")
    class Settings:
        QLIB_PROVIDER_URI = os.path.expanduser("~/.qlib/qlib_data/cn_data")
        QLIB_REGION = "cn"
    settings = Settings()


def init_worker_process():
    """
    工作进程初始化函数
    在进程池创建时调用，每个工作进程只调用一次
    """
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
    执行数据下载任务
    """
    task_type = task_params.get("task_type")
    task_id = task_params.get("task_id")
    start_date = task_params.get("start_date", "2015-01-01")
    end_date = task_params.get("end_date")
    stocks = task_params.get("stocks", [])
    
    logger.info(f"Executing data download task {task_id}")
    
    try:
        from .data_service import download_data_from_yahoo
        from .progress_reporter import ProgressReporter
        
        reporter = ProgressReporter(task_id)
        reporter.update_progress(10, "Starting data download...")
        
        # 执行数据下载
        result = download_data_from_yahoo(
            start_date=start_date,
            end_date=end_date,
            stocks=stocks,
            progress_callback=lambda p, msg: reporter.update_progress(10 + p * 0.8, msg)
        )
        
        reporter.update_progress(100, "Data download completed")
        logger.info(f"Data download task {task_id} completed successfully")
        
        return {
            "task_id": task_id,
            "task_type": task_type,
            "status": "completed",
            "progress": 100.0,
            "message": "Data download completed successfully",
            "downloaded_stocks": result.get("downloaded_stocks", []),
            "failed_stocks": result.get("failed_stocks", []),
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
    执行数据更新任务
    """
    task_type = task_params.get("task_type")
    task_id = task_params.get("task_id")
    stocks = task_params.get("stocks", [])
    
    logger.info(f"Executing data update task {task_id}")
    
    try:
        from .data_service import update_data_from_yahoo
        from .progress_reporter import ProgressReporter
        
        reporter = ProgressReporter(task_id)
        reporter.update_progress(10, "Starting data update...")
        
        # 执行数据更新
        result = update_data_from_yahoo(
            stocks=stocks,
            progress_callback=lambda p, msg: reporter.update_progress(10 + p * 0.8, msg)
        )
        
        reporter.update_progress(100, "Data update completed")
        logger.info(f"Data update task {task_id} completed successfully")
        
        return {
            "task_id": task_id,
            "task_type": task_type,
            "status": "completed",
            "progress": 100.0,
            "message": "Data update completed successfully",
            "updated_stocks": result.get("updated_stocks", []),
            "failed_stocks": result.get("failed_stocks", []),
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
        from .qlib_predictor import QlibPredictor
        from .progress_reporter import ProgressReporter
        
        reporter = ProgressReporter(task_id)
        reporter.update_progress(10, "Initializing predictor...")
        
        # 使用配置中的 provider_uri 创建预测器
        predictor = QlibPredictor(
            provider_uri=settings.QLIB_PROVIDER_URI,
            experiment_name=f"prediction_{task_id}"
        )
        reporter.update_progress(20, "Generating predictions...")
        
        result = predictor.predict(
            predict_date=predict_date,
            stock_codes=stocks,
            progress_callback=lambda p, msg: reporter.update_progress(20 + p * 0.7, msg)
        )
        
        reporter.update_progress(100, "Prediction completed")
        logger.info(f"Prediction task {task_id} completed successfully")
        
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


# 任务类型映射字典
TASK_EXECUTORS = {
    "data_download": execute_data_download_task,
    "data_update": execute_data_update_task,
    "prediction": execute_prediction_task,
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
