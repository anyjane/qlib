"""Prediction API"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from loguru import logger

from database import MongoDB
from main import manager
from services.qlib_predictor import QlibPredictor

router = APIRouter(prefix="/api/predict", tags=["Predict"])


class PredictRequest(BaseModel):
    """预测请求体"""
    stocks: Optional[List[str]] = None


async def execute_predict_task(task_id: str, predict_date: str, stocks: List[str]):
    """
    后台执行预测任务

    Args:
        task_id: 任务ID
        predict_date: 预测日期
        stocks: 股票代码列表
    """
    try:
        logger.info(f"[{task_id}] Starting prediction task for {len(stocks)} stocks")

        # 更新任务状态为"运行中"
        await MongoDB.update_prediction(task_id, {"status": "running"})

        # 使用 Qlib 预测服务
        # 获取股票名称映射
        stocks_data = await MongoDB.get_stocks(enabled_only=True)
        stock_names_map: Dict[str, str] = {s["code"]: s["name"] for s in stocks_data}

        # 创建 Qlib 预测器
        predictor = QlibPredictor(
            provider_uri="~/.qlib/tencent_data/qlib_data",
            experiment_name=f"prediction_{task_id}"
        )

        # 执行预测
        logger.info(f"[{task_id}] Calling Qlib prediction service for {len(stocks)} stocks")
        result = predictor.predict(
            predict_date=predict_date,
            stock_codes=stocks,
            stock_names_map=stock_names_map
        )

        # 转换预测结果
        predictions = []
        for pred in result['predictions']:
            predictions.append({
                "date": predict_date,
                "code": pred['code'],
                "name": pred['name'],
                "score": pred['score'],
                "execution_timestamp": result['execution_timestamp'],
                "data_date": result['data_date'],
                "created_at": datetime.utcnow()
            })

        logger.info(f"[{task_id}] Qlib prediction completed: {len(predictions)} predictions")
        if result.get('outliers'):
            logger.warning(f"[{task_id}] Found outliers: {result['outliers']}")

        # 保存预测结果到数据库
        logger.info(f"[{task_id}] Saving {len(predictions)} predictions to database")
        await MongoDB.insert_predictions(predictions)

        # 更新任务状态为"完成"
        await MongoDB.update_prediction(task_id, {
            "status": "completed",
            "progress": 100,
            "predicted_count": len(stocks),
            "updated_at": datetime.utcnow()
        })

        # 推送完成状态
        await manager.broadcast_task_update(task_id, {
            "progress": 100,
            "status": "completed",
            "predicted_count": len(stocks)
        })

        logger.info(f"[{task_id}] Prediction task completed successfully")

    except Exception as e:
        logger.error(f"[{task_id}] Prediction task failed: {e}")
        # 更新任务状态为"失败"
        await MongoDB.update_prediction(task_id, {
            "status": "failed",
            "error": str(e),
            "updated_at": datetime.utcnow()
        })

        # 推送失败状态
        await manager.broadcast_task_update(task_id, {
            "status": "failed",
            "error": str(e)
        })


@router.post("/")
async def predict(
    background_tasks: BackgroundTasks,
    predict_date: Optional[str] = Query(None, description="预测日期（默认: 今天）"),
    request_data: PredictRequest = None
):
    """
    执行预测（默认最新数据）

    Args:
        predict_date: 预测日期（默认: 今天）
        request_data: 请求数据，包含股票代码列表（默认: 所有启用的股票）

    Returns:
        任务信息
    """
    # 从请求体中提取股票列表
    stocks = request_data.stocks if request_data else None
    try:
        if predict_date is None:
            predict_date = datetime.now().strftime("%Y-%m-%d")
        else:
            # 验证日期格式
            try:
                datetime.strptime(predict_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="日期格式无效，请使用 YYYY-MM-DD 格式")

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

        # 添加后台任务执行预测
        background_tasks.add_task(execute_predict_task, task_id, predict_date, stocks)

        logger.info(f"Prediction task created: {task_id}, background task scheduled")

        return {
            "task_id": task_id,
            "status": "started",
            "message": "预测任务已创建",
            "predict_date": predict_date,
            "stocks_count": len(stocks)
        }
    except HTTPException:
        raise
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
        # 如果 limit 为 0，直接返回空列表
        if limit == 0:
            return []

        query = {}
        if date:
            query["date"] = date
        if code:
            query["code"] = code

        # 持仓筛选
        if filter_type != "all":
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
        predictions = await MongoDB.get_predictions(
            query=query,
            sort=[(sort_field, sort_order)],
            limit=limit
        )

        # 标记持仓状态
        if filter_type != "all":
            positions = await MongoDB.get_positions()
            position_codes = set(p["code"] for p in positions)

            for pred in predictions:
                pred["is_held"] = pred["code"] in position_codes

        return predictions if predictions else []
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
