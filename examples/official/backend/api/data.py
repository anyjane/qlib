"""Data management API"""
from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional
from datetime import datetime
from loguru import logger
from pydantic import BaseModel
import pandas as pd

from database import MongoDB
from services.data_service import TencentDataService
from services.task_pool import get_task_pool_manager
from websocket_manager import manager

router = APIRouter(prefix="/api/data", tags=["Data"])


class StockListRequest(BaseModel):
    """股票列表请求体"""
    stocks: Optional[List[str]] = None


class DownloadRequest(BaseModel):
    """下载数据请求体"""
    start_date: str = "2015-01-01"
    end_date: Optional[str] = None
    stocks: Optional[List[str]] = None


class DeleteRequest(BaseModel):
    """删除数据请求体"""
    stocks: List[str]


async def execute_download_task(task_id: str, start_date: str, end_date: str, stocks: List[str]):
    """
    后台执行下载任务

    Args:
        task_id: 任务ID
        start_date: 开始日期
        end_date: 结束日期
        stocks: 股票代码列表
    """
    all_data_dict = {}

    try:
        logger.info(f"[{task_id}] Starting download task: {start_date} to {end_date}, {len(stocks)} stocks")

        # 更新任务状态为"运行中"
        await MongoDB.update_data_task(task_id, {"status": "running"})

        total_stocks = len(stocks)
        # 逐个股票下载并推送进度
        for idx, code in enumerate(stocks):
            try:
                # 下载单个股票
                data_dict = await TencentDataService.download_from_tencent([code], start_date, end_date)
                all_data_dict.update(data_dict)

                # 推送进度
                progress = int((idx + 1) / total_stocks * 100)
                await manager.broadcast_task_update(task_id, {
                    "progress": progress,
                    "current_stock": code,
                    "downloaded_count": idx + 1,
                    "total_count": total_stocks,
                    "status": "running"
                })
                logger.debug(f"[{task_id}] Downloaded {idx + 1}/{total_stocks}: {code}")
            except Exception as e:
                logger.error(f"[{task_id}] Failed to download {code}: {e}")

        # 所有下载完成后，将数据保存为 Qlib 格式
        logger.info(f"[{task_id}] Download completed, saving to Qlib format...")
        await manager.broadcast_task_update(task_id, {
            "progress": 95,
            "status": "saving",
            "message": "正在保存数据到 Qlib 格式"
        })

        save_results = TencentDataService.save_data_to_qlib_format(all_data_dict, start_date, end_date)

        # 更新任务状态为"完成"
        await MongoDB.update_data_task(task_id, {
            "status": "completed",
            "progress": 100,
            "downloaded_count": total_stocks,
            "error": None,
            "updated_at": datetime.utcnow()
        })

        # 最终推送完成状态
        await manager.broadcast_task_update(task_id, {
            "progress": 100,
            "status": "completed",
            "downloaded_count": total_stocks,
            "save_results": save_results
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

        # 推送失败状态
        await manager.broadcast_task_update(task_id, {
            "status": "failed",
            "error": str(e)
        })


async def execute_update_task(task_id: str, stocks: List[str]):
    """
    后台执行更新任务

    Args:
        task_id: 任务ID
        stocks: 股票代码列表
    """
    all_data_dict = {}
    # 记录每个股票实际下载的日期范围
    stock_download_ranges = {}

    try:
        logger.info(f"[{task_id}] Starting update task for {len(stocks)} stocks")

        # 更新任务状态为"运行中"
        await MongoDB.update_data_task(task_id, {"status": "running"})

        # 获取最新数据日期（当前日期）
        end_date = datetime.now().strftime("%Y-%m-%d")

        # 获取已有数据的最新日期，从该日期的下一天开始更新
        # 默认使用最近 90 天（如果无法获取已有数据日期）
        default_start_date = "2015-01-01"  # 使用固定的开始日期，避免问题

        total_stocks = len(stocks)
        # 逐个股票更新并推送进度
        for idx, code in enumerate(stocks):
            try:
                # 获取该股票的已有数据结束日期
                data_info = await TencentDataService.get_stock_data_info(code)
                if data_info.get("has_data"):
                    # 从已有数据的结束日期的下一天开始
                    end_date_str = data_info.get("end_date")
                    if end_date_str:
                        end_date_ts = pd.Timestamp(end_date_str)
                        start_date = (end_date_ts + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
                        logger.info(f"[{code}] 已有数据到 {end_date_str}，从 {start_date} 开始更新")
                    else:
                        start_date = default_start_date
                else:
                    # 没有数据，使用默认开始日期
                    start_date = default_start_date
                    logger.info(f"[{code}] 无已有数据，从 {start_date} 开始下载")

                # 更新单个股票
                data_dict = await TencentDataService.download_from_tencent([code], start_date, end_date)
                all_data_dict.update(data_dict)

                # 记录实际下载的日期范围
                if code in data_dict and data_dict[code].get("count", 0) > 0:
                    stock_download_ranges[code] = {"start": start_date, "end": end_date}

                # 推送进度
                progress = int((idx + 1) / total_stocks * 100)
                await manager.broadcast_task_update(task_id, {
                    "progress": progress,
                    "current_stock": code,
                    "updated_count": idx + 1,
                    "total_count": total_stocks,
                    "status": "running"
                })
                logger.debug(f"[{task_id}] Updated {idx + 1}/{total_stocks}: {code}")
            except Exception as e:
                logger.error(f"[{task_id}] Failed to update {code}: {e}")

        # 所有更新完成后，将数据保存为 Qlib 格式
        logger.info(f"[{task_id}] Update completed, saving to Qlib format...")
        await manager.broadcast_task_update(task_id, {
            "progress": 95,
            "status": "saving",
            "message": "正在保存数据到 Qlib 格式"
        })

        # 使用实际下载的日期范围来保存，并使用 update 模式
        save_results = TencentDataService.save_data_to_qlib_format(
            all_data_dict,
            stock_download_ranges,
            end_date,
            use_update_mode=True  # 使用 dump_update 模式进行增量更新
        )

        # 更新任务状态为"完成"
        await MongoDB.update_data_task(task_id, {
            "status": "completed",
            "progress": 100,
            "updated_count": total_stocks,
            "error": None,
            "updated_at": datetime.utcnow()
        })

        # 最终推送完成状态
        await manager.broadcast_task_update(task_id, {
            "progress": 100,
            "status": "completed",
            "updated_count": total_stocks,
            "save_results": save_results
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

        # 推送失败状态
        await manager.broadcast_task_update(task_id, {
            "status": "failed",
            "error": str(e)
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
async def download_data(request_data: DownloadRequest):
    """
    下载数据

    Args:
        request_data: 请求数据，包含日期范围和股票列表

    Returns:
        任务信息
    """
    # 固定开始日期为 2015-01-01
    start_date = "2015-01-01"
    # 结束日期为当前日期
    end_date = datetime.now().strftime("%Y-%m-%d")
    stocks = request_data.stocks

    try:
        # 获取任务池管理器
        task_pool_manager = get_task_pool_manager()
        
        # 检查进程池是否已初始化
        if not task_pool_manager.is_initialized():
            raise HTTPException(status_code=500, detail="任务池未初始化，请检查服务启动")

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

        # 提交任务到进程池
        task_params = {
            "task_type": "data_download",
            "task_id": task_id,
            "start_date": start_date,
            "end_date": end_date,
            "stocks": stocks or []
        }
        
        success = task_pool_manager.submit_task(task_params)
        
        if not success:
            raise HTTPException(status_code=500, detail="提交任务到进程池失败")

        logger.info(f"Data download task created: {task_id}, submitted to process pool")

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
async def update_data(request_data: StockListRequest):
    """
    增量更新数据

    Args:
        request_data: 请求数据，包含股票列表

    Returns:
        任务信息
    """
    stocks = request_data.stocks

    try:
        # 获取任务池管理器
        task_pool_manager = get_task_pool_manager()
        
        # 检查进程池是否已初始化
        if not task_pool_manager.is_initialized():
            raise HTTPException(status_code=500, detail="任务池未初始化，请检查服务启动")

        # 如果未指定股票，获取所有启用的股票
        if stocks is None:
            stocks_data = await MongoDB.get_stocks(enabled_only=True)
            stocks = [s['code'] for s in stocks_data]
            logger.info(f"Updating data for {len(stocks)} enabled stocks")

        # 创建更新任务
        task_id = await TencentDataService.create_update_task(stocks=stocks or [])

        # 提交任务到进程池
        task_params = {
            "task_type": "data_update",
            "task_id": task_id,
            "stocks": stocks or []
        }
        
        success = task_pool_manager.submit_task(task_params)
        
        if not success:
            raise HTTPException(status_code=500, detail="提交任务到进程池失败")

        logger.info(f"Data update task created: {task_id}, submitted to process pool")

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


@router.get("/stocks/status")
async def get_stocks_data_status():
    """获取所有股票的数据状态（从 Qlib 读取）"""
    try:
        stocks = await MongoDB.get_stocks(enabled_only=True)
        result = []
        for stock in stocks:
            data_info = await TencentDataService.get_stock_data_info(stock['code'])
            result.append({
                "code": stock['code'],
                "name": stock['name'],
                "enabled": stock['enabled'],
                "has_data": data_info['has_data'],
                "data_start_date": data_info.get('start_date'),
                "data_end_date": data_info.get('end_date'),
                "data_count": data_info.get('count', 0)
            })
        return result
    except Exception as e:
        logger.error(f"Failed to get stocks data status: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.post("/delete")
async def delete_stocks_data(request_data: DeleteRequest):
    """删除指定股票的数据（数据库 + Qlib 文件）"""
    stocks = request_data.stocks
    try:
        results = []
        for code in stocks:
            try:
                # 删除 Qlib 数据文件
                await TencentDataService.delete_stock_data(code)
                # 更新数据库状态
                await MongoDB.update_stock(code, {
                    "has_data": False,
                    "data_start_date": None,
                    "data_end_date": None
                })
                results.append({"code": code, "success": True})
                logger.info(f"Deleted data for stock: {code}")
            except Exception as e:
                results.append({"code": code, "success": False, "error": str(e)})
                logger.error(f"Failed to delete data for {code}: {e}")
        return {"results": results}
    except Exception as e:
        logger.error(f"Failed to delete stocks data: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
