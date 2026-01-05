"""FastAPI application entry point"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import sys
import signal
from typing import Dict, Set, Optional

from config import settings
from database import MongoDB
from services.task_pool import initialize_task_pool, get_task_pool_manager
from websocket_manager import manager


# Configure loguru
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=settings.LOG_LEVEL
)
logger.add(
    f"{settings.LOG_DIR}/app.log",
    rotation="500 MB",
    retention="10 days",
    level=settings.LOG_LEVEL
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Setup signal handler for graceful shutdown
    def handle_signal(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        # 标记请求停止，让 lifespan 的 shutdown 部分处理
        pass

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Startup
    logger.info("Starting Quantitative Investment Management System...")

    # 初始化任务进程池（TaskPoolManager 是单例，initialize_task_pool 返回实例）
    # 必须在 MongoDB 连接之前初始化进程池，避免子进程继承不可序列化的 MongoDB 连接对象
    logger.info("Initializing task process pool...")
    task_pool_manager = initialize_task_pool(
        pool_size=4,  # 可以根据需要调整进程数
        max_queue_size=100,
        enable_progress_queue=True
    )
    logger.info("Task process pool initialized successfully")

    # MongoDB 连接必须在进程池初始化之后进行
    await MongoDB.connect_to_mongodb()

    yield

    # Shutdown
    logger.info("Shutting down...")

    # 停止任务进程池（使用 get_task_pool_manager 获取单例实例）
    logger.info("Stopping task process pool...")
    pool_manager = get_task_pool_manager()
    if pool_manager.is_initialized():
        pool_manager.stop()
        logger.info("Task process pool stopped")
    else:
        logger.warning("Task pool manager was not initialized")

    await MongoDB.close_mongodb()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于 FastAPI 的量化投资管理系统，支持股票代码管理、数据下载、预测、持仓管理和交易代理管理",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health Check
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check MongoDB connection
        await MongoDB.database.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


# ============================================================================
# API Routers
# ============================================================================

from api import stock, data, predict, position, agent, log

app.include_router(stock.router)
app.include_router(data.router)
app.include_router(predict.router)
app.include_router(position.router)
app.include_router(agent.router)
app.include_router(log.router)


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@app.websocket("/ws/tasks/{client_id}")
async def websocket_tasks(websocket: WebSocket, client_id: str):
    """WebSocket 端点：实时推送任务状态更新"""
    await manager.connect(websocket, client_id)
    try:
        # 保持连接，等待客户端消息
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, client_id)
        logger.info(f"WebSocket connection closed for client: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        await manager.disconnect(websocket, client_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
