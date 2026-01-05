"""Data management API"""
from fastapi import APIRouter, HTTPException, Body, BackgroundTasks
from typing import List, Optional
from datetime import datetime
from loguru import logger
import pandas as pd

from database import MongoDB
from services.data_service import TencentDataService

router = APIRouter(prefix="/api/data", tags=["Data"])


async def execute_download_task(task_id: str, start_date: str, end_date: str, stocks: List[str]):
    """
    后台执行下载任务

    Args:
        task_id: 任务ID
        start_date: 开始日期
        end_date: 结束日期
        stocks: 股票代码列表
    """
    try:
        logger.info(f"[{task_id}] Starting download task: {start_date} to {end_date}, {len(stocks)} stocks")

        # 更新任务状态为"运行中"
        await MongoDB.update_data_task(task_id, {"status": "running"})

        # 执行下载
        data_dict = await TencentDataService.download_from_tencent(stocks, start_date, end_date)

        # 保存下载的数据到数据库或文件
        # 这里简化处理，只记录成功数量
        success_count = len(data_dict)
        logger.info(f"[{task_id}] Downloaded data for {success_count}/{len(stocks)} stocks")

        # 更新任务状态为"完成"
        await MongoDB.update_data_task(task_id, {
            "status": "completed",
            "progress": 100,
            "downloaded_count": success_count,
            "error": None,
            "updated_at": datetime.utcnow()
        })

        logger.info(f"[{task_id}] Download task completed successfully")

    except Exception as e:
        logger.error(f"[{task_id}] Download task failed: {e}")
        # 更新任务状态为"失败"
        await MongoDB.update_data_task(task_id, {
            "status": "failed",
            "error": str(e),
            "updated_at": datetime.utcnow()
        })


async def execute_update_task(task_id: str, stocks: List[str]):
    """
    后台执行更新任务

    Args:
        task_id: 任务ID
        stocks: 股票代码列表
    """
    try:
        logger.info(f"[{task_id}] Starting update task for {len(stocks)} stocks")

        # 更新任务状态为"运行中"
        await MongoDB.update_data_task(task_id, {"status": "running"})

        # 获取最新数据日期
        end_date = datetime.now().strftime("%Y-%m-%d")
        # 获取已有数据的最新日期，这里简化处理，使用最近30天
        start_date = (datetime.now() - pd.Timedelta(days=30)).strftime("%Y-%m-%d")

        # 执行更新下载
        data_dict = await TencentDataService.download_from_tencent(stocks, start_date, end_date)

        # 记录更新数量
        success_count = len(data_dict)
        logger.info(f"[{task_id}] Updated data for {success_count}/{len(stocks)} stocks")

        # 更新任务状态为"完成"
        await MongoDB.update_data_task(task_id, {
            "status": "completed",
            "progress": 100,
            "updated_count": success_count,
            "error": None,
            "updated_at": datetime.utcnow()
        })

        logger.info(f"[{task_id}] Update task completed successfully")

    except Exception as e:
        logger.error(f"[{task_id}] Update task failed: {e}")
        # 更新任务状态为"失败"
        await MongoDB.update_data_task(task_id, {
            "status": "failed",
            "error": str(e),
            "updated_at": datetime.utcnow()
        })



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
    background_tasks: BackgroundTasks,
    start_date: str = Body(default="2015-01-01"),
    end_date: Optional[str] = Body(default=None),
    stocks: Optional[List[str]] = Body(default=None)
):
    """
    下载数据

    Args:
        background_tasks: FastAPI BackgroundTasks
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

        # 如果未指定股票，获取所有启用的股票
        if stocks is None:
            stocks_data = await MongoDB.get_stocks(enabled_only=True)
            stocks = [s['code'] for s in stocks_data]
            logger.info(f"Downloading data for {len(stocks)} enabled stocks")

        # 创建下载任务
        task_id = await TencentDataService.create_download_task(
            start_date=start_date,
            end_date=end_date,
            stocks=stocks or []
        )

        # 添加后台任务执行下载
        background_tasks.add_task(execute_download_task, task_id, start_date, end_date, stocks or [])

        logger.info(f"Data download task created: {task_id}, background task scheduled")

        return {
            "task_id": task_id,
            "status": "started",
            "message": "数据下载任务已创建",
            "start_date": start_date,
            "end_date": end_date,
            "total_stocks": len(stocks or [])
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create download task: {e}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.post("/update")
async def update_data(
    background_tasks: BackgroundTasks,
    stocks: Optional[List[str]] = Body(default=None)
):
    """
    增量更新数据

    Args:
        background_tasks: FastAPI BackgroundTasks
        stocks: 指定股票代码列表（默认: 所有启用的股票）

    Returns:
        任务信息
    """
    try:
        # 如果未指定股票，获取所有启用的股票
        if stocks is None:
            stocks_data = await MongoDB.get_stocks(enabled_only=True)
            stocks = [s['code'] for s in stocks_data]
            logger.info(f"Updating data for {len(stocks)} enabled stocks")

        # 创建更新任务
        task_id = await TencentDataService.create_update_task(stocks=stocks or [])

        # 添加后台任务执行更新
        background_tasks.add_task(execute_update_task, task_id, stocks or [])

        logger.info(f"Data update task created: {task_id}, background task scheduled")

        return {
            "task_id": task_id,
            "status": "started",
            "message": "数据更新任务已创建",
            "total_stocks": len(stocks or [])
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
