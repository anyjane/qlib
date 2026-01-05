"""Task queue and dispatcher for process pool"""
import logging
import threading
from typing import Dict, Any, Optional
from queue import Empty
import asyncio

logger = logging.getLogger(__name__)


class TaskQueue:
    """任务队列类，用于在主进程和工作进程之间传递任务"""

    def __init__(self, maxsize: int = 100):
        """
        初始化任务队列

        Args:
            maxsize: 队列最大长度
        """
        from multiprocessing import Manager
        self.manager = Manager()
        self.task_queue = self.manager.Queue(maxsize=maxsize)
        self.result_queue = self.manager.Queue(maxsize=maxsize)
        self.logger = logging.getLogger(__name__)
        self._closed = False  # 添加关闭标志
    
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
        # 如果队列已关闭，直接返回 None
        if self._closed:
            return None

        try:
            task_params = self.task_queue.get(timeout=timeout)
            self.logger.debug(f"Task {task_params.get('task_id')} retrieved from queue")
            return task_params
        except Empty:
            return None
        except BrokenPipeError:
            # 队列被关闭时的预期错误，静默处理
            return None
        except Exception as e:
            # 只在非关闭状态下记录错误
            if not self._closed:
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
        if self._closed:
            return False

        try:
            self.result_queue.put(result, timeout=5)
            self.logger.debug(f"Result for task {result.get('task_id')} added to result queue")
            return True
        except BrokenPipeError:
            # 队列被关闭时的预期错误
            return False
        except Exception as e:
            if not self._closed:
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
        # Manager Queue 不支持 task_done()
        pass
    
    def join(self):
        """等待队列中的所有任务完成"""
        # Manager Queue 不支持 join()
        pass
    
    def close(self):
        """关闭队列"""
        self._closed = True
        try:
            self.task_queue.close()
            self.result_queue.close()
            self.manager.shutdown()
        except Exception as e:
            # 忽略关闭时的错误
            self.logger.debug(f"Queue close error (expected): {e}")
    
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
        self.result_queue = None  # 用于存储结果队列的引用
    
    def start(self):
        """启动任务分发器"""
        if self.running:
            self.logger.warning("Task dispatcher already running")
            return
        
        self.running = True
        self.result_queue = self.task_queue.result_queue
        self.dispatcher_thread = threading.Thread(target=self._dispatch_loop, daemon=False)
        self.dispatcher_thread.start()
        self.logger.info("Task dispatcher started")
    
    def stop(self):
        """停止任务分发器"""
        if not self.running:
            return

        # 先设置 running 标志，让循环退出
        self.running = False

        # 等待线程完全停止
        if self.dispatcher_thread and self.dispatcher_thread.is_alive():
            # 给线程一些时间自然退出
            self.dispatcher_thread.join(timeout=2)
            if self.dispatcher_thread.is_alive():
                self.logger.warning("Dispatcher thread did not stop gracefully, forcing exit")

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
                
            except Exception as e:
                # 只在仍在运行时记录错误，避免在停止时写日志
                if self.running:
                    self.logger.error(f"Error in dispatch loop: {e}")
        
        # 线程退出前清理
        self.logger.debug("Dispatch loop exiting")
    
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
        # 如果已经停止，不处理回调
        if not self.running:
            return

        task_id = result.get("task_id")
        self.logger.info(f"Task {task_id} completed with status: {result.get('status')}")

        # 直接更新到数据库和 WebSocket（在回调线程中）
        try:
            from database import MongoDB
            from models import TaskStatus

            task_type = result.get("task_type")

            # 创建新的事件循环来运行异步操作
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # 根据任务类型更新不同的集合
                if task_type == "data_download" or task_type == "data_update":
                    loop.run_until_complete(self._update_to_db_and_ws(result))
                elif task_type == "prediction":
                    loop.run_until_complete(self._update_to_db_and_ws(result))
            finally:
                loop.close()
                asyncio.set_event_loop(None)

        except Exception as e:
            if self.running:
                self.logger.error(f"Failed to handle task result: {e}")
    
    def _task_error_callback(self, error):
        """
        任务错误回调函数

        Args:
            error: 错误对象
        """
        # 如果已经停止，不处理错误回调
        if not self.running:
            return

        self.logger.error(f"Task failed with error: {error}")

        # 构造错误结果
        result = {
            "task_id": "unknown",
            "status": "failed",
            "error": str(error),
            "completed_at": None
        }

        try:
            from database import MongoDB
            from websocket_manager import WebSocketManager

            # 创建新的事件循环来运行异步操作
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._update_error_to_db_and_ws(result))
            finally:
                loop.close()
                asyncio.set_event_loop(None)
        except Exception as e:
            if self.running:
                self.logger.error(f"Failed to handle task error: {e}")
    
    async def _update_to_db_and_ws(self, result: Dict[str, Any]):
        """
        更新结果到数据库和 WebSocket
        
        Args:
            result: 任务结果
        """
        from database import MongoDB
        from websocket_manager import WebSocketManager
        
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
            ws_manager = WebSocketManager()
            await ws_manager.broadcast_task_update({
                "task_id": task_id,
                "task_type": task_type,
                "status": result.get("status"),
                "progress": result.get("progress"),
                "message": result.get("message"),
                "error": result.get("error")
            })
            
            self.logger.debug(f"Task {task_id} result updated")
            
        except Exception as e:
            self.logger.error(f"Failed to update task {task_id}: {e}")
    
    async def _update_error_to_db_and_ws(self, result: Dict[str, Any]):
        """
        更新错误到数据库和 WebSocket
        
        Args:
            result: 错误结果
        """
        from database import MongoDB
        from websocket_manager import WebSocketManager
        
        task_id = result.get("task_id")
        
        try:
            # 通过 WebSocket 推送错误
            ws_manager = WebSocketManager()
            await ws_manager.broadcast_task_update({
                "task_id": task_id,
                "status": "failed",
                "error": result.get("error")
            })
            
            self.logger.debug(f"Task {task_id} error updated")
            
        except Exception as e:
            self.logger.error(f"Failed to update task error {task_id}: {e}")
