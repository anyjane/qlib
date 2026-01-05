"""Prediction API"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from loguru import logger

from database import MongoDB
from services.qlib_predictor import QlibPredictor
from services.task_pool import get_task_pool_manager
from config import settings
from main import manager

router = APIRouter(prefix="/api/predict", tags=["Predict"])


class PredictRequest(BaseModel):
    """预测请求体"""
    stocks: Optional[List[str]] = None


class LockRequest(BaseModel):
    """锁定状态请求体"""
    is_locked: bool


async def execute_predict_task(task_id: str, predict_date: str, stocks: List[str]):
    """
    后台执行预测任务（已弃用，请使用进程池版本）

    Args:
        task_id: 任务ID
        predict_date: 预测日期
        stocks: 股票代码列表
    """
    try:
        logger.info(f"[{task_id}] Starting prediction task for {len(stocks)} stocks")

        # 更新任务状态为"运行中"
        await MongoDB.update_prediction_task(task_id, {"status": "running"})

        # 使用 Qlib 预测服务
        # 获取股票名称映射
        stocks_data = await MongoDB.get_stocks(enabled_only=True)
        stock_names_map: Dict[str, str] = {s["code"]: s["name"] for s in stocks_data}

        # 创建 Qlib 预测器（使用配置中的路径）
        predictor = QlibPredictor(
            provider_uri=settings.QLIB_PROVIDER_URI,
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
        # 为每个预测结果添加 task_id
        for pred in predictions:
            pred["task_id"] = task_id
        await MongoDB.insert_predictions(predictions)

        # 更新任务状态为"完成"
        await MongoDB.update_prediction_task(task_id, {
            "status": "completed",
            "progress": 100,
            "predicted_count": len(stocks),
            "updated_at": datetime.utcnow()
        })

        # 推送完成状态
        await manager.broadcast_task_update({
            "task_id": task_id,
            "progress": 100,
            "status": "completed",
            "predicted_count": len(stocks)
        })

        logger.info(f"[{task_id}] Prediction task completed successfully")

    except Exception as e:
        logger.error(f"[{task_id}] Prediction task failed: {e}")
        # 更新任务状态为"失败"
        await MongoDB.update_prediction_task(task_id, {
            "status": "failed",
            "error": str(e),
            "updated_at": datetime.utcnow()
        })

        # 推送失败状态
        await manager.broadcast_task_update({
            "task_id": task_id,
            "status": "failed",
            "error": str(e)
        })


@router.post("/")
async def predict(
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
        # 获取任务池管理器
        task_pool_manager = get_task_pool_manager()
        
        # 检查进程池是否已初始化
        if not task_pool_manager.is_initialized():
            raise HTTPException(status_code=500, detail="任务池未初始化，请检查服务启动")
        
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
        await MongoDB.insert_prediction_task({
            "task_id": task_id,
            "status": "pending",
            "predict_date": predict_date,
            "stocks": stocks,
            "is_locked": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })

        # 提交任务到进程池
        task_params = {
            "task_type": "prediction",
            "task_id": task_id,
            "predict_date": predict_date,
            "stocks": stocks
        }
        
        success = task_pool_manager.submit_task(task_params)
        
        if not success:
            raise HTTPException(status_code=500, detail="提交任务到进程池失败")

        logger.info(f"Prediction task created: {task_id}, submitted to process pool")

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


@router.get("/validate")
async def validate_data_date(date: str = Query(..., description="数据日期（格式：YYYY-MM-DD）")):
    """
    验证数据日期

    检查是否有足够的股票数据（超过5个代码无数据则返回错误）

    Args:
        date: 数据日期

    Returns:
        验证结果
    """
    try:
        # 验证日期格式
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式无效，请使用 YYYY-MM-DD 格式")

        # 获取所有启用的股票
        stocks_data = await MongoDB.get_stocks(enabled_only=True)
        all_stocks = [s["code"] for s in stocks_data]

        if not all_stocks:
            raise HTTPException(status_code=400, detail="没有启用的股票代码")

        # 检查是否有预测数据
        query = {"date": date, "code": {"$in": all_stocks}}
        existing_predictions = await MongoDB.get_predictions(query=query)

        existing_codes = set(p["code"] for p in existing_predictions)
        missing_codes = [code for code in all_stocks if code not in existing_codes]

        if len(missing_codes) > 5:
            return {
                "valid": False,
                "error": f"数据不完整：{len(missing_codes)} 个股票代码缺少数据（允许最多5个）",
                "missing_count": len(missing_codes),
                "missing_codes": missing_codes[:10]  # 只返回前10个
            }

        return {
            "valid": True,
            "message": "数据验证通过"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate data date: {e}")
        raise HTTPException(status_code=500, detail=f"验证失败: {str(e)}")


@router.get("/tasks")
async def get_prediction_tasks_list(limit: int = Query(50, description="返回数量限制")):
    """
    获取预测任务列表

    Args:
        limit: 返回数量限制

    Returns:
        预测任务列表
    """
    try:
        tasks = await MongoDB.get_prediction_tasks(limit=limit)

        # 格式化任务列表
        formatted_tasks = []
        for task in tasks:
            formatted_tasks.append({
                "id": task.get("task_id"),
                "start_time": task.get("created_at"),
                "data_date": task.get("predict_date"),
                "status": task.get("status", "unknown"),
                "is_locked": task.get("is_locked", False)
            })

        return formatted_tasks
    except Exception as e:
        logger.error(f"Failed to get prediction tasks: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/tasks/{task_id}/results")
async def get_task_results(task_id: str):
    """
    获取特定任务的预测结果

    Args:
        task_id: 任务ID

    Returns:
        预测结果列表
    """
    try:
        # 检查任务是否存在
        task = await MongoDB.get_prediction_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 获取持仓列表
        positions = await MongoDB.get_positions()
        position_codes = set(p["code"] for p in positions)

        # 获取预测结果
        predictions = await MongoDB.get_prediction_results(task_id)

        # 格式化结果
        formatted_results = []
        for idx, pred in enumerate(predictions, 1):
            formatted_results.append({
                "row_number": idx,
                "stock_code": pred.get("code"),
                "stock_name": pred.get("name"),
                "prediction_score": pred.get("score"),
                "is_held": pred.get("code") in position_codes
            })

        return formatted_results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task results: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.delete("/tasks/{task_id}")
async def delete_prediction_task_endpoint(task_id: str):
    """
    删除预测任务

    Args:
        task_id: 任务ID

    Returns:
        删除结果
    """
    try:
        # 检查任务是否存在
        task = await MongoDB.get_prediction_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 检查是否锁定
        if task.get("is_locked", False):
            raise HTTPException(status_code=403, detail="任务已锁定，无法删除")

        # 删除任务
        deleted_count = await MongoDB.delete_prediction_task(task_id)

        if deleted_count == 0:
            raise HTTPException(status_code=500, detail="删除失败")

        return {"message": "删除成功", "task_id": task_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete prediction task: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.put("/tasks/{task_id}/lock")
async def update_task_lock_status(task_id: str, request_data: LockRequest):
    """
    更新任务锁定状态

    Args:
        task_id: 任务ID
        request_data: 锁定状态请求

    Returns:
        更新结果
    """
    try:
        # 检查任务是否存在
        task = await MongoDB.get_prediction_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 更新锁定状态
        await MongoDB.update_prediction_task(task_id, {
            "is_locked": request_data.is_locked,
            "updated_at": datetime.utcnow()
        })

        return {
            "message": "更新成功",
            "task_id": task_id,
            "is_locked": request_data.is_locked
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update task lock status: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")
