"""Process pool manager for background task execution"""
import logging
from typing import Optional, Dict, Any
from multiprocessing import Pool, cpu_count, Queue
import threading

from .task_queue import TaskQueue, TaskDispatcher, ResultCollector
from .task_worker import init_worker_process

logger = logging.getLogger(__name__)


class TaskPoolManager:
    """进程池管理器，负责管理后台任务的生命周期"""
    
    _instance: Optional['TaskPoolManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """单例模式，确保只有一个进程池管理器实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(TaskPoolManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        pool_size: Optional[int] = None,
        max_queue_size: int = 100,
        enable_progress_queue: bool = True
    ):
        """
        初始化进程池管理器
        
        Args:
            pool_size: 进程池大小，None 表示自动检测 CPU 核心数
            max_queue_size: 任务队列最大长度
            enable_progress_queue: 是否启用进度队列
        """
        # 避免重复初始化
        if hasattr(self, 'initialized') and self.initialized:
            return
        
        self.pool_size = pool_size or cpu_count()
        self.max_queue_size = max_queue_size
        self.enable_progress_queue = enable_progress_queue
        
        # 创建进程池
        self.pool: Optional[Pool] = None
        
        # 创建任务队列
        self.task_queue = TaskQueue(maxsize=max_queue_size)
        
        # 创建进度队列（如果启用）
        self.progress_queue: Optional[Queue] = None
        if enable_progress_queue:
            self.progress_queue = Queue(maxsize=max_queue_size)
        
        # 任务分发器和结果收集器
        self.dispatcher: Optional[TaskDispatcher] = None
        self.result_collector: Optional[ResultCollector] = None
        
        self.initialized = False
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """启动进程池管理器"""
        if self.initialized:
            self.logger.warning("TaskPoolManager already started")
            return
        
        try:
            self.logger.info(f"Starting TaskPoolManager with pool_size={self.pool_size}")
            
            # 创建进程池，使用初始化函数在每个工作进程中初始化 Qlib
            self.pool = Pool(
                processes=self.pool_size,
                initializer=init_worker_process,
                initargs=()
            )
            
            self.logger.info(f"Process pool created with {self.pool_size} workers")
            
            # 创建并启动任务分发器
            self.dispatcher = TaskDispatcher(self.task_queue, self.pool)
            self.dispatcher.start()
            
            # 创建并启动结果收集器
            self.result_collector = ResultCollector(self.task_queue)
            self.result_collector.start()
            
            # 启动进度监控器（如果启用）
            if self.enable_progress_queue and self.progress_queue:
                from .progress_reporter import ProgressMonitor
                progress_monitor = ProgressMonitor(self.progress_queue)
                import asyncio
                asyncio.create_task(progress_monitor.monitor_progress())
            
            self.initialized = True
            self.logger.info("TaskPoolManager started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start TaskPoolManager: {e}")
            raise
    
    def stop(self):
        """停止进程池管理器"""
        if not self.initialized:
            self.logger.warning("TaskPoolManager not started")
            return
        
        try:
            self.logger.info("Stopping TaskPoolManager...")
            
            # 停止任务分发器
            if self.dispatcher:
                self.dispatcher.stop()
            
            # 停止结果收集器
            if self.result_collector:
                self.result_collector.stop()
            
            # 关闭队列
            self.task_queue.close()
            
            # 关闭进程池
            if self.pool:
                self.pool.close()
                self.pool.join()
                self.logger.info("Process pool closed and joined")
            
            # 关闭进度队列
            if self.progress_queue:
                self.progress_queue.close()
            
            self.initialized = False
            self.logger.info("TaskPoolManager stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping TaskPoolManager: {e}")
    
    def submit_task(self, task_params: Dict[str, Any]) -> bool:
        """
        提交任务到进程池
        
        Args:
            task_params: 任务参数字典，必须包含 task_type 和 task_id
            
        Returns:
            是否成功提交任务
        """
        if not self.initialized:
            self.logger.error("TaskPoolManager not started, cannot submit task")
            return False
        
        # 检查必需的参数
        if "task_type" not in task_params or "task_id" not in task_params:
            self.logger.error("Missing required parameters: task_type or task_id")
            return False
        
        # 添加进度队列到任务参数中（如果启用）
        if self.enable_progress_queue and self.progress_queue:
            task_params["progress_queue"] = self.progress_queue
        
        # 将任务放入队列
        success = self.task_queue.put_task(task_params)
        
        if success:
            self.logger.info(f"Task {task_params['task_id']} submitted successfully")
        else:
            self.logger.error(f"Failed to submit task {task_params['task_id']}")
        
        return success
    
    def get_pool_status(self) -> Dict[str, Any]:
        """
        获取进程池状态
        
        Returns:
            进程池状态字典
        """
        return {
            "initialized": self.initialized,
            "pool_size": self.pool_size,
            "queue_size": self.task_queue.size(),
            "max_queue_size": self.max_queue_size,
            "enable_progress_queue": self.enable_progress_queue
        }
    
    def is_initialized(self) -> bool:
        """检查进程池是否已初始化"""
        return self.initialized


# 全局实例
_task_pool_manager: Optional[TaskPoolManager] = None


def get_task_pool_manager() -> TaskPoolManager:
    """
    获取全局任务池管理器实例
    
    Returns:
        TaskPoolManager 实例
    """
    global _task_pool_manager
    if _task_pool_manager is None:
        _task_pool_manager = TaskPoolManager()
    return _task_pool_manager


def initialize_task_pool(
    pool_size: Optional[int] = None,
    max_queue_size: int = 100,
    enable_progress_queue: bool = True
):
    """
    初始化全局任务池管理器
    
    Args:
        pool_size: 进程池大小
        max_queue_size: 任务队列最大长度
        enable_progress_queue: 是否启用进度队列
    """
    global _task_pool_manager
    if _task_pool_manager is None:
        _task_pool_manager = TaskPoolManager(
            pool_size=pool_size,
            max_queue_size=max_queue_size,
            enable_progress_queue=enable_progress_queue
        )
    _task_pool_manager.start()
