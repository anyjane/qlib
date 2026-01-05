"""Task queue and dispatcher for process pool"""
import logging
from typing import Dict, Any, Optional
from multiprocessing import Queue, JoinableQueue
import threading
from queue import Empty

logger = logging.getLogger(__name__)


class TaskQueue:
    """任务队列类，用于在主进程和工作进程之间传递任务"""
    
    def __init__(self, maxsize: int = 100):
        """
        初始化任务队列
        
        Args:
            maxsize: 队列最大长度
        """
        self.task_queue = JoinableQueue(maxsize=maxsize)
        self.result_queue = Queue(maxsize=maxsize)
        self.logger = logging.getLogger(__name__)
    
    def put_task(self, task_params: Dict[str, Any]) -> bool:
        """
        将任务放入队列
        
        Args:
            task_params: 任务参数字典
            
        Returns:
            是否成功放入队列
        """
        try:
            self.task_queue.put(task_params, timeout=5)
            self.logger.debug(f"Task {task_params.get('task_id')} added to queue")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add task to queue: {e}")
            return False
    
    def get_task(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        从队列中获取任务
        
        Args:
            timeout: 超时时间（秒），None 表示无限等待
            
        Returns:
            任务参数字典，超时返回 None
        """
        try:
            task_params = self.task_queue.get(timeout=timeout)
            self.logger.debug(f"Task {task_params.get('task_id')} retrieved from queue")
            return task_params
        except Empty:
            return None
        except Exception as e:
            self.logger.error(f"Failed to get task from queue: {e}")
            return None
    
    def put_result(self, result: Dict[str, Any]) -> bool:
        """
        将任务结果放入结果队列
        
        Args:
            result: 任务结果字典
            
        Returns:
            是否成功放入队列
        """
        try:
            self.result_queue.put(result, timeout=5)
            self.logger.debug(f"Result for task {result.get('task_id')} added to result queue")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add result to queue: {e}")
            return False
    
    def get_result(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        从结果队列中获取结果
        
        Args:
            timeout: 超时时间（秒），None 表示无限等待
            
        Returns:
            任务结果字典，超时返回 None
        """
        try:
            result = self.result_queue.get(timeout=timeout)
            self.logger.debug(f"Result for task {result.get('task_id')} retrieved from result queue")
            return result
        except Empty:
            return None
        except Exception as e:
            self.logger.error(f"Failed to get result from queue: {e}")
            return None
    
    def task_done(self):
        """标记任务已完成"""
        self.task_queue.task_done()
    
    def join(self):
        """等待队列中的所有任务完成"""
        self.task_queue.join()
    
    def close(self):
        """关闭队列"""
        self.task_queue.close()
        self.result_queue.close()
    
    def size(self) -> int:
        """获取队列大小"""
        return self.task_queue.qsize()


class TaskDispatcher:
    """任务分发器，负责从队列中获取任务并分发到工作进程"""
    
    def __init__(self, task_queue: TaskQueue, pool):
        """
        初始化任务分发器
        
        Args:
            task_queue: 任务队列实例
            pool: 进程池实例
        """
        self.task_queue = task_queue
        self.pool = pool
        self.running = False
        self.dispatcher_thread = None
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """启动任务分发器"""
        if self.running:
            self.logger.warning("Task dispatcher already running")
            return
        
        self.running = True
        self.dispatcher_thread = threading.Thread(target=self._dispatch_loop, daemon=True)
        self.dispatcher_thread.start()
        self.logger.info("Task dispatcher started")
    
    def stop(self):
        """停止任务分发器"""
        if not self.running:
            return
        
        self.running = False
        if self.dispatcher_thread:
            self.dispatcher_thread.join(timeout=5)
        self.logger.info("Task dispatcher stopped")
    
    def _dispatch_loop(self):
        """任务分发循环"""
        while self.running:
            try:
                # 从队列中获取任务
                task_params = self.task_queue.get_task(timeout=1)
                if task_params is None:
                    continue
                
                # 异步提交任务到进程池
                task_id = task_params.get("task_id")
                self.logger.info(f"Dispatching task {task_id} to worker pool")
                
                self.pool.apply_async(
                    self._worker_wrapper,
                    args=(task_params,),
                    callback=self._task_callback,
                    error_callback=self._task_error_callback
                )
                
                # 标记任务已从队列中取出
                self.task_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error in dispatch loop: {e}")
    
    def _worker_wrapper(self, task_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        工作进程包装函数
        用于在主进程和工作进程之间传递数据
        
        Args:
            task_params: 任务参数
            
        Returns:
            任务结果
        """
        from .task_worker import worker_main
        
        return worker_main(task_params)
    
    def _task_callback(self, result: Dict[str, Any]):
        """
        任务完成回调函数
        
        Args:
            result: 任务结果
        """
        task_id = result.get("task_id")
        self.logger.info(f"Task {task_id} completed with status: {result.get('status')}")
        
        # 将结果放入结果队列
        self.task_queue.put_result(result)
    
    def _task_error_callback(self, error):
        """
        任务错误回调函数
        
        Args:
            error: 错误对象
        """
        self.logger.error(f"Task failed with error: {error}")
        
        # 构造错误结果
        result = {
            "task_id": "unknown",
            "status": "failed",
            "error": str(error),
            "completed_at": None
        }
        self.task_queue.put_result(result)


class ResultCollector:
    """结果收集器，负责从结果队列中收集结果并更新到数据库"""
    
    def __init__(self, task_queue: TaskQueue):
        """
        初始化结果收集器
        
        Args:
            task_queue: 任务队列实例
        """
        self.task_queue = task_queue
        self.running = False
        self.collector_thread = None
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """启动结果收集器"""
        if self.running:
            self.logger.warning("Result collector already running")
            return
        
        self.running = True
        self.collector_thread = threading.Thread(target=self._collect_loop, daemon=True)
        self.collector_thread.start()
        self.logger.info("Result collector started")
    
    def stop(self):
        """停止结果收集器"""
        if not self.running:
            return
        
        self.running = False
        if self.collector_thread:
            self.collector_thread.join(timeout=5)
        self.logger.info("Result collector stopped")
    
    def _collect_loop(self):
        """结果收集循环"""
        while self.running:
            try:
                # 从结果队列中获取结果
                result = self.task_queue.get_result(timeout=1)
                if result is None:
                    continue
                
                # 异步处理结果
                task_id = result.get("task_id")
                self.logger.info(f"Collecting result for task {task_id}")
                
                # 将结果更新到数据库
                import asyncio
                asyncio.create_task(self._update_task_result(result))
                
            except Exception as e:
                self.logger.error(f"Error in collect loop: {e}")
    
    async def _update_task_result(self, result: Dict[str, Any]):
        """
        更新任务结果到数据库
        
        Args:
            result: 任务结果
        """
        from ..database import MongoDB
        from ..models import TaskStatus
        
        task_id = result.get("task_id")
        task_type = result.get("task_type")
        
        try:
            # 根据任务类型更新不同的集合
            if task_type == "data_download" or task_type == "data_update":
                await MongoDB.update_data_task(task_id, {
                    "status": result.get("status"),
                    "progress": result.get("progress"),
                    "message": result.get("message"),
                    "error": result.get("error"),
                    "completed_at": result.get("completed_at")
                })
            elif task_type == "prediction":
                await MongoDB.update_prediction_task(task_id, {
                    "status": result.get("status"),
                    "progress": result.get("progress"),
                    "message": result.get("message"),
                    "error": result.get("error"),
                    "completed_at": result.get("completed_at")
                })
            
            # 通过 WebSocket 推送任务状态更新
            from ..websocket_manager import WebSocketManager
            ws_manager = WebSocketManager()
            await ws_manager.broadcast_task_update({
                "task_id": task_id,
                "task_type": task_type,
                "status": result.get("status"),
                "progress": result.get("progress"),
                "message": result.get("message"),
                "error": result.get("error")
            })
            
            self.logger.info(f"Task {task_id} result updated to database")
            
        except Exception as e:
            self.logger.error(f"Failed to update task result for {task_id}: {e}")
