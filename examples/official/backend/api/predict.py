"""Prediction API"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from datetime import datetime
from loguru import logger

router = APIRouter(prefix="/api/predict", tags=["Predict"])


@router.post("/")
async def predict(
    background_tasks: BackgroundTasks,
    predict_date: str = None,
    stocks: List[str] = None
):
    """
    执行预测（默认最新数据）

    Args:
        predict_date: 预测日期（默认: 今天）
        stocks: 指定股票代码列表（默认: 所有启用的股票）

    Returns:
        任务信息
    """
    try:
        from ..database import MongoDB

        if predict_date is None:
            predict_date = datetime.now().strftime("%Y-%m-%d")

        # 获取所有启用的股票
        stocks_data = await MongoDB.get_stocks(enabled_only=True)
        stocks = [s["code"] for s in stocks_data] if stocks is None else stocks

        # 创建预测任务
        task_id = f"predict_{predict_date.replace('-', '')}_{datetime.now().timestamp()}"

        # 保存任务到数据库
        await MongoDB.insert_prediction({
            "task_id": task_id,
            "status": "pending",
            "predict_date": predict_date,
            "stocks": stocks,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })

        # 后台执行预测
        logger.info(f"Prediction task created: {task_id}")

        return {
            "task_id": task_id,
            "status": "started",
            "message": "预测任务已创建",
            "predict_date": predict_date,
            "stocks_count": len(stocks)
        }
    except Exception as e:
        logger.error(f"Failed to create prediction task: {e}")
        raise HTTPException(status_code=500, detail=f"创建预测任务失败: {str(e)}")


@router.get("/results")
async def get_predictions(
    date: str = None,
    code: str = None,
    sort_by: str = "score",
    sort_order: str = "desc",
    limit: int = 100,
    filter_type: str = "all"
):
    """
    查询预测结果

    Args:
        date: 预测日期
        code: 股票代码
        sort_by: 排序字段（date, code, name, score）
        sort_order: 排序方式（asc, desc）
        limit: 返回数量限制
        filter_type: 筛选类型（all, held, not_held）

    Returns:
        预测结果列表
    """
    try:
        from ..database import MongoDB

        query = {}
        if date:
            query["date"] = date
        if code:
            query["code"] = code

        # 持仓筛选
        if filter_type != "all":
            from ..database import MongoDB
            positions = await MongoDB.get_positions()
            position_codes = set(p["code"] for p in positions)

            if filter_type == "held":
                query["code"] = {"$in": list(position_codes)}
            elif filter_type == "not_held":
                query["code"] = {"$nin": list(position_codes)}

        # 排序
        sort_order = -1 if sort_order == "desc" else 1
        sort_field = {
            "date": "date",
            "code": "code",
            "name": "name",
            "score": "score",
        }.get(sort_by, "score")

        # 查询预测结果
        cursor = await MongoDB.get_predictions(
            query=query,
            sort=[(sort_field, sort_order)],
            limit=limit
        )

        predictions = await cursor.to_list(length=None)

        # 标记持仓状态
        if filter_type != "all":
            from ..database import MongoDB
            positions = await MongoDB.get_positions()
            position_codes = set(p["code"] for p in positions)

            for pred in predictions:
                pred["is_held"] = pred["code"] in position_codes

        return predictions
    except Exception as e:
        logger.error(f"Failed to get predictions: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/status")
async def get_all_prediction_tasks():
    """查询所有预测任务"""
    try:
        # 返回一个空列表，因为 MongoDB 中没有存储任务
        return []
    except Exception as e:
        logger.error(f"Failed to get prediction tasks: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
