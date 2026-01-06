"""MongoDB database operations"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
from config import settings


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
        cursor = cls.database.stocks.find(query, {"_id": 0})
        stocks = await cursor.to_list(length=None)
        # Ensure data types match Pydantic models
        for stock in stocks:
            if "code" in stock and stock["code"] is not None:
                stock["code"] = str(stock["code"])
            if "name" in stock and stock["name"] is not None:
                stock["name"] = str(stock["name"])
        return stocks

    @classmethod
    async def get_stock(cls, code: str) -> Optional[Dict]:
        """Get stock by code"""
        stock = await cls.database.stocks.find_one({"code": code}, {"_id": 0})
        if stock and "name" in stock and stock["name"] is not None:
            stock["name"] = str(stock["name"])
        if stock and "code" in stock and stock["code"] is not None:
            stock["code"] = str(stock["code"])
        return stock

    @classmethod
    async def insert_stock(cls, stock_dict: Dict):
        """Insert a stock"""
        await cls.database.stocks.insert_one(stock_dict)

    @classmethod
    async def update_stock(cls, code: str, update_dict: Dict) -> bool:
        """Update a stock"""
        result = await cls.database.stocks.update_one(
            {"code": code},
            {"$set": update_dict}
        )
        return result.modified_count > 0

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
    # Backtest Task Collection Operations
    # ============================================================================

    @classmethod
    async def insert_backtest_task(cls, task_dict: Dict):
        """Insert a backtest task"""
        await cls.database.backtest_tasks.insert_one(task_dict)
        logger.info(f"Inserted backtest task: {task_dict.get('task_id')}")

    @classmethod
    async def get_backtest_tasks(cls, limit: int = 50) -> List[Dict]:
        """Get backtest tasks"""
        cursor = cls.database.backtest_tasks.find().sort("created_at", -1).limit(limit)
        tasks = await cursor.to_list(length=None)
        return tasks

    @classmethod
    async def get_backtest_task(cls, task_id: str) -> Optional[Dict]:
        """Get backtest task by ID"""
        task = await cls.database.backtest_tasks.find_one({"task_id": task_id})
        return task

    @classmethod
    async def delete_backtest_task(cls, task_id: str) -> int:
        """Delete a backtest task"""
        result = await cls.database.backtest_tasks.delete_one({"task_id": task_id})
        return result.deleted_count

    # ============================================================================
    # Backtest Result Collection Operations
    # ============================================================================

    @classmethod
    async def insert_backtest_result(cls, result_dict: Dict):
        """Insert a backtest result"""
        await cls.database.backtest_results.insert_one(result_dict)
        logger.info(f"Inserted backtest result: {result_dict.get('task_id')}")

    @classmethod
    async def get_backtest_result(cls, task_id: str) -> Optional[Dict]:
        """Get backtest result by ID"""
        result = await cls.database.backtest_results.find_one({"task_id": task_id}, {"_id": 0})
        return result

    @classmethod
    async def get_all_backtest_results(cls, limit: int = 20, market: Optional[str] = None) -> List[Dict]:
        """Get all backtest results"""
        query = {}
        if market:
            query["config.market"] = market

        cursor = cls.database.backtest_results.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
        results = await cursor.to_list(length=None)
        return results

    @classmethod
    async def delete_backtest_result(cls, task_id: str) -> int:
        """Delete a backtest result"""
        result = await cls.database.backtest_results.delete_one({"task_id": task_id})
        return result.deleted_count

    # ============================================================================
    # Position Collection Operations
    # ============================================================================

    @classmethod
    async def get_positions(cls) -> List[Dict]:
        """Get all positions"""
        cursor = cls.database.local_positions.find({}, {"_id": 0})
        positions = await cursor.to_list(length=None)
        for pos in positions:
            if "code" in pos and pos["code"] is not None:
                pos["code"] = str(pos["code"])
            if "name" in pos and pos["name"] is not None:
                pos["name"] = str(pos["name"])
        return positions

    @classmethod
    async def get_position(cls, code: str) -> Optional[Dict]:
        """Get position by code"""
        pos = await cls.database.local_positions.find_one({"code": code}, {"_id": 0})
        if pos and "name" in pos and pos["name"] is not None:
            pos["name"] = str(pos["name"])
        if pos and "code" in pos and pos["code"] is not None:
            pos["code"] = str(pos["code"])
        return pos

    @classmethod
    async def insert_position(cls, position_dict: Dict):
        """Insert a position"""
        await cls.database.local_positions.insert_one(position_dict)

    @classmethod
    async def update_position(cls, code: str, update_dict: Dict) -> bool:
        """Update a position"""
        result = await cls.database.local_positions.update_one(
            {"code": code},
            {"$set": update_dict}
        )
        return result.modified_count > 0

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
        cursor = cls.database.predictions.find(query or {}, {"_id": 0})

        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)

        predictions = await cursor.to_list(length=None)
        for pred in predictions:
            if "code" in pred and pred["code"] is not None:
                pred["code"] = str(pred["code"])
            if "name" in pred and pred["name"] is not None:
                pred["name"] = str(pred["name"])
        return predictions if predictions else []

    @classmethod
    async def insert_prediction(cls, prediction_dict: Dict):
        """Insert a prediction"""
        await cls.database.predictions.insert_one(prediction_dict)

    @classmethod
    async def insert_predictions(cls, predictions_list: List[Dict]):
        """Insert multiple predictions"""
        if predictions_list:
            await cls.database.predictions.insert_many(predictions_list)

    @classmethod
    async def update_prediction(cls, task_id: str, update_dict: Dict):
        """Update prediction task by task_id"""
        await cls.database.predictions.update_one(
            {"task_id": task_id},
            {"$set": update_dict}
        )

    # ============================================================================
    # Agent Config Collection Operations
    # ============================================================================

    @classmethod
    async def get_all_agent_configs(cls) -> List[Dict]:
        """Get all agent configs"""
        cursor = cls.database.agent_configs.find({}, {"_id": 0})
        return await cursor.to_list(length=None)

    @classmethod
    async def get_agent_config(cls, agent_id: str) -> Optional[Dict]:
        """Get agent config by ID"""
        return await cls.database.agent_configs.find_one({"agent_id": agent_id}, {"_id": 0})

    @classmethod
    async def create_agent_config(cls, agent_dict: Dict):
        """Create agent config"""
        await cls.database.agent_configs.insert_one(dict(agent_dict))

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
        return await cls.database.agent_configs.find_one({"is_primary": True}, {"_id": 0})

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
        return await cls.database.data_tasks.find_one({"task_id": task_id}, {"_id": 0})

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
        cursor = cls.database.data_tasks.find({}, {"_id": 0})
        return await cursor.to_list(length=None)

    # ============================================================================
    # Prediction Tasks Collection Operations
    # ============================================================================

    @classmethod
    async def get_prediction_tasks(cls, limit: int = None) -> List[Dict]:
        """Get all prediction tasks"""
        cursor = cls.database.prediction_tasks.find({}, {"_id": 0}).sort("created_at", -1)
        if limit:
            cursor = cursor.limit(limit)
        tasks = await cursor.to_list(length=None)
        return tasks if tasks else []

    @classmethod
    async def get_prediction_task(cls, task_id: str) -> Optional[Dict]:
        """Get prediction task by ID"""
        task = await cls.database.prediction_tasks.find_one({"task_id": task_id}, {"_id": 0})
        return task

    @classmethod
    async def insert_prediction_task(cls, task_dict: Dict):
        """Insert a prediction task"""
        await cls.database.prediction_tasks.insert_one(task_dict)

    @classmethod
    async def update_prediction_task(cls, task_id: str, update_dict: Dict):
        """Update prediction task"""
        await cls.database.prediction_tasks.update_one(
            {"task_id": task_id},
            {"$set": update_dict}
        )

    @classmethod
    async def delete_prediction_task(cls, task_id: str) -> int:
        """Delete prediction task"""
        result = await cls.database.prediction_tasks.delete_one({"task_id": task_id})
        return result.deleted_count

    @classmethod
    async def get_prediction_results(cls, task_id: str) -> List[Dict]:
        """Get prediction results by task_id"""
        query = {"task_id": task_id}
        predictions = await cls.get_predictions(query=query, sort=[("score", -1)], limit=None)
        return predictions

    # ============================================================================
    # Backtest Tasks Collection Operations
    # ============================================================================

    @classmethod
    async def get_backtest_tasks(cls, limit: int = None) -> List[Dict]:
        """Get all backtest tasks"""
        cursor = cls.database.backtest_tasks.find({}, {"_id": 0}).sort("created_at", -1)
        if limit:
            cursor = cursor.limit(limit)
        tasks = await cursor.to_list(length=None)
        return tasks if tasks else []

    @classmethod
    async def get_backtest_task(cls, task_id: str) -> Optional[Dict]:
        """Get backtest task by ID"""
        task = await cls.database.backtest_tasks.find_one({"task_id": task_id}, {"_id": 0})
        return task

    @classmethod
    async def insert_backtest_task(cls, task_dict: Dict):
        """Insert a backtest task"""
        await cls.database.backtest_tasks.insert_one(task_dict)

    @classmethod
    async def update_backtest_task(cls, task_id: str, update_dict: Dict):
        """Update backtest task"""
        await cls.database.backtest_tasks.update_one(
            {"task_id": task_id},
            {"$set": update_dict}
        )

    @classmethod
    async def delete_backtest_task(cls, task_id: str) -> int:
        """Delete backtest task and its results"""
        # Delete task
        result = await cls.database.backtest_tasks.delete_one({"task_id": task_id})
        # Also delete associated results
        await cls.database.backtest_results.delete_many({"task_id": task_id})
        return result.deleted_count

    @classmethod
    async def get_backtest_results(cls, task_id: str) -> Optional[Dict]:
        """Get backtest results by task_id"""
        result = await cls.database.backtest_results.find_one({"task_id": task_id}, {"_id": 0})
        return result

    @classmethod
    async def insert_backtest_results(cls, results_dict: Dict):
        """Insert backtest results"""
        await cls.database.backtest_results.insert_one(results_dict)
