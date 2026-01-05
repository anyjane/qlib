"""FastAPI application entry point"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import sys
from typing import Dict, Set

from config import settings
from database import MongoDB

# ============================================================================
# WebSocket Connection Manager
# ============================================================================

class ConnectionManager:
    """WebSocket 连接管理器 - 用于实时推送任务状态"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """客户端连接"""
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = set()
        self.active_connections[client_id].add(websocket)
        logger.info(f"WebSocket client connected: {client_id}")
    
    async def disconnect(self, websocket: WebSocket, client_id: str):
        """客户端断开连接"""
        if client_id in self.active_connections:
            self.active_connections[client_id].discard(websocket)
            logger.info(f"WebSocket client disconnected: {client_id}")
    
    async def broadcast_task_update(self, task_id: str, update_data: dict):
        """广播任务更新到所有连接的客户端"""
        disconnected = set()
        for client_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json({
                        "type": "task_update",
                        "task_id": task_id,
                        "data": update_data
                    })
                except Exception as e:
                    logger.warning(f"Failed to send to client {client_id}: {e}")
                    disconnected.add(connection)
            # 清理断开的连接
            if disconnected:
                self.active_connections[client_id] -= disconnected
        logger.debug(f"Broadcasted task update for {task_id}")

# 创建全局 WebSocket 管理器
manager = ConnectionManager()


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
    # Startup
    logger.info("Starting Quantitative Investment Management System...")
    await MongoDB.connect_to_mongodb()
    yield
    # Shutdown
    logger.info("Shutting down...")
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
