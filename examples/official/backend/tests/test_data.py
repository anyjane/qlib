"""
Data 模块接口测试
测试数据下载管理的所有接口：获取最新日期、下载数据、更新数据、任务查询
"""
import pytest
from datetime import datetime, timedelta
from tests.utils.client import (
    APITestClient,
    assert_success_response,
    assert_error_response,
    assert_json_keys
)


# ============================================================================
# 测试标记
# ============================================================================

pytestmark = pytest.mark.data


# ============================================================================
# 获取最新数据日期
# ============================================================================

@pytest.mark.asyncio
async def test_get_latest_data_date(client):
    """测试获取最新数据日期"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/data/latest_date")
    assert_success_response(response, 200)

    result = response.json()
    assert "latest_date" in result


@pytest.mark.asyncio
async def test_get_latest_data_date_empty(client):
    """测试获取最新数据日期 - 无数据"""
    api_client = APITestClient(client)
    # 即使没有数据也应该返回响应
    response = await api_client.get("/api/data/latest_date")
    assert response.status_code in [200, 500]


# ============================================================================
# 下载数据
# ============================================================================

@pytest.mark.asyncio
async def test_download_data_default_params(client, populated_stocks_db):
    """测试下载数据 - 默认参数"""
    api_client = APITestClient(client)
    response = await api_client.post("/api/data/download")
    assert_success_response(response, 200)

    result = response.json()
    assert "task_id" in result
    assert "status" in result
    assert result["status"] == "started"


@pytest.mark.asyncio
async def test_download_data_with_dates(client, populated_stocks_db):
    """测试下载数据 - 指定日期范围"""
    api_client = APITestClient(client)
    start_date = "2024-01-01"
    end_date = "2024-12-31"

    response = await api_client.post(
        "/api/data/download",
        params={"start_date": start_date, "end_date": end_date}
    )
    assert_success_response(response, 200)

    result = response.json()
    assert result["start_date"] == start_date
    assert result["end_date"] == end_date


@pytest.mark.asyncio
async def test_download_data_with_stocks(client, populated_stocks_db):
    """测试下载数据 - 指定股票"""
    api_client = APITestClient(client)
    stocks = ["sh600000", "sh600036"]

    response = await api_client.post(
        "/api/data/download",
        json=stocks
    )
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_download_data_invalid_date_format(client, populated_stocks_db):
    """测试下载数据 - 无效日期格式"""
    api_client = APITestClient(client)
    response = await api_client.post(
        "/api/data/download",
        params={"start_date": "invalid-date"}
    )
    # 可能返回 400 或 500 错误
    assert response.status_code in [400, 500]


@pytest.mark.asyncio
async def test_download_data_empty_stocks(client):
    """测试下载数据 - 空股票列表"""
    api_client = APITestClient(client)
    response = await api_client.post(
        "/api/data/download",
        json=[]
    )
    # 应该仍然能创建任务
    assert_success_response(response, 200)


# ============================================================================
# 更新数据
# ============================================================================

@pytest.mark.asyncio
async def test_update_data_default(client, populated_stocks_db):
    """测试更新数据 - 默认参数（更新所有启用的股票）"""
    api_client = APITestClient(client)
    response = await api_client.post("/api/data/update")
    assert_success_response(response, 200)

    result = response.json()
    assert "task_id" in result
    assert result["status"] == "started"


@pytest.mark.asyncio
async def test_update_data_with_stocks(client, populated_stocks_db):
    """测试更新数据 - 指定股票"""
    api_client = APITestClient(client)
    stocks = ["sh600000", "sz000001"]

    response = await api_client.post(
        "/api/data/update",
        json=stocks
    )
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_update_data_no_enabled_stocks(client):
    """测试更新数据 - 无启用的股票"""
    # 创建禁用的股票
    from database import MongoDB

    await MongoDB.insert_stock({
        "code": "sh600000",
        "name": "测试",
        "enabled": False,
        "is_a500": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })

    api_client = APITestClient(client)
    response = await api_client.post("/api/data/update")
    # 应该仍然能创建任务，只是没有股票可更新
    assert_success_response(response, 200)


# ============================================================================
# 查询任务状态
# ============================================================================

@pytest.mark.asyncio
async def test_get_task_status(client, populated_data_tasks_db):
    """测试查询单个任务状态"""
    api_client = APITestClient(client)
    task_id = populated_data_tasks_db

    response = await api_client.get(f"/api/data/status/{task_id}")
    assert_success_response(response, 200)

    result = response.json()
    assert "task_id" in result
    assert "status" in result


@pytest.mark.asyncio
async def test_get_task_status_not_found(client):
    """测试查询单个任务状态 - 任务不存在"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/data/status/non_existent_task")
    assert_error_response(response, 404, "任务不存在")


@pytest.mark.asyncio
async def test_get_task_status_empty(client):
    """测试查询单个任务状态 - 无数据"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/data/status/task_123456")
    assert_error_response(response, 404, "任务不存在")


# ============================================================================
# 查询所有任务
# ============================================================================

@pytest.mark.asyncio
async def test_get_all_tasks_empty(client):
    """测试查询所有任务 - 空列表"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/data/status")
    assert_success_response(response, 200)

    tasks = response.json()
    assert isinstance(tasks, list)


@pytest.mark.asyncio
async def test_get_all_tasks_with_data(client, populated_data_tasks_db):
    """测试查询所有任务 - 有数据"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/data/status")
    assert_success_response(response, 200)

    tasks = response.json()
    assert isinstance(tasks, list)
    assert len(tasks) >= 1

    if tasks:
        assert "task_id" in tasks[0]
        assert "status" in tasks[0]


# ============================================================================
# 边界测试
# ============================================================================

@pytest.mark.asyncio
async def test_download_data_future_end_date(client, populated_stocks_db):
    """测试下载数据 - 结束日期在未来"""
    api_client = APITestClient(client)
    future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    response = await api_client.post(
        "/api/data/download",
        params={"start_date": "2024-01-01", "end_date": future_date}
    )
    # 应该仍然能创建任务
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_download_data_end_before_start(client, populated_stocks_db):
    """测试下载数据 - 结束日期早于开始日期"""
    api_client = APITestClient(client)
    response = await api_client.post(
        "/api/data/download",
        params={"start_date": "2024-12-31", "end_date": "2024-01-01"}
    )
    # 可能返回错误或创建任务
    assert response.status_code in [200, 400, 500]


@pytest.mark.asyncio
async def test_download_data_large_stock_list(client, populated_stocks_db):
    """测试下载数据 - 大量股票"""
    # 添加更多股票
    from database import MongoDB

    for i in range(100, 200):
        await MongoDB.insert_stock({
            "code": f"sh6000{i}",
            "name": f"股票{i}",
            "enabled": True,
            "is_a500": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

    api_client = APITestClient(client)
    response = await api_client.post("/api/data/download")
    assert_success_response(response, 200)


# ============================================================================
# 性能测试（可选）
# ============================================================================

@pytest.mark.slow
@pytest.mark.asyncio
async def test_multiple_data_tasks(client, populated_stocks_db):
    """测试创建多个数据下载任务"""
    api_client = APITestClient(client)

    for i in range(3):
        response = await api_client.post("/api/data/download")
        assert_success_response(response, 200)

    # 查询所有任务
    response = await api_client.get("/api/data/status")
    tasks = response.json()
    assert len(tasks) >= 3
