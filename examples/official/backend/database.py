"""MongoDB database operations"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
from ..config import settings


class MongoDB:
    """MongoDB async operations"""

    client: Optional[AsyncIOMotorClient] = None
    database = None

    @classmethod
    async def connect_to_mongodb(cls):
        """Connect to MongoDB"""
        if cls.client is None:
            cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
            cls.database = cls.client[settings.MONGODB_DB_NAME]
            logger.info(f"Connected to MongoDB: {settings.MONGODB_DB_NAME}")

    @classmethod
    async def close_mongodb(cls):
        """Close MongoDB connection"""
        if cls.client is not None:
            cls.client.close()
            logger.info("MongoDB connection closed")

    # ============================================================================
    # Stock Collection Operations
    # ============================================================================

    @classmethod
    async def get_stocks(cls, enabled_only: bool = False) -> List[Dict]:
        """Get all stocks"""
        query = {"enabled": True} if enabled_only else {}
        cursor = cls.database.stocks.find(query)
        return await cursor.to_list(length=None)

    @classmethod
    async def get_stock(cls, code: str) -> Optional[Dict]:
        """Get stock by code"""
        return await cls.database.stocks.find_one({"code": code})

    @classmethod
    async def insert_stock(cls, stock_dict: Dict):
        """Insert a stock"""
        await cls.database.stocks.insert_one(stock_dict)

    @classmethod
    async def update_stock(cls, code: str, update_dict: Dict):
        """Update a stock"""
        await cls.database.stocks.update_one(
            {"code": code},
            {"$set": update_dict}
        )

    @classmethod
    async def delete_stock(cls, code: str) -> bool:
        """Delete a stock"""
        result = await cls.database.stocks.delete_one({"code": code})
        return result.deleted_count > 0

    @classmethod
    async def clear_all_stocks(cls):
        """Clear all stocks"""
        result = await cls.database.stocks.delete_many({})
        logger.info(f"Cleared all stocks: {result.deleted_count} records")
        return result.deleted_count

    @classmethod
    async def batch_update_stocks(cls, codes: List[str], update_dict: Dict) -> int:
        """Batch update stocks"""
        result = await cls.database.stocks.update_many(
            {"code": {"$in": codes}},
            {"$set": update_dict}
        )
        logger.info(f"Batch updated {result.modified_count} stocks")
        return result.modified_count

    @classmethod
    async def batch_delete_stocks(cls, codes: List[str]) -> int:
        """Batch delete stocks"""
        result = await cls.database.stocks.delete_many({"code": {"$in": codes}})
        logger.info(f"Batch deleted {result.deleted_count} stocks")
        return result.deleted_count

    # ============================================================================
    # Position Collection Operations
    # ============================================================================

    @classmethod
    async def get_positions(cls) -> List[Dict]:
        """Get all positions"""
        cursor = cls.database.local_positions.find({})
        return await cursor.to_list(length=None)

    @classmethod
    async def get_position(cls, code: str) -> Optional[Dict]:
        """Get position by code"""
        return await cls.database.local_positions.find_one({"code": code})

    @classmethod
    async def insert_position(cls, position_dict: Dict):
        """Insert a position"""
        await cls.database.local_positions.insert_one(position_dict)

    @classmethod
    async def update_position(cls, code: str, update_dict: Dict):
        """Update a position"""
        await cls.database.local_positions.update_one(
            {"code": code},
            {"$set": update_dict}
        )

    @classmethod
    async def delete_position(cls, code: str) -> bool:
        """Delete a position"""
        result = await cls.database.local_positions.delete_one({"code": code})
        return result.deleted_count > 0

    @classmethod
    async def clear_all_local_positions(cls) -> int:
        """Clear all local positions"""
        result = await cls.database.local_positions.delete_many({})
        logger.info(f"Cleared all local positions: {result.deleted_count} records")
        return result.deleted_count

    @classmethod
    async def batch_delete_positions(cls, codes: List[str]) -> int:
        """Batch delete positions"""
        result = await cls.database.local_positions.delete_many({"code": {"$in": codes}})
        logger.info(f"Batch deleted {result.deleted_count} positions")
        return result.deleted_count

    @classmethod
    async def batch_update_positions(cls, codes: List[str], update_data: Dict) -> int:
        """Batch update positions"""
        result = await cls.database.local_positions.update_many(
            {"code": {"$in": codes}},
            {"$set": update_data}
        )
        logger.info(f"Batch updated {result.modified_count} positions")
        return result.modified_count

    # ============================================================================
    # Prediction Collection Operations
    # ============================================================================

    @classmethod
    async def get_predictions(
        cls,
        query: Dict = None,
        sort: List[tuple] = None,
        limit: int = None
    ):
        """Get predictions with filtering and sorting"""
        cursor = cls.database.predictions.find(query or {})

        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)

        return cursor

    @classmethod
    async def insert_prediction(cls, prediction_dict: Dict):
        """Insert a prediction"""
        await cls.database.predictions.insert_one(prediction_dict)

    # ============================================================================
    # Agent Config Collection Operations
    # ============================================================================

    @classmethod
    async def get_all_agent_configs(cls) -> List[Dict]:
        """Get all agent configs"""
        cursor = cls.database.agent_configs.find({})
        return await cursor.to_list(length=None)

    @classmethod
    async def get_agent_config(cls, agent_id: str) -> Optional[Dict]:
        """Get agent config by ID"""
        return await cls.database.agent_configs.find_one({"agent_id": agent_id})

    @classmethod
    async def create_agent_config(cls, agent_dict: Dict):
        """Create agent config"""
        await cls.database.agent_configs.insert_one(agent_dict)

    @classmethod
    async def update_agent_config(cls, agent_id: str, update_dict: Dict):
        """Update agent config"""
        await cls.database.agent_configs.update_one(
            {"agent_id": agent_id},
            {"$set": update_dict}
        )

    @classmethod
    async def delete_agent_config(cls, agent_id: str) -> int:
        """Delete agent config"""
        result = await cls.database.agent_configs.delete_one({"agent_id": agent_id})
        return result.deleted_count

    @classmethod
    async def update_all_agents_primary(cls, primary_agent_id: str):
        """Set all agents to secondary, except primary"""
        await cls.database.agent_configs.update_many(
            {"agent_id": {"$ne": primary_agent_id}},
            {"$set": {"is_primary": False}}
        )

    @classmethod
    async def get_primary_agent_config(cls) -> Optional[Dict]:
        """Get primary agent config"""
        return await cls.database.agent_configs.find_one({"is_primary": True})

    @classmethod
    async def update_agent_heartbeat(cls, agent_id: str):
        """Update agent heartbeat timestamp"""
        await cls.database.agent_configs.update_one(
            {"agent_id": agent_id},
            {"$set": {
                "last_heartbeat": datetime.utcnow(),
                "status": "active"
            }}
        )

    @classmethod
    async def update_agent_status(cls, agent_id: str, status: str):
        """Update agent status"""
        await cls.database.agent_configs.update_one(
            {"agent_id": agent_id},
            {"$set": {"status": status}}
        )

    # ============================================================================
    # Data Task Collection Operations
    # ============================================================================

    @classmethod
    async def insert_data_task(cls, task_dict: Dict):
        """Insert a data task"""
        await cls.database.data_tasks.insert_one(task_dict)

    @classmethod
    async def get_data_task(cls, task_id: str) -> Optional[Dict]:
        """Get data task by ID"""
        return await cls.database.data_tasks.find_one({"task_id": task_id})

    @classmethod
    async def update_data_task(cls, task_id: str, update_dict: Dict):
        """Update data task"""
        await cls.database.data_tasks.update_one(
            {"task_id": task_id},
            {"$set": update_dict}
        )

    @classmethod
    async def get_all_data_tasks(cls) -> List[Dict]:
        """Get all data tasks"""
        cursor = cls.database.data_tasks.find({})
        return await cursor.to_list(length=None)
