"""Progress reporter for task progress updates"""
import logging
from typing import Optional, TYPE_CHECKING

# 为了避免循环导入和 multiprocessing 问题，使用 TYPE_CHECKING
if TYPE_CHECKING:
    from multiprocessing import Queue

logger = logging.getLogger(__name__)


class ProgressReporter:
    """进度上报器，用于在工作进程中上报任务进度"""
    
    def __init__(self, task_id: str, progress_queue: Optional['Queue'] = None):
        """
        初始化进度上报器

        Args:
            task_id: 任务ID
            progress_queue: 进度队列（用于跨进程通信）
        """
        self.task_id = task_id
        self.progress_queue = progress_queue
        self.logger = logging.getLogger(__name__)
    
    def update_progress(self, progress: float, message: Optional[str] = None):
        """
        更新任务进度
        
        Args:
            progress: 进度百分比 (0-100)
            message: 进度消息
        """
        self.logger.debug(f"Task {self.task_id} progress: {progress}% - {message}")
        
        # 如果有进度队列，将进度更新放入队列
        if self.progress_queue:
            try:
                self.progress_queue.put({
                    "task_id": self.task_id,
                    "progress": progress,
                    "message": message
                })
            except Exception as e:
                self.logger.error(f"Failed to send progress update: {e}")
        
        # 同时记录日志
        if message:
            self.logger.info(f"Task {self.task_id}: {progress}% - {message}")
    
    def report_error(self, error: str):
        """
        报告错误
        
        Args:
            error: 错误信息
        """
        self.logger.error(f"Task {self.task_id} error: {error}")
        
        if self.progress_queue:
            try:
                self.progress_queue.put({
                    "task_id": self.task_id,
                    "error": error
                })
            except Exception as e:
                self.logger.error(f"Failed to send error report: {e}")
    
    def report_completion(self, message: str = "Task completed"):
        """
        报告任务完成
        
        Args:
            message: 完成消息
        """
        self.update_progress(100.0, message)
        self.logger.info(f"Task {self.task_id} completed: {message}")


class ProgressMonitor:
    """进度监控器，运行在主进程中，负责收集进度更新并更新到数据库"""
    
    def __init__(self, progress_queue: Optional['Queue'] = None):
        """
        初始化进度监控器

        Args:
            progress_queue: 进度队列
        """
        self.progress_queue = progress_queue
        self.logger = logging.getLogger(__name__)
    
    async def monitor_progress(self):
        """
        监控进度队列，收集进度更新
        
        此方法应该在后台线程中运行
        """
        import threading
        
        def _monitor_loop():
            from queue import Empty
            import asyncio
            
            while True:
                try:
                    # 从队列中获取进度更新
                    progress_update = self.progress_queue.get(timeout=1)
                    if progress_update is None:
                        continue
                    
                    # 异步处理进度更新
                    task_id = progress_update.get("task_id")
                    self.logger.debug(f"Received progress update for task {task_id}")
                    
                    # 在事件循环中运行异步任务
                    loop = asyncio.get_event_loop()
                    loop.create_task(self._handle_progress_update(progress_update))
                    
                except Empty:
                    continue
                except Exception as e:
                    self.logger.error(f"Error in progress monitor loop: {e}")
        
        # 在后台线程中启动监控循环
        monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
        monitor_thread.start()
        self.logger.info("Progress monitor started")
    
    async def _handle_progress_update(self, progress_update: dict):
        """
        处理进度更新
        
        Args:
            progress_update: 进度更新字典
        """
        from ..database import MongoDB
        from ..websocket_manager import WebSocketManager
        
        task_id = progress_update.get("task_id")
        
        try:
            # 检查是否有错误
            error = progress_update.get("error")
            if error:
                # 更新任务状态为失败
                await MongoDB.update_data_task(task_id, {
                    "status": "failed",
                    "error": error
                })
                
                # 通过 WebSocket 推送错误
                ws_manager = WebSocketManager()
                await ws_manager.broadcast_task_update({
                    "task_id": task_id,
                    "status": "failed",
                    "error": error
                })
                
                self.logger.info(f"Task {task_id} error reported")
                return
            
            # 更新任务进度
            progress = progress_update.get("progress")
            message = progress_update.get("message")
            
            # 首先尝试更新 data_task
            try:
                await MongoDB.update_data_task(task_id, {
                    "progress": progress,
                    "message": message
                })
            except:
                # 如果 data_task 更新失败，尝试更新 prediction_task
                try:
                    await MongoDB.update_prediction_task(task_id, {
                        "progress": progress,
                        "message": message
                    })
                except Exception as e:
                    self.logger.error(f"Failed to update progress for task {task_id}: {e}")
                    return
            
            # 通过 WebSocket 推送进度更新
            ws_manager = WebSocketManager()
            await ws_manager.broadcast_task_update({
                "task_id": task_id,
                "progress": progress,
                "message": message
            })
            
            self.logger.debug(f"Progress updated for task {task_id}: {progress}%")
            
        except Exception as e:
            self.logger.error(f"Failed to handle progress update for task {task_id}: {e}")
