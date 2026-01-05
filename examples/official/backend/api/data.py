"""Data management API"""
from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional
from datetime import datetime
from loguru import logger

from database import MongoDB
from services.data_service import TencentDataService

router = APIRouter(prefix="/api/data", tags=["Data"])


@router.get("/latest_date")
async def get_latest_data_date():
    """获取最新数据日期"""
    try:
        latest_date = await TencentDataService.get_latest_data_date()
        return {"latest_date": latest_date}
    except Exception as e:
        logger.error(f"Failed to get latest data date: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.post("/download")
async def download_data(
    start_date: str = "2015-01-01",
    end_date: Optional[str] = None,
    stocks: Optional[List[str]] = Body(default=None)
):
    """
    下载数据

    Args:
        start_date: 开始日期（默认: 2015-01-01）
        end_date: 结束日期（默认: 今天）
        stocks: 指定股票代码列表（默认: 所有启用的股票）

    Returns:
        任务信息
    """
    try:
        # 验证日期格式
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式无效，请使用 YYYY-MM-DD 格式")

        if end_date is not None:
            try:
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="日期格式无效，请使用 YYYY-MM-DD 格式")

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        # 创建下载任务
        task_id = await TencentDataService.create_download_task(
            start_date=start_date,
            end_date=end_date,
            stocks=stocks
        )

        # 后台执行下载
        # 注意：在生产环境中应该使用 BackgroundTasks 或 Celery
        logger.info(f"Data download task created: {task_id}")

        return {
            "task_id": task_id,
            "status": "started",
            "message": "数据下载任务已创建",
            "start_date": start_date,
            "end_date": end_date
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create download task: {e}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.post("/update")
async def update_data(
    stocks: Optional[List[str]] = Body(default=None)
):
    """
    增量更新数据

    Args:
        stocks: 指定股票代码列表（默认: 所有启用的股票）

    Returns:
        任务信息
    """
    try:
        # 创建更新任务
        task_id = await TencentDataService.create_update_task(stocks=stocks)

        # 后台执行更新
        logger.info(f"Data update task created: {task_id}")

        return {
            "task_id": task_id,
            "status": "started",
            "message": "数据更新任务已创建"
        }
    except Exception as e:
        logger.error(f"Failed to create update task: {e}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """查询任务状态"""
    try:
        task = await MongoDB.get_data_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        return task
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/status")
async def get_all_tasks():
    """查询所有下载任务状态"""
    try:
        tasks = await MongoDB.get_all_data_tasks()
        return tasks
    except Exception as e:
        logger.error(f"Failed to get all tasks: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
