"""Agent management API with primary/secondary failover"""
from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
from loguru import logger

from database import MongoDB
from models import AgentConfigCreate, AgentAssetInfo

router = APIRouter(prefix="/api/agent", tags=["Agent"])


@router.get("/config")
async def get_agent_configs():
    """
    获取所有代理配置

    Returns:
        代理配置列表
    """
    try:
        configs = await MongoDB.get_all_agent_configs()
        return configs
    except Exception as e:
        logger.error(f"Failed to get agent configs: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/config/{agent_id}")
async def get_agent_config(agent_id: str):
    """
    获取指定代理配置

    Args:
        agent_id: 代理ID

    Returns:
        代理配置
    """
    try:
        config = await MongoDB.get_agent_config(agent_id)
        if not config:
            raise HTTPException(status_code=404, detail="代理不存在")
        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent config: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/config")
async def create_agent_config(config: AgentConfigCreate):
    """
    创建代理配置

    Args:
        config: 代理配置

    Returns:
        创建的代理配置
    """
    try:
        from services.agent_service import AgentService

        result = await AgentService.create_agent_config(config)

        logger.info(f"Created agent config: {config.agent_name}")
        return result
    except Exception as e:
        logger.error(f"Failed to create agent config: {e}")
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.put("/config/{agent_id}")
async def update_agent_config(agent_id: str, config: AgentConfigCreate):
    """
    更新代理配置

    Args:
        agent_id: 代理ID
        config: 代理配置

    Returns:
        操作结果
    """
    try:
        from services.agent_service import AgentService

        # 检查代理是否存在
        existing = await MongoDB.get_agent_config(agent_id)
        if not existing:
            raise HTTPException(status_code=404, detail="代理不存在")

        # 更新配置
        await AgentService.update_agent_config(agent_id, config)

        logger.info(f"Updated agent config: {agent_id}")
        return {"message": f"代理 {agent_id} 已更新"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update agent config: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/config/{agent_id}")
async def delete_agent_config(agent_id: str):
    """
    删除代理配置

    Args:
        agent_id: 代理ID

    Returns:
        操作结果
    """
    try:
        result = await MongoDB.delete_agent_config(agent_id)
        if not result:
            raise HTTPException(status_code=404, detail="代理不存在")

        logger.info(f"Deleted agent config: {agent_id}")
        return {"message": f"代理 {agent_id} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete agent config: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.put("/config/{agent_id}/primary")
async def set_primary_agent(agent_id: str):
    """
    设置主用代理

    Args:
        agent_id: 代理ID

    Returns:
        操作结果
    """
    try:
        from services.agent_service import AgentService

        result = await AgentService.set_primary_agent(agent_id)

        logger.info(f"Set primary agent: {agent_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to set primary agent: {e}")
        raise HTTPException(status_code=500, detail=f"设置失败: {str(e)}")


@router.get("/primary")
async def get_primary_agent():
    """
    获取当前主用代理

    Returns:
        主用代理配置，如果没有则返回 None
    """
    try:
        from services.agent_service import AgentService

        agent = await AgentService.get_primary_agent()
        return agent
    except Exception as e:
        logger.error(f"Failed to get primary agent: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/status")
async def get_agents_status():
    """
    获取所有代理状态

    Returns:
        代理状态列表（包含是否可用、是否主用）
    """
    try:
        from services.agent_service import AgentService

        configs = await MongoDB.get_all_agent_configs()

        # 检查每个代理的状态
        for config in configs:
            try:
                # 尝试连接代理
                await AgentService.heartbeat_agent(config['agent_id'])
                config['status'] = 'active'
            except Exception as e:
                logger.warning(f"Agent {config['agent_id']} is unavailable: {e}")
                config['status'] = 'unavailable'

        return configs
    except Exception as e:
        logger.error(f"Failed to get agents status: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/asset/{agent_id}")
async def get_agent_asset_info(agent_id: str):
    """
    获取代理资产信息（账号ID、资产、持仓列表）

    Args:
        agent_id: 代理ID

    Returns:
        资产信息（账号ID、总资产、可用资金、持仓列表等）
    """
    try:
        from services.agent_service import AgentService

        asset_info = await AgentService.get_agent_asset_info(agent_id)

        return asset_info
    except Exception as e:
        logger.error(f"Failed to get agent asset info: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/orders")
async def submit_agent_orders(action: str, stocks: List[dict] = None):
    """
    提交交易订单到代理

    Args:
        action: 交易类型（buy/sell/cancel）
        stocks: 股票列表

    Returns:
        订单提交结果
    """
    try:
        from services.agent_service import AgentService

        # 如果 stocks 为 None，设置为空列表
        if stocks is None:
            stocks = []

        result = await AgentService.submit_orders(action, stocks)

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit orders: {e}")
        raise HTTPException(status_code=500, detail=f"提交订单失败: {str(e)}")


@router.get("/orders")
async def get_agent_orders(order_id: str = None, limit: int = 100):
    """
    查询代理订单状态

    Args:
        order_id: 订单ID（可选）
        limit: 返回数量限制

    Returns:
        订单列表
    """
    try:
        from services.agent_service import AgentService

        orders = await AgentService.get_agent_orders(order_id, limit)

        return orders
    except Exception as e:
        logger.error(f"Failed to get agent orders: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/positions/{agent_id}")
async def get_agent_positions(agent_id: str):
    """
    查询代理持仓状态

    Args:
        agent_id: 代理ID

    Returns:
        持仓列表
    """
    try:
        from services.agent_service import AgentService

        positions = await AgentService.get_agent_positions(agent_id)

        return positions
    except Exception as e:
        logger.error(f"Failed to get agent positions: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/heartbeat/{agent_id}")
async def heartbeat_agent(agent_id: str):
    """
    代理心跳检测

    Args:
        agent_id: 代理ID

    Returns:
        心跳检测结果（是否可用）
    """
    try:
        from services.agent_service import AgentService

        result = await AgentService.heartbeat_agent(agent_id)

        return result
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="代理不存在")
        raise
    except Exception as e:
        logger.error(f"Failed to heartbeat agent: {e}")
        raise HTTPException(status_code=500, detail=f"心跳检测失败: {str(e)}")
