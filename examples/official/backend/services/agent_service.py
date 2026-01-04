"""Agent management service with primary/secondary failover"""
import httpx
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger

from database import MongoDB
from models import AgentConfigCreate


class AgentService:
    """交易代理管理服务（优化主从机制）"""

    @staticmethod
    async def create_agent_config(config: AgentConfigCreate) -> Dict:
        """创建代理配置"""
        agent_id = f"agent_{datetime.now().timestamp()}"

        agent_dict = config.dict()
        agent_dict["agent_id"] = agent_id
        agent_dict["is_primary"] = False  # 默认不是主用
        agent_dict["status"] = "inactive"
        agent_dict["last_heartbeat"] = None
        agent_dict["created_at"] = datetime.utcnow()
        agent_dict["updated_at"] = datetime.utcnow()

        await MongoDB.create_agent_config(agent_dict)

        return agent_dict

    @staticmethod
    async def update_agent_config(agent_id: str, config: AgentConfigCreate):
        """更新代理配置"""
        await MongoDB.update_agent_config(agent_id, {
            "agent_url": config.agent_url,
            "agent_token": config.agent_token,
            "agent_name": config.agent_name,
            "updated_at": datetime.utcnow()
        })

    @staticmethod
    async def set_primary_agent(agent_id: str) -> Dict:
        """
        设置主用代理

        将指定代理设置为主用，其他代理自动切换为从用
        """
        # 检查代理是否存在
        config = await MongoDB.get_agent_config(agent_id)
        if not config:
            raise ValueError("Agent not found")

        # 将所有代理的 is_primary 设置为 False
        await MongoDB.update_all_agents_primary(agent_id)

        # 设置主用代理
        await MongoDB.update_agent_config(agent_id, {
            "is_primary": True,
            "updated_at": datetime.utcnow()
        })

        logger.info(f"Set primary agent: {agent_id}")
        return {"message": f"Successfully set {agent_id} as primary agent"}

    @staticmethod
    async def get_primary_agent() -> Optional[Dict]:
        """
        获取当前主用代理

        Returns:
            主用代理配置，如果没有则返回 None
        """
        return await MongoDB.get_primary_agent_config()

    @staticmethod
    async def get_agent_asset_info(agent_id: str) -> Dict:
        """
        获取代理资产信息（账号ID、资产、持仓列表）

        Args:
            agent_id: 代理ID

        Returns:
            资产信息
        """
        config = await MongoDB.get_agent_config(agent_id)
        if not config:
            raise ValueError("Agent not found")

        # 调用代理 API 获取资产信息
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{config['agent_url']}/api/trade/asset",
                headers={
                    "Authorization": f"Bearer {config['agent_token']}",
                },
                timeout=30.0
            )
            response.raise_for_status()
            asset_data = response.json()

        # 调用代理 API 获取持仓列表
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{config['agent_url']}/api/trade/positions_and_trades",
                headers={
                    "Authorization": f"Bearer {config['agent_token']}",
                },
                timeout=30.0
            )
            response.raise_for_status()
            positions_data = response.json()

        # 整合数据
        asset_info = {
            "account_id": asset_data.get("account_id", ""),
            "total_assets": asset_data.get("total_assets", 0.0),
            "available_cash": asset_data.get("available_cash", 0.0),
            "market_value": asset_data.get("market_value", 0.0),
            "positions": positions_data.get("positions", []),
            "updated_at": datetime.utcnow(),
        }

        # 更新心跳时间
        await MongoDB.update_agent_heartbeat(agent_id)

        return asset_info

    @staticmethod
    async def submit_orders(action: str, stocks: List[dict]) -> Dict:
        """
        提交交易订单到代理

        Args:
            action: 交易类型（buy/sell/cancel）
            stocks: 股票列表

        Returns:
            订单提交结果
        """
        # 获取主用代理
        primary_agent = await AgentService.get_primary_agent()
        if not primary_agent:
            raise ValueError("No primary agent available")

        # 检查主用代理是否可用
        if primary_agent.get('status') != 'active':
            # 尝试切换到可用的从用代理
            await AgentService._failover_to_secondary_agent()

            # 重新获取主用代理
            primary_agent = await AgentService.get_primary_agent()
            if not primary_agent or primary_agent.get('status') != 'active':
                raise ValueError("No available agent for trading")

        # 提交订单到主用代理
        payload = {
            "action": action,
            "stocks": stocks,
            "timestamp": datetime.now().isoformat()
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{primary_agent['agent_url']}/api/trade/order_commit",
                json=payload,
                headers={
                    "Authorization": f"Bearer {primary_agent['agent_token']}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def get_agent_orders(order_id: str = None, limit: int = 100) -> Dict:
        """查询代理订单状态"""
        primary_agent = await AgentService.get_primary_agent()
        if not primary_agent:
            raise ValueError("No primary agent available")

        params = {}
        if order_id:
            params["order_id"] = order_id
        if limit:
            params["limit"] = limit

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{primary_agent['agent_url']}/api/trade/order",
                params=params,
                headers={
                    "Authorization": f"Bearer {primary_agent['agent_token']}",
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def get_agent_positions(agent_id: str) -> Dict:
        """查询代理持仓状态"""
        config = await MongoDB.get_agent_config(agent_id)
        if not config:
            raise ValueError("Agent not found")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{config['agent_url']}/api/trade/positions_and_trades",
                headers={
                    "Authorization": f"Bearer {config['agent_token']}",
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def heartbeat_agent(agent_id: str) -> Dict:
        """
        代理心跳检测

        Args:
            agent_id: 代理ID

        Returns:
            心跳检测结果（是否可用）
        """
        try:
            # 尝试获取资产信息
            asset_info = await AgentService.get_agent_asset_info(agent_id)
            await MongoDB.update_agent_status(agent_id, "active")
            return {"status": "active", "agent_id": agent_id}
        except Exception as e:
            logger.warning(f"Heartbeat failed for agent {agent_id}: {e}")
            await MongoDB.update_agent_status(agent_id, "unavailable")
            return {"status": "unavailable", "agent_id": agent_id}

    @staticmethod
    async def _failover_to_secondary_agent():
        """
        自动故障转移到从用代理

        将第一个可用的从用代理提升为主用
        """
        configs = await MongoDB.get_all_agent_configs()

        # 找到第一个可用的从用代理
        for config in configs:
            if not config.get('is_primary'):
                try:
                    # 检查代理是否可用
                    await AgentService.heartbeat_agent(config['agent_id'])
                    # 提升为主用代理
                    await AgentService.set_primary_agent(config['agent_id'])
                    logger.info(f"Failed over to secondary agent: {config['agent_id']}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to failover to {config['agent_id']}: {e}")
                    continue

        logger.error("No available secondary agent for failover")
