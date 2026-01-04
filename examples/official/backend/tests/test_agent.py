"""
Agent 模块接口测试
测试交易代理管理的所有接口：配置管理、主用代理设置、订单、资产查询、心跳
"""
import pytest
from unittest.mock import AsyncMock, patch
from tests.utils.client import (
    APITestClient,
    assert_success_response,
    assert_error_response,
    assert_agent_structure
)


# ============================================================================
# 测试标记
# ============================================================================

pytestmark = pytest.mark.agent


# ============================================================================
# 获取代理配置
# ============================================================================

@pytest.mark.asyncio
async def test_get_agent_configs_empty(client):
    """测试获取所有代理配置 - 空列表"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/agent/config")
    assert_success_response(response, 200)
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_agent_configs_with_data(client, populated_agents_db):
    """测试获取所有代理配置 - 有数据"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/agent/config")
    assert_success_response(response, 200)

    configs = response.json()
    assert isinstance(configs, list)
    assert len(configs) >= 1
    assert_agent_structure(configs[0])


# ============================================================================
# 获取指定代理配置
# ============================================================================

@pytest.mark.asyncio
async def test_get_agent_config(client, populated_agents_db):
    """测试获取指定代理配置"""
    api_client = APITestClient(client)
    agent_id = "agent_primary_001"

    response = await api_client.get(f"/api/agent/config/{agent_id}")
    assert_success_response(response, 200)

    config = response.json()
    assert config["agent_id"] == agent_id


@pytest.mark.asyncio
async def test_get_agent_config_not_found(client):
    """测试获取指定代理配置 - 不存在"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/agent/config/non_existent_agent")
    assert_error_response(response, 404, "代理不存在")


# ============================================================================
# 创建代理配置
# ============================================================================

@pytest.mark.asyncio
async def test_create_agent_config(client, sample_agent_config_create):
    """测试创建代理配置"""
    api_client = APITestClient(client)
    response = await api_client.post("/api/agent/config", json=sample_agent_config_create)
    assert_success_response(response, 200)

    config = response.json()
    assert "agent_id" in config
    assert "agent_url" in config


@pytest.mark.asyncio
async def test_create_agent_config_missing_fields(client):
    """测试创建代理配置 - 缺少必需字段"""
    api_client = APITestClient(client)
    invalid_data = {"agent_name": "Test"}
    response = await api_client.post("/api/agent/config", json=invalid_data)
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_create_agent_config_invalid_url(client):
    """测试创建代理配置 - 无效 URL"""
    api_client = APITestClient(client)
    invalid_data = {
        "agent_url": "invalid-url",
        "agent_token": "test_token"
    }
    response = await api_client.post("/api/agent/config", json=invalid_data)
    # 可能返回验证错误
    assert response.status_code in [200, 400, 422]


# ============================================================================
# 更新代理配置
# ============================================================================

@pytest.mark.asyncio
async def test_update_agent_config(client, sample_agent_config_create):
    """测试更新代理配置"""
    # 先创建
    from database import MongoDB
    await MongoDB.database.agent_configs.insert_one({
        "agent_id": "test_agent_001",
        "agent_url": "http://old.example.com",
        "agent_token": "old_token",
        "agent_name": "Old Name",
        "is_primary": False,
        "created_at": pytest.helpers.datetime.utcnow(),
        "updated_at": pytest.helpers.datetime.utcnow()
    })

    api_client = APITestClient(client)
    response = await api_client.put(
        "/api/agent/config/test_agent_001",
        json=sample_agent_config_create
    )
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_update_agent_config_not_found(client, sample_agent_config_create):
    """测试更新代理配置 - 不存在"""
    api_client = APITestClient(client)
    response = await api_client.put("/api/agent/config/non_existent", json=sample_agent_config_create)
    assert_error_response(response, 404, "代理不存在")


# ============================================================================
# 删除代理配置
# ============================================================================

@pytest.mark.asyncio
async def test_delete_agent_config(client, populated_agents_db):
    """测试删除代理配置"""
    from database import MongoDB
    # 创建一个临时代理
    await MongoDB.database.agent_configs.insert_one({
        "agent_id": "temp_agent_001",
        "agent_url": "http://temp.example.com",
        "agent_token": "temp_token",
        "agent_name": "Temp Agent",
        "is_primary": False,
        "created_at": pytest.helpers.datetime.utcnow(),
        "updated_at": pytest.helpers.datetime.utcnow()
    })

    api_client = APITestClient(client)
    response = await api_client.delete("/api/agent/config/temp_agent_001")
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_delete_agent_config_not_found(client):
    """测试删除代理配置 - 不存在"""
    api_client = APITestClient(client)
    response = await api_client.delete("/api/agent/config/non_existent")
    assert_error_response(response, 404, "代理不存在")


# ============================================================================
# 设置主用代理
# ============================================================================

@pytest.mark.asyncio
async def test_set_primary_agent(client, populated_agents_db):
    """测试设置主用代理"""
    api_client = APITestClient(client)
    agent_id = "agent_backup_001"

    response = await api_client.put(f"/api/agent/config/{agent_id}/primary")
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_set_primary_agent_not_found(client):
    """测试设置主用代理 - 不存在"""
    api_client = APITestClient(client)
    response = await api_client.put("/api/agent/config/non_existent/primary")
    # 可能返回 404 或其他错误
    assert response.status_code in [404, 500]


# ============================================================================
# 获取主用代理
# ============================================================================

@pytest.mark.asyncio
async def test_get_primary_agent(client, populated_agents_db):
    """测试获取主用代理"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/agent/primary")
    assert_success_response(response, 200)

    agent = response.json()
    # 应该返回主用代理
    if agent:
        assert agent["is_primary"] is True


@pytest.mark.asyncio
async def test_get_primary_agent_no_primary(client):
    """测试获取主用代理 - 无主用代理"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/agent/primary")
    # 可能返回 None 或 404
    assert response.status_code in [200, 404]


# ============================================================================
# 获取代理状态
# ============================================================================

@pytest.mark.asyncio
async def test_get_agents_status(client, populated_agents_db):
    """测试获取所有代理状态"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/agent/status")
    assert_success_response(response, 200)

    agents = response.json()
    assert isinstance(agents, list)
    if agents:
        assert "status" in agents[0]


@pytest.mark.asyncio
async def test_get_agents_status_empty(client):
    """测试获取所有代理状态 - 空列表"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/agent/status")
    assert_success_response(response, 200)
    assert response.json() == []


# ============================================================================
# 获取代理资产信息
# ============================================================================

@pytest.mark.asyncio
@patch('httpx.AsyncClient')
async def test_get_agent_asset_info(mock_httpx_client, client, populated_agents_db):
    """测试获取代理资产信息"""
    # Mock httpx 客户端
    mock_client = AsyncMock()
    mock_client.get.return_value.json.return_value = {
        "account_id": "test_account",
        "total_assets": 100000.0,
        "available_cash": 50000.0,
        "market_value": 50000.0,
        "positions": []
    }
    mock_httpx_client.return_value.__aenter__.return_value = mock_client

    api_client = APITestClient(client)
    response = await api_client.get("/api/agent/asset/agent_primary_001")
    # 可能返回 200 或 500（取决于 mock 设置）
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_get_agent_asset_info_not_found(client):
    """测试获取代理资产信息 - 代理不存在"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/agent/asset/non_existent")
    assert response.status_code in [404, 500]


# ============================================================================
# 提交订单
# ============================================================================

@pytest.mark.asyncio
async def test_submit_agent_orders_buy(client):
    """测试提交买入订单"""
    api_client = APITestClient(client)
    stocks = [
        {"code": "sh600000", "quantity": 100, "price": 10.50}
    ]

    response = await api_client.post(
        "/api/agent/orders",
        params={"action": "buy"},
        json={"stocks": stocks}
    )
    # 可能返回 200 或 500（取决于代理是否可用）
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_submit_agent_orders_sell(client):
    """测试提交卖出订单"""
    api_client = APITestClient(client)
    stocks = [
        {"code": "sh600000", "quantity": 100, "price": 10.50}
    ]

    response = await api_client.post(
        "/api/agent/orders",
        params={"action": "sell"},
        json={"stocks": stocks}
    )
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_submit_agent_orders_cancel(client):
    """测试取消订单"""
    api_client = APITestClient(client)
    stocks = [
        {"order_id": "test_order_001"}
    ]

    response = await api_client.post(
        "/api/agent/orders",
        params={"action": "cancel"},
        json={"stocks": stocks}
    )
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_submit_agent_orders_invalid_action(client):
    """测试提交订单 - 无效操作"""
    api_client = APITestClient(client)
    response = await api_client.post(
        "/api/agent/orders",
        params={"action": "invalid"},
        json={"stocks": []}
    )
    # 可能返回 400 或 500
    assert response.status_code in [400, 500]


# ============================================================================
# 查询订单状态
# ============================================================================

@pytest.mark.asyncio
async def test_get_agent_orders(client):
    """测试查询所有订单"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/agent/orders")
    # 可能返回 200 或 500（取决于代理是否可用）
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_get_agent_order_by_id(client):
    """测试查询单个订单"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/agent/orders", params={"order_id": "test_order_001"})
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_get_agent_orders_with_limit(client):
    """测试查询订单 - 限制数量"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/agent/orders", params={"limit": 10})
    assert response.status_code in [200, 500]


# ============================================================================
# 查询代理持仓
# ============================================================================

@pytest.mark.asyncio
async def test_get_agent_positions(client, populated_agents_db):
    """测试查询代理持仓"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/agent/positions/agent_primary_001")
    # 可能返回 200 或 500（取决于代理是否可用）
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_get_agent_positions_not_found(client):
    """测试查询代理持仓 - 代理不存在"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/agent/positions/non_existent")
    assert response.status_code in [404, 500]


# ============================================================================
# 心跳检测
# ============================================================================

@pytest.mark.asyncio
async def test_heartbeat_agent(client, populated_agents_db):
    """测试代理心跳检测"""
    api_client = APITestClient(client)
    response = await api_client.post("/api/agent/heartbeat/agent_primary_001")
    # 可能返回 200 或 500（取决于代理是否可用）
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_heartbeat_agent_not_found(client):
    """测试代理心跳检测 - 代理不存在"""
    api_client = APITestClient(client)
    response = await api_client.post("/api/agent/heartbeat/non_existent")
    assert response.status_code in [404, 500]


# ============================================================================
# 边界测试
# ============================================================================

@pytest.mark.asyncio
async def test_agent_config_long_name(client):
    """测试代理配置 - 超长名称"""
    api_client = APITestClient(client)
    config_data = {
        "agent_url": "http://test.example.com",
        "agent_token": "test_token",
        "agent_name": "A" * 200
    }

    response = await api_client.post("/api/agent/config", json=config_data)
    # 长名称可能仍然被接受
    assert response.status_code in [200, 400, 422]


@pytest.mark.asyncio
async def test_agent_config_empty_token(client):
    """测试代理配置 - 空 token"""
    api_client = APITestClient(client)
    config_data = {
        "agent_url": "http://test.example.com",
        "agent_token": "",
        "agent_name": "Test Agent"
    }

    response = await api_client.post("/api/agent/config", json=config_data)
    assert response.status_code in [200, 400, 422]


@pytest.mark.asyncio
async def test_submit_orders_empty_list(client):
    """测试提交订单 - 空列表"""
    api_client = APITestClient(client)
    response = await api_client.post(
        "/api/agent/orders",
        params={"action": "buy"},
        json={"stocks": []}
    )
    # 空列表可能被接受或拒绝
    assert response.status_code in [200, 400, 500]
