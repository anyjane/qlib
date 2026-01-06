"""Backtest API - 量化回测管理接口"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from loguru import logger
import io
import csv
import json

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
            "config_json": config.json(),
            "initial_capital": int(config.initial_capital * 10000) # Convert 万 to 元
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
        
        # 将任务配置合并到结果中
        if task.get("config"):
            results["config"] = task["config"]
            
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


@router.get("/config/default")
async def get_default_config():
    """
    获取默认回测配置
    
    Returns:
        回测配置
    """
    try:
        config = await MongoDB.get_default_backtest_config()
        return config if config else {}
    except Exception as e:
        logger.error(f"Failed to get default backtest config: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.put("/config/default")
async def save_default_config(config: BacktestConfig):
    """
    保存默认回测配置
    
    Args:
        config: 回测配置
        
    Returns:
        保存结果
    """
    try:
        await MongoDB.save_default_backtest_config(config.dict())
        return {"message": "配置已保存"}
    except Exception as e:
        logger.error(f"Failed to save default backtest config: {e}")
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}")


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


@router.get("/export/{task_id}")
async def export_backtest_result(task_id: str, format: str = Query("csv", description="导出格式: csv 或 json")):
    """
    导出回测结果
    
    Args:
        task_id: 任务ID
        format: 导出格式 (csv/json)
        
    Returns:
        文件下载流
    """
    try:
        # 获取结果
        results = await MongoDB.get_backtest_results(task_id)
        if not results:
            raise HTTPException(status_code=404, detail="未找到回测结果")
            
        task = await MongoDB.get_backtest_task(task_id)
        
        # 准备导出数据
        trade_logs = results.get("trade_logs", [])
        
        if format == "json":
            # JSON 导出
            if task and task.get("config"):
                results["config"] = task["config"]
                
            # 处理 ObjectId 和 datetime
            def json_serial(obj):
                if isinstance(obj, (datetime, datetime.date)):
                    return obj.isoformat()
                if hasattr(obj, '__str__'):
                    return str(obj)
                raise TypeError(f"Type {type(obj)} not serializable")
                
            json_str = json.dumps(results, default=json_serial, ensure_ascii=False, indent=2)
            
            return StreamingResponse(
                io.StringIO(json_str),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=backtest_result_{task_id}.json"}
            )
            
        elif format == "csv":
            # CSV 导出 (主要导出交易记录)
            output = io.StringIO()
            writer = csv.writer(output)
            
            # 写入表头
            writer.writerow(["日期", "代码", "操作", "数量", "价格", "金额", "费用", "说明"])
            
            for log in trade_logs:
                date = log.get("trade_date")
                
                # 买入记录
                for buy in log.get("buys", []):
                    writer.writerow([
                        date,
                        buy.get("code"),
                        "买入",
                        buy.get("amount"),
                        f"{buy.get('price', 0):.2f}",
                        f"{buy.get('value', 0):.2f}",
                        f"{buy.get('commission', 0):.2f}",
                        "Predict Score: N/A" # 暂无详细分
                    ])
                    
                # 卖出记录
                for sell in log.get("sells", []):
                    writer.writerow([
                        date,
                        sell.get("code"),
                        "卖出",
                        sell.get("amount"),
                        f"{sell.get('price', 0):.2f}",
                        f"{sell.get('value', 0):.2f}",
                        f"{sell.get('commission', 0):.2f}",
                        f"Actual: {sell.get('actual_received', 0):.2f}"
                    ])
                    
            output.seek(0)
            
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=backtest_result_{task_id}.csv"}
            )
            
        else:
            raise HTTPException(status_code=400, detail="不支持的导出格式")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export backtest result: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")
