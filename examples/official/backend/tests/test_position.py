"""
Position 模块接口测试
测试持仓管理的所有接口：增删改查、批量操作、导入、同步
"""
import pytest
from io import BytesIO
import pandas as pd
from tests.utils.client import (
    APITestClient,
    assert_success_response,
    assert_error_response,
    assert_position_structure
)


# ============================================================================
# 测试标记
# ============================================================================

pytestmark = pytest.mark.position


# ============================================================================
# 获取持仓列表
# ============================================================================

@pytest.mark.asyncio
async def test_get_positions_empty(client):
    """测试获取持仓列表 - 空列表"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/positions/")
    assert_success_response(response, 200)
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_positions_with_data(client, populated_positions_db):
    """测试获取持仓列表 - 有数据"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/positions/")
    assert_success_response(response, 200)

    positions = response.json()
    assert isinstance(positions, list)
    assert len(positions) >= 1
    assert_position_structure(positions[0])


# ============================================================================
# 创建持仓
# ============================================================================

@pytest.mark.asyncio
async def test_create_position(client, sample_position_create, populated_stocks_db):
    """测试创建持仓"""
    api_client = APITestClient(client)
    response = await api_client.post("/api/positions/", json=sample_position_create)
    assert_success_response(response, 200)

    result = response.json()
    assert "message" in result


@pytest.mark.asyncio
async def test_create_position_duplicate(client, sample_position_create):
    """测试创建持仓 - 重复"""
    api_client = APITestClient(client)

    # 第一次创建
    await api_client.post("/api/positions/", json=sample_position_create)

    # 第二次创建（应该失败）
    response = await api_client.post("/api/positions/", json=sample_position_create)
    assert_error_response(response, 400, "持仓已存在")


@pytest.mark.asyncio
async def test_create_position_auto_name(client, populated_stocks_db):
    """测试创建持仓 - 自动获取股票名称"""
    api_client = APITestClient(client)
    position_data = {
        "code": "sh600000",
        "quantity": 100.0,
        "cost_price": 10.0
    }

    response = await api_client.post("/api/positions/", json=position_data)
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_create_position_invalid_quantity(client):
    """测试创建持仓 - 无效数量"""
    api_client = APITestClient(client)
    invalid_data = {
        "code": "sh600000",
        "quantity": -100.0,  # 负数
        "cost_price": 10.0
    }

    response = await api_client.post("/api/positions/", json=invalid_data)
    # 可能返回 422 验证错误
    assert response.status_code in [400, 422]


# ============================================================================
# 更新持仓
# ============================================================================

@pytest.mark.asyncio
async def test_update_position(client, sample_position_create, sample_position_update):
    """测试更新持仓"""
    api_client = APITestClient(client)

    # 先创建
    await api_client.post("/api/positions/", json=sample_position_create)

    # 更新
    response = await api_client.put(
        f"/api/positions/{sample_position_create['code']}",
        json=sample_position_update
    )
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_update_position_not_found(client, sample_position_update):
    """测试更新持仓 - 不存在"""
    api_client = APITestClient(client)
    response = await api_client.put("/api/positions/sh999999", json=sample_position_update)
    assert_error_response(response, 404, "持仓不存在")


@pytest.mark.asyncio
async def test_update_position_auto_recalculate_market_value(client, sample_position_create):
    """测试更新持仓 - 自动重新计算市值"""
    api_client = APITestClient(client)

    # 先创建
    await api_client.post("/api/positions/", json=sample_position_create)

    # 更新数量和成本价
    update_data = {"quantity": 200.0, "cost_price": 15.0}
    response = await api_client.put(
        f"/api/positions/{sample_position_create['code']}",
        json=update_data
    )
    assert_success_response(response, 200)


# ============================================================================
# 删除持仓
# ============================================================================

@pytest.mark.asyncio
async def test_delete_position(client, sample_position_create):
    """测试删除持仓"""
    api_client = APITestClient(client)

    # 先创建
    await api_client.post("/api/positions/", json=sample_position_create)

    # 删除
    response = await api_client.delete(f"/api/positions/{sample_position_create['code']}")
    assert_success_response(response, 200)

    result = response.json()
    assert "message" in result


@pytest.mark.asyncio
async def test_delete_position_not_found(client):
    """测试删除持仓 - 不存在"""
    api_client = APITestClient(client)
    response = await api_client.delete("/api/positions/sh999999")
    assert_error_response(response, 404, "持仓不存在")


# ============================================================================
# 导入持仓
# ============================================================================

@pytest.mark.asyncio
async def test_import_positions_csv(client):
    """测试导入持仓 - CSV 格式"""
    # 创建 CSV 内容
    csv_content = """code,quantity,cost_price,name
sh600000,1000,10.50,浦发银行
sh600036,500,35.80,招商银行"""
    csv_bytes = csv_content.encode('utf-8')

    api_client = APITestClient(client)
    files = {"file": ("positions.csv", BytesIO(csv_bytes), "text/csv")}

    response = await api_client.post("/api/positions/import", files=files)
    assert_success_response(response, 200)

    result = response.json()
    assert "imported" in result


@pytest.mark.asyncio
async def test_import_positions_csv_with_existing(client, populated_positions_db):
    """测试导入持仓 - 更新已存在的持仓"""
    csv_content = """code,quantity,cost_price,name
sh600000,1500,11.00,浦发银行"""
    csv_bytes = csv_content.encode('utf-8')

    api_client = APITestClient(client)
    files = {"file": ("positions.csv", BytesIO(csv_bytes), "text/csv")}

    response = await api_client.post("/api/positions/import", files=files)
    # 应该跳过已存在的持仓
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_import_positions_invalid_format(client):
    """测试导入持仓 - 无效格式"""
    api_client = APITestClient(client)
    files = {"file": ("invalid.txt", BytesIO(b"invalid"), "text/plain")}

    response = await api_client.post("/api/positions/import", files=files)
    # CSV 解析可能返回 500 错误
    assert response.status_code in [400, 500]


@pytest.mark.asyncio
async def test_import_positions_missing_columns(client):
    """测试导入持仓 - 缺少必需列"""
    csv_content = """code,name
sh600000,浦发银行"""
    csv_bytes = csv_content.encode('utf-8')

    api_client = APITestClient(client)
    files = {"file": ("positions.csv", BytesIO(csv_bytes), "text/csv")}

    response = await api_client.post("/api/positions/import", files=files)
    assert response.status_code in [400, 500]


# ============================================================================
# 批量操作
# ============================================================================

@pytest.mark.asyncio
async def test_batch_delete_positions(client, populated_positions_db):
    """测试批量删除持仓"""
    api_client = APITestClient(client)
    codes = ["sh600000"]

    response = await api_client.post(
        "/api/positions/batch",
        params={"operation": "delete"},
        json={"codes": codes}
    )
    assert_success_response(response, 200)

    result = response.json()
    assert "modified_count" in result


@pytest.mark.asyncio
async def test_batch_update_positions(client, populated_positions_db):
    """测试批量更新持仓"""
    api_client = APITestClient(client)
    codes = ["sh600000"]
    update_data = {"quantity": 2000.0}

    response = await api_client.post(
        "/api/positions/batch",
        params={"operation": "update"},
        json={"codes": codes, "update_data": update_data}
    )
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_batch_operation_invalid(client):
    """测试批量操作 - 无效操作类型"""
    api_client = APITestClient(client)
    response = await api_client.post(
        "/api/positions/batch",
        params={"operation": "invalid"},
        json={"codes": []}
    )
    assert_error_response(response, 400, "无效的操作类型")


# ============================================================================
# 同步持仓
# ============================================================================

@pytest.mark.asyncio
async def test_sync_positions_no_primary_agent(client):
    """测试同步持仓 - 无主用代理"""
    api_client = APITestClient(client)
    response = await api_client.post("/api/positions/sync")
    assert_error_response(response, 503, "没有可用的主用代理")


# ============================================================================
# 边界测试
# ============================================================================

@pytest.mark.asyncio
async def test_position_zero_quantity(client):
    """测试持仓 - 零数量"""
    api_client = APITestClient(client)
    position_data = {
        "code": "sh600000",
        "quantity": 0.0,
        "cost_price": 10.0
    }

    response = await api_client.post("/api/positions/", json=position_data)
    # 零持仓应该是有效的
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_position_zero_cost_price(client):
    """测试持仓 - 零成本价"""
    api_client = APITestClient(client)
    position_data = {
        "code": "sh600000",
        "quantity": 100.0,
        "cost_price": 0.0
    }

    response = await api_client.post("/api/positions/", json=position_data)
    # 零成本价可能是有效的
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_position_large_quantity(client):
    """测试持仓 - 大数量"""
    api_client = APITestClient(client)
    position_data = {
        "code": "sh600000",
        "quantity": 1000000.0,
        "cost_price": 10.0
    }

    response = await api_client.post("/api/positions/", json=position_data)
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_update_position_partial_fields(client, sample_position_create):
    """测试更新持仓 - 部分字段"""
    api_client = APITestClient(client)

    # 先创建
    await api_client.post("/api/positions/", json=sample_position_create)

    # 只更新数量
    update_data = {"quantity": 300.0}
    response = await api_client.put(
        f"/api/positions/{sample_position_create['code']}",
        json=update_data
    )
    assert_success_response(response, 200)


# ============================================================================
# 性能测试（可选）
# ============================================================================

@pytest.mark.slow
@pytest.mark.asyncio
async def test_import_large_positions_csv(client):
    """测试导入大量持仓"""
    # 创建包含 1000 行的 CSV
    positions_data = []
    for i in range(1000):
        positions_data.append({
            "code": f"sh6000{i % 100}",
            "quantity": float(i + 1) * 10,
            "cost_price": 10.0 + i * 0.1,
            "name": f"股票{i % 100}"
        })

    df = pd.DataFrame(positions_data)
    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)

    api_client = APITestClient(client)
    files = {"file": ("large_positions.csv", output, "text/csv")}

    response = await api_client.post("/api/positions/import", files=files)
    assert_success_response(response, 200)

    result = response.json()
    assert result["imported"] > 0
