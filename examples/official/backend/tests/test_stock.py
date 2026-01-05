"""
Stock 模块接口测试
测试股票管理的所有接口：增删改查、批量操作、导入导出、初始化
"""
import pytest
from tests.utils.client import (
    APITestClient,
    assert_success_response,
    assert_error_response,
    assert_json_keys,
    assert_stock_structure
)


# ============================================================================
# 测试标记
# ============================================================================

pytestmark = pytest.mark.stock


# ============================================================================
# 获取股票列表
# ============================================================================

@pytest.mark.asyncio
async def test_get_stocks_empty(client):
    """测试获取股票列表 - 空列表"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/stocks/")
    assert_success_response(response, 200)
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_stocks_with_data(client, populated_stocks_db):
    """测试获取股票列表 - 有数据"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/stocks/")
    assert_success_response(response, 200)

    stocks = response.json()
    assert isinstance(stocks, list)
    assert len(stocks) == 5
    assert_stock_structure(stocks[0])


@pytest.mark.asyncio
async def test_get_stocks_enabled_only(client, populated_stocks_db):
    """测试获取股票列表 - 仅启用"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/stocks/", params={"enabled_only": True})
    assert_success_response(response, 200)

    stocks = response.json()
    assert isinstance(stocks, list)
    assert len(stocks) == 4  # 4个启用的股票
    for stock in stocks:
        assert stock["enabled"] is True


# ============================================================================
# 导出股票列表
# ============================================================================

@pytest.mark.asyncio
async def test_export_stocks_csv(client, populated_stocks_db):
    """测试导出股票列表 - CSV 格式"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/stocks/export", params={"format": "csv"})
    assert_success_response(response, 200)
    assert "text/csv" in response.headers.get("content-type", "")
    assert "stocks_" in response.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_export_stocks_excel(client, populated_stocks_db):
    """测试导出股票列表 - Excel 格式"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/stocks/export", params={"format": "excel"})
    assert_success_response(response, 200)
    assert "application/vnd.openxmlformats" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_export_stocks_empty(client):
    """测试导出股票列表 - 空列表"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/stocks/export")
    assert_success_response(response, 200)


# ============================================================================
# 导入股票列表
# ============================================================================

@pytest.mark.asyncio
async def test_import_stocks_csv(client, sample_csv_content):
    """测试导入股票列表 - CSV 格式"""
    from io import BytesIO

    api_client = APITestClient(client)
    csv_content = sample_csv_content.encode('utf-8')
    files = {"file": ("test.csv", BytesIO(csv_content), "text/csv")}

    response = await api_client.post("/api/stocks/import", files=files)
    assert_success_response(response, 200)

    result = response.json()
    assert "message" in result
    assert "imported" in result
    assert "updated" in result
    assert result["imported"] >= 0


@pytest.mark.asyncio
async def test_import_stocks_csv_with_existing(client, populated_stocks_db, sample_csv_content):
    """测试导入股票列表 - 更新已存在的股票"""
    from io import BytesIO

    api_client = APITestClient(client)
    csv_content = sample_csv_content.encode('utf-8')
    files = {"file": ("test.csv", BytesIO(csv_content), "text/csv")}

    response = await api_client.post("/api/stocks/import", files=files)
    assert_success_response(response, 200)

    result = response.json()
    assert result["updated"] > 0 or result["imported"] > 0


@pytest.mark.asyncio
async def test_import_stocks_excel(client, sample_excel_content):
    """测试导入股票列表 - Excel 格式"""
    api_client = APITestClient(client)
    files = {"file": ("test.xlsx", sample_excel_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}

    response = await api_client.post("/api/stocks/import", files=files)
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_import_stocks_invalid_format(client):
    """测试导入股票列表 - 不支持的格式"""
    from io import BytesIO

    api_client = APITestClient(client)
    files = {"file": ("test.txt", BytesIO(b"invalid"), "text/plain")}

    response = await api_client.post("/api/stocks/import", files=files)
    assert_error_response(response, 400, "不支持的文件格式")


@pytest.mark.asyncio
async def test_import_stocks_missing_columns(client):
    """测试导入股票列表 - 缺少必需列"""
    from io import BytesIO
    import pandas as pd

    df = pd.DataFrame({"name": ["测试股票"]})
    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)

    api_client = APITestClient(client)
    files = {"file": ("test.csv", output, "text/csv")}

    response = await api_client.post("/api/stocks/import", files=files)
    assert_error_response(response, 400, "缺少必需的列")


# ============================================================================
# 初始化股票列表
# ============================================================================

@pytest.mark.asyncio
async def test_initialize_stocks_from_csv(client, a500_csv_file):
    """测试从 A500.csv 初始化股票列表"""
    api_client = APITestClient(client)
    response = await api_client.post("/api/stocks/initialize")
    assert_success_response(response, 200)

    result = response.json()
    assert "message" in result
    assert "imported" in result
    assert result["imported"] == 5


@pytest.mark.asyncio
async def test_initialize_stocks_file_not_found(client):
    """测试从 A500.csv 初始化 - 文件不存在"""
    api_client = APITestClient(client)
    response = await api_client.post("/api/stocks/initialize")
    assert_error_response(response, 404, "A500.csv 文件不存在")


# ============================================================================
# 创建股票
# ============================================================================

@pytest.mark.asyncio
async def test_create_stock(client, sample_stock_create):
    """测试创建股票"""
    api_client = APITestClient(client)
    response = await api_client.post("/api/stocks/", json=sample_stock_create)
    assert_success_response(response, 201)

    stock = response.json()
    assert_stock_structure(stock)
    assert stock["code"] == sample_stock_create["code"]
    assert stock["name"] == sample_stock_create["name"]


@pytest.mark.asyncio
async def test_create_stock_duplicate(client, sample_stock_create):
    """测试创建股票 - 重复"""
    api_client = APITestClient(client)

    # 第一次创建
    await api_client.post("/api/stocks/", json=sample_stock_create)

    # 第二次创建（应该失败）
    response = await api_client.post("/api/stocks/", json=sample_stock_create)
    assert_error_response(response, 400, "股票已存在")


@pytest.mark.asyncio
async def test_create_stock_invalid_code(client):
    """测试创建股票 - 无效代码"""
    api_client = APITestClient(client)
    invalid_data = {"code": "", "name": "测试"}
    response = await api_client.post("/api/stocks/", json=invalid_data)
    # 应该返回 422 验证错误
    assert response.status_code in [400, 422]


# ============================================================================
# 删除股票
# ============================================================================

@pytest.mark.asyncio
async def test_delete_stock(client, sample_stock_create):
    """测试删除股票"""
    api_client = APITestClient(client)

    # 先创建
    await api_client.post("/api/stocks/", json=sample_stock_create)

    # 删除
    response = await api_client.delete(f"/api/stocks/{sample_stock_create['code']}")
    assert_success_response(response, 200)

    result = response.json()
    assert "message" in result


@pytest.mark.asyncio
async def test_delete_stock_not_found(client):
    """测试删除股票 - 不存在"""
    api_client = APITestClient(client)
    response = await api_client.delete("/api/stocks/sh999999")
    assert_error_response(response, 404, "股票不存在")


# ============================================================================
# 更新股票
# ============================================================================

@pytest.mark.asyncio
async def test_update_stock(client, sample_stock_create, sample_stock_update):
    """测试更新股票信息"""
    api_client = APITestClient(client)

    # 先创建
    await api_client.post("/api/stocks/", json=sample_stock_create)

    # 更新
    response = await api_client.put(f"/api/stocks/{sample_stock_create['code']}", json=sample_stock_update)
    assert_success_response(response, 200)

    result = response.json()
    assert "message" in result


@pytest.mark.asyncio
async def test_update_stock_not_found(client, sample_stock_update):
    """测试更新股票 - 不存在"""
    api_client = APITestClient(client)
    response = await api_client.put("/api/stocks/sh999999", json=sample_stock_update)
    assert_error_response(response, 404, "股票不存在")


# ============================================================================
# 使能/去使能股票
# ============================================================================

@pytest.mark.asyncio
async def test_enable_stock(client, sample_stock_create):
    """测试启用股票"""
    api_client = APITestClient(client)

    # 先创建
    await api_client.post("/api/stocks/", json=sample_stock_create)

    # 启用
    response = await api_client.put(f"/api/stocks/{sample_stock_create['code']}/enable", params={"enabled": True})
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_disable_stock(client, sample_stock_create):
    """测试禁用股票"""
    api_client = APITestClient(client)

    # 先创建
    await api_client.post("/api/stocks/", json=sample_stock_create)

    # 禁用
    response = await api_client.put(f"/api/stocks/{sample_stock_create['code']}/enable", params={"enabled": False})
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_enable_stock_not_found(client):
    """测试启用股票 - 不存在"""
    api_client = APITestClient(client)
    response = await api_client.put("/api/stocks/sh999999/enable", params={"enabled": True})
    assert_error_response(response, 404, "股票不存在")


# ============================================================================
# 批量操作
# ============================================================================

@pytest.mark.asyncio
async def test_batch_enable_stocks(client, populated_stocks_db):
    """测试批量启用股票"""
    api_client = APITestClient(client)
    codes = ["sh600000", "sh600036"]

    response = await api_client.post("/api/stocks/batch", params={"operation": "enable"}, json={"codes": codes})
    assert_success_response(response, 200)

    result = response.json()
    assert "modified_count" in result


@pytest.mark.asyncio
async def test_batch_disable_stocks(client, populated_stocks_db):
    """测试批量禁用股票"""
    api_client = APITestClient(client)
    codes = ["sh600000", "sh600036"]

    response = await api_client.post("/api/stocks/batch", params={"operation": "disable"}, json={"codes": codes})
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_batch_delete_stocks(client, populated_stocks_db):
    """测试批量删除股票"""
    api_client = APITestClient(client)
    codes = ["sz000001", "sz000002"]

    response = await api_client.post("/api/stocks/batch", params={"operation": "delete"}, json={"codes": codes})
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_batch_operation_invalid(client):
    """测试批量操作 - 无效操作"""
    api_client = APITestClient(client)
    response = await api_client.post("/api/stocks/batch", params={"operation": "invalid"}, json={"codes": []})
    assert_error_response(response, 400, "无效的操作类型")


# ============================================================================
# 边界测试
# ============================================================================

@pytest.mark.asyncio
async def test_stock_code_standardization(client):
    """测试股票代码标准化"""
    api_client = APITestClient(client)

    # 测试数字代码转换为标准格式
    response = await api_client.post("/api/stocks/", json={"code": "600000", "name": "测试股票"})
    # 应该成功处理并标准化为 sh600000
    assert response.status_code in [200, 201]


@pytest.mark.asyncio
async def test_long_stock_name(client):
    """测试超长股票名称"""
    api_client = APITestClient(client)
    long_name = "A" * 200
    response = await api_client.post("/api/stocks/", json={"code": "sh999999", "name": long_name})
    assert_success_response(response, 201)
