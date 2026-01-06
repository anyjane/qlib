"""增强的回测 API 路由"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from loguru import logger

from database import MongoDB
from config import settings
from backtest import (
    BacktestService,
    BacktestConfig,
    BacktestResult,
    StrategyType,
    MethodType,
    get_available_strategies,
)

router = APIRouter(prefix="/api/backtest-enhanced", tags=["Backtest Enhanced"])


# ============================================================================
# 请求/响应模型
# ============================================================================

class BacktestConfigRequest(BaseModel):
    """回测配置请求"""
    # 基础配置
    initial_capital: float = 100.0
    market: str = "csi300"

    # 日期配置
    train_start: str = "2020-01-01"
    train_end: str = "2024-12-31"
    test_start: str = "2025-01-01"
    test_end: str = "2025-12-30"

    # 交易费用配置
    buy_rate: float = 0.0005
    sell_rate: float = 0.0015
    min_commission: float = 5.0
    limit_threshold: float = 0.095
    deal_price: str = "close"

    # 策略配置
    strategy_type: str = "topk_reallocation"
    topk: int = 50
    n_drop: int = 5
    hold_thresh: int = 1
    method_sell: str = "bottom"
    method_buy: str = "top"
    only_tradable: bool = False
    forbid_all_trade_at_limit: bool = True
    max_reallocation_rounds: int = 3
    log_prediction_details: bool = True
    verbose: bool = True


class BacktestExecuteRequest(BaseModel):
    """回测执行请求"""
    config: BacktestConfigRequest


# ============================================================================
# 默认配置
# ============================================================================

DEFAULT_CONFIG = {
    "initial_capital": 100.0,
    "market": "csi300",
    "train_start": "2020-01-01",
    "train_end": "2024-12-31",
    "test_start": "2025-01-01",
    "test_end": "2025-12-30",
    "buy_rate": 0.0005,
    "sell_rate": 0.0015,
    "min_commission": 5.0,
    "limit_threshold": 0.095,
    "deal_price": "close",
    "strategy_type": "topk_reallocation",
    "topk": 50,
    "n_drop": 5,
    "hold_thresh": 1,
    "method_sell": "bottom",
    "method_buy": "top",
    "only_tradable": False,
    "forbid_all_trade_at_limit": True,
    "max_reallocation_rounds": 3,
    "log_prediction_details": True,
    "verbose": True,
}


# ============================================================================
# API 路由
# ============================================================================

@router.get("/config/default")
async def get_default_config():
    """
    获取默认回测配置

    Returns:
        默认配置
    """
    return DEFAULT_CONFIG


@router.get("/strategies")
async def get_available_strategies_list():
    """
    获取可用的策略列表

    Returns:
        策略信息列表
    """
    strategies = get_available_strategies()

    result = []
    for strategy_type, strategy_info in strategies.items():
        result.append({
            "type": strategy_type.value,
            "name": strategy_info.name,
            "description": strategy_info.description,
            "params": strategy_info.params,
        })

    return {"strategies": result}


@router.post("/execute")
async def execute_backtest(request: BacktestExecuteRequest):
    """
    执行回测

    Args:
        request: 回测执行请求

    Returns:
        回测结果
    """
    try:
        # 转换配置
        config_dict = request.config.dict()
        config_dict["strategy_type"] = StrategyType(config_dict["strategy_type"])
        config_dict["method_sell"] = MethodType(config_dict["method_sell"])
        config_dict["method_buy"] = MethodType(config_dict["method_buy"])

        config = BacktestConfig(**config_dict)

        # 生成任务 ID 和实验名称
        task_id = f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        experiment_name = f"backtest_{config.market}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Executing backtest: {task_id}")
        logger.info(f"Config: {config.dict()}")

        # 创建回测服务
        service = BacktestService(data_dir=settings.QLIB_PROVIDER_URI)

        # 执行回测
        result = service.run_backtest(
            config=config,
            task_id=task_id,
            experiment_name=experiment_name,
        )

        # 保存结果到数据库
        result_dict = result.dict()
        await MongoDB.insert_backtest_result({
            "task_id": task_id,
            "experiment_name": experiment_name,
            "config": config_dict,
            "metrics": result_dict["metrics"],
            "trade_logs": result_dict["trade_logs"],
            "equity_curve": result_dict["equity_curve"],
            "created_at": datetime.utcnow(),
        })

        return {
            "task_id": task_id,
            "status": "completed",
            "result": result_dict,
            "message": "回测执行成功",
        }

    except Exception as e:
        logger.error(f"Failed to execute backtest: {e}")
        raise HTTPException(status_code=500, detail=f"回测执行失败: {str(e)}")


@router.get("/results/{task_id}")
async def get_backtest_result(task_id: str):
    """
    获取回测结果

    Args:
        task_id: 任务ID

    Returns:
        回测结果
    """
    try:
        result = await MongoDB.get_backtest_result(task_id)

        if not result:
            raise HTTPException(status_code=404, detail="回测结果不存在")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get backtest result: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/results")
async def get_all_backtest_results(
    limit: int = Query(20, description="返回数量限制"),
    market: Optional[str] = Query(None, description="市场筛选"),
):
    """
    获取所有回测结果列表

    Args:
        limit: 返回数量限制
        market: 市场筛选

    Returns:
        回测结果列表
    """
    try:
        results = await MongoDB.get_all_backtest_results(limit=limit, market=market)

        return {
            "results": results,
            "count": len(results),
        }

    except Exception as e:
        logger.error(f"Failed to get backtest results: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.delete("/results/{task_id}")
async def delete_backtest_result(task_id: str):
    """
    删除回测结果

    Args:
        task_id: 任务ID

    Returns:
        删除结果
    """
    try:
        deleted_count = await MongoDB.delete_backtest_result(task_id)

        if deleted_count == 0:
            raise HTTPException(status_code=404, detail="回测结果不存在")

        return {
            "message": "删除成功",
            "task_id": task_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete backtest result: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
