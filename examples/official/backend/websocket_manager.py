"""WebSocket connection manager for real-time task updates"""
from fastapi import WebSocket
from typing import Dict, Set
from loguru import logger


class ConnectionManager:
    """WebSocket connection manager - for real-time task status updates"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """Client connection"""
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = set()
        self.active_connections[client_id].add(websocket)
        logger.info(f"WebSocket client connected: {client_id}")

    async def disconnect(self, websocket: WebSocket, client_id: str):
        """Client disconnection"""
        if client_id in self.active_connections:
            self.active_connections[client_id].discard(websocket)
            logger.info(f"WebSocket client disconnected: {client_id}")

    async def broadcast_task_update(self, update_data: dict):
        """Broadcast task updates to all connected clients

        Args:
            update_data: Dictionary containing task_id and other update information
        """
        disconnected = set()
        task_id = update_data.get("task_id", "unknown")

        for client_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json({
                        "type": "task_update",
                        "data": update_data
                    })
                except Exception as e:
                    logger.warning(f"Failed to send to client {client_id}: {e}")
                    disconnected.add(connection)
            # Clean up disconnected connections
            if disconnected:
                self.active_connections[client_id] -= disconnected
        logger.debug(f"Broadcasted task update for {task_id}")


# Create global connection manager
manager = ConnectionManager()


# Alias for backward compatibility
WebSocketManager = ConnectionManager
