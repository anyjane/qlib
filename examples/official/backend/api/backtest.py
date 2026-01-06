"""Backtest API - 量化回测管理接口"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from loguru import logger

from database import MongoDB
from services.task_pool import get_task_pool_manager
from config import settings

router = APIRouter(prefix="/api/backtest", tags=["Backtest"])


from backtest.type_defs import BacktestConfig


@router.post("/")
async def create_backtest(config: BacktestConfig):
    """
    创建回测任务
    
    Args:
        config: 回测配置
        
    Returns:
        任务信息
    """
    try:
        # 获取任务池管理器
        task_pool_manager = get_task_pool_manager()
        
        if not task_pool_manager.is_initialized():
            raise HTTPException(status_code=500, detail="任务池未初始化")
        
        # 生成任务 ID
        task_id = f"backtest_{datetime.now().strftime('%Y%m%d')}_{datetime.now().timestamp()}"
        
        # 实验名称
        experiment_name = f"backtest_{config.market}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 保存任务到数据库
        task_doc = {
            "task_id": task_id,
            "status": "pending",
            "config": config.dict(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        await MongoDB.insert_backtest_task(task_doc)
        
        # 提交任务到进程池
        task_params = {
            "task_type": "backtest",
            "task_id": task_id,
            "experiment_name": experiment_name,
            "provider_uri": settings.QLIB_PROVIDER_URI,
            "config_json": config.json()
        }
        
        success = task_pool_manager.submit_task(task_params)
        
        if not success:
            raise HTTPException(status_code=500, detail="提交任务到进程池失败")
        
        logger.info(f"Backtest task created: {task_id}")
        
        return {
            "task_id": task_id,
            "status": "started",
            "message": "回测任务已创建",
            "config": task_doc["config"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create backtest task: {e}")
        raise HTTPException(status_code=500, detail=f"创建回测任务失败: {str(e)}")


@router.get("/tasks")
async def get_backtest_tasks(limit: int = Query(50, description="返回数量限制")):
    """
    获取回测任务列表
    
    Args:
        limit: 返回数量限制
        
    Returns:
        任务列表
    """
    try:
        tasks = await MongoDB.get_backtest_tasks(limit=limit)
        
        formatted_tasks = []
        for task in tasks:
            formatted_tasks.append({
                "id": task.get("task_id"),
                "status": task.get("status", "unknown"),
                "market": task.get("config", {}).get("market", "unknown"),
                "train_period": f"{task.get('config', {}).get('train_start', '')} ~ {task.get('config', {}).get('train_end', '')}",
                "test_period": f"{task.get('config', {}).get('test_start', '')} ~ {task.get('config', {}).get('test_end', '')}",
                "created_at": task.get("created_at"),
                "updated_at": task.get("updated_at"),
            })
        
        return formatted_tasks
    except Exception as e:
        logger.error(f"Failed to get backtest tasks: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/tasks/{task_id}")
async def get_backtest_task(task_id: str):
    """
    获取回测任务详情
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务详情
    """
    try:
        task = await MongoDB.get_backtest_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return task
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get backtest task: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/tasks/{task_id}/results")
async def get_backtest_results(task_id: str):
    """
    获取回测结果
    
    Args:
        task_id: 任务ID
        
    Returns:
        回测结果
    """
    try:
        # 检查任务是否存在
        task = await MongoDB.get_backtest_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 获取结果
        results = await MongoDB.get_backtest_results(task_id)
        
        if not results:
            if task.get("status") == "running":
                return {"message": "任务正在执行中，请稍后查询"}
            elif task.get("status") == "failed":
                return {"error": task.get("error", "任务执行失败")}
            else:
                return {"message": "暂无结果"}
        
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get backtest results: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.delete("/tasks/{task_id}")
async def delete_backtest_task(task_id: str):
    """
    删除回测任务
    
    Args:
        task_id: 任务ID
        
    Returns:
        删除结果
    """
    try:
        task = await MongoDB.get_backtest_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        if task.get("status") == "running":
            raise HTTPException(status_code=400, detail="无法删除正在运行的任务")
        
        deleted_count = await MongoDB.delete_backtest_task(task_id)
        
        if deleted_count == 0:
            raise HTTPException(status_code=500, detail="删除失败")
        
        return {"message": "删除成功", "task_id": task_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete backtest task: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.get("/markets")
async def get_available_markets():
    """
    获取可用市场列表
    
    Returns:
        市场列表
    """
    return {
        "markets": [
            {"id": "all", "name": "全部股票", "description": "使用所有启用的股票"},
            {"id": "csi300", "name": "沪深300", "description": "沪深300指数成分股"},
            {"id": "csi500", "name": "中证500", "description": "中证500指数成分股"},
        ]
    }
