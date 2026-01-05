"""
Predict 模块接口测试
测试预测管理的所有接口：执行预测、查询预测结果、查询任务状态
"""
import pytest
from datetime import datetime
from tests.utils.client import (
    APITestClient,
    assert_success_response,
    assert_error_response,
    assert_json_keys
)


# ============================================================================
# 测试标记
# ============================================================================

pytestmark = pytest.mark.predict


# ============================================================================
# 执行预测
# ============================================================================

@pytest.mark.asyncio
async def test_predict_default_params(client, populated_stocks_db):
    """测试执行预测 - 默认参数"""
    api_client = APITestClient(client)
    response = await api_client.post("/api/predict/")
    assert_success_response(response, 200)

    result = response.json()
    assert "task_id" in result
    assert "status" in result
    assert "predict_date" in result
    assert "stocks_count" in result
    assert result["status"] == "started"


@pytest.mark.asyncio
async def test_predict_with_date(client, populated_stocks_db):
    """测试执行预测 - 指定日期"""
    api_client = APITestClient(client)
    predict_date = "2025-01-01"

    response = await api_client.post(
        "/api/predict/",
        params={"predict_date": predict_date}
    )
    assert_success_response(response, 200)

    result = response.json()
    assert result["predict_date"] == predict_date


@pytest.mark.asyncio
async def test_predict_with_stocks(client, populated_stocks_db):
    """测试执行预测 - 指定股票"""
    api_client = APITestClient(client)
    stocks = ["sh600000", "sh600036"]

    response = await api_client.post(
        "/api/predict/",
        json=stocks
    )
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_predict_no_enabled_stocks(client):
    """测试执行预测 - 无启用的股票"""
    api_client = APITestClient(client)
    response = await api_client.post("/api/predict/")
    # 应该仍然能创建任务，只是没有股票可预测
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_predict_invalid_date_format(client):
    """测试执行预测 - 无效日期格式"""
    api_client = APITestClient(client)
    response = await api_client.post(
        "/api/predict/",
        params={"predict_date": "invalid-date"}
    )
    # 可能返回 400 或 500 错误
    assert response.status_code in [400, 500]


# ============================================================================
# 查询预测结果
# ============================================================================

@pytest.mark.asyncio
async def test_get_predictions_empty(client):
    """测试查询预测结果 - 空列表"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/predict/results")
    assert_success_response(response, 200)

    predictions = response.json()
    assert isinstance(predictions, list)


@pytest.mark.asyncio
async def test_get_predictions_with_data(client, populated_predictions_db):
    """测试查询预测结果 - 有数据"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/predict/results")
    assert_success_response(response, 200)

    predictions = response.json()
    assert isinstance(predictions, list)
    assert len(predictions) >= 1

    if predictions:
        assert "date" in predictions[0]
        assert "code" in predictions[0]
        assert "score" in predictions[0]


@pytest.mark.asyncio
async def test_get_predictions_by_date(client, populated_predictions_db):
    """测试查询预测结果 - 按日期筛选"""
    api_client = APITestClient(client)
    date = "2025-01-04"

    response = await api_client.get(
        "/api/predict/results",
        params={"date": date}
    )
    assert_success_response(response, 200)

    predictions = response.json()
    for pred in predictions:
        assert pred["date"] == date


@pytest.mark.asyncio
async def test_get_predictions_by_code(client, populated_predictions_db):
    """测试查询预测结果 - 按股票代码筛选"""
    api_client = APITestClient(client)
    code = "sh600000"

    response = await api_client.get(
        "/api/predict/results",
        params={"code": code}
    )
    assert_success_response(response, 200)

    predictions = response.json()
    for pred in predictions:
        assert pred["code"] == code


@pytest.mark.asyncio
async def test_get_predictions_sort_by_score(client, populated_predictions_db):
    """测试查询预测结果 - 按得分排序"""
    api_client = APITestClient(client)
    response = await api_client.get(
        "/api/predict/results",
        params={"sort_by": "score", "sort_order": "desc"}
    )
    assert_success_response(response, 200)

    predictions = response.json()
    if len(predictions) > 1:
        # 验证是否按得分降序排列
        scores = [p["score"] for p in predictions]
        assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_get_predictions_sort_by_code(client, populated_predictions_db):
    """测试查询预测结果 - 按代码排序"""
    api_client = APITestClient(client)
    response = await api_client.get(
        "/api/predict/results",
        params={"sort_by": "code", "sort_order": "asc"}
    )
    assert_success_response(response, 200)

    predictions = response.json()
    if len(predictions) > 1:
        # 验证是否按代码升序排列
        codes = [p["code"] for p in predictions]
        assert codes == sorted(codes)


@pytest.mark.asyncio
async def test_get_predictions_with_limit(client, populated_predictions_db):
    """测试查询预测结果 - 限制返回数量"""
    api_client = APITestClient(client)
    limit = 2

    response = await api_client.get(
        "/api/predict/results",
        params={"limit": limit}
    )
    assert_success_response(response, 200)

    predictions = response.json()
    assert len(predictions) <= limit


@pytest.mark.asyncio
async def test_get_predictions_filter_held(client, populated_predictions_db, populated_positions_db):
    """测试查询预测结果 - 筛选已持仓"""
    api_client = APITestClient(client)
    response = await api_client.get(
        "/api/predict/results",
        params={"filter_type": "held"}
    )
    assert_success_response(response, 200)

    predictions = response.json()
    # 所有返回的预测都应该是持仓中的股票
    for pred in predictions:
        assert pred.get("is_held", False) is True


@pytest.mark.asyncio
async def test_get_predictions_filter_not_held(client, populated_predictions_db, populated_positions_db):
    """测试查询预测结果 - 筛选未持仓"""
    api_client = APITestClient(client)
    response = await api_client.get(
        "/api/predict/results",
        params={"filter_type": "not_held"}
    )
    assert_success_response(response, 200)

    predictions = response.json()
    # 所有返回的预测都应该是非持仓中的股票
    for pred in predictions:
        assert pred.get("is_held", True) is False


@pytest.mark.asyncio
async def test_get_predictions_invalid_sort_field(client, populated_predictions_db):
    """测试查询预测结果 - 无效排序字段"""
    api_client = APITestClient(client)
    response = await api_client.get(
        "/api/predict/results",
        params={"sort_by": "invalid_field"}
    )
    # 应该使用默认排序字段
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_get_predictions_invalid_filter_type(client, populated_predictions_db):
    """测试查询预测结果 - 无效筛选类型"""
    api_client = APITestClient(client)
    response = await api_client.get(
        "/api/predict/results",
        params={"filter_type": "invalid_type"}
    )
    # 应该返回所有结果
    assert_success_response(response, 200)


# ============================================================================
# 查询所有预测任务
# ============================================================================

@pytest.mark.asyncio
async def test_get_all_prediction_tasks(client):
    """测试查询所有预测任务"""
    api_client = APITestClient(client)
    response = await api_client.get("/api/predict/status")
    assert_success_response(response, 200)

    tasks = response.json()
    assert isinstance(tasks, list)


# ============================================================================
# 边界测试
# ============================================================================

@pytest.mark.asyncio
async def test_predict_large_stock_list(client):
    """测试执行预测 - 大量股票"""
    # 添加大量股票
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
    response = await api_client.post("/api/predict/")
    assert_success_response(response, 200)

    result = response.json()
    assert result["stocks_count"] >= 100


@pytest.mark.asyncio
async def test_predict_future_date(client, populated_stocks_db):
    """测试执行预测 - 未来日期"""
    from datetime import timedelta

    future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    api_client = APITestClient(client)
    response = await api_client.post(
        "/api/predict/",
        params={"predict_date": future_date}
    )
    # 应该仍然能创建任务
    assert_success_response(response, 200)


@pytest.mark.asyncio
async def test_get_predictions_limit_zero(client, populated_predictions_db):
    """测试查询预测结果 - 限制为0"""
    api_client = APITestClient(client)
    response = await api_client.get(
        "/api/predict/results",
        params={"limit": 0}
    )
    assert_success_response(response, 200)

    predictions = response.json()
    assert len(predictions) == 0


@pytest.mark.asyncio
async def test_get_predictions_large_limit(client, populated_predictions_db):
    """测试查询预测结果 - 大限制值"""
    api_client = APITestClient(client)
    response = await api_client.get(
        "/api/predict/results",
        params={"limit": 10000}
    )
    assert_success_response(response, 200)
