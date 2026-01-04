"""
测试 HTTP 客户端封装
提供统一的接口调用方法和断言辅助函数
"""
from typing import Dict, Any, Optional
from httpx import AsyncClient, Response
import json


class APITestClient:
    """API 测试客户端封装"""

    def __init__(self, client: AsyncClient):
        self.client = client

    async def get(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> Response:
        """
        GET 请求

        Args:
            endpoint: API 端点
            params: 查询参数
            **kwargs: 其他请求参数

        Returns:
            httpx Response 对象
        """
        return await self.client.get(endpoint, params=params, **kwargs)

    async def post(self, endpoint: str, data: Optional[Dict] = None, json: Optional[Dict] = None, **kwargs) -> Response:
        """
        POST 请求

        Args:
            endpoint: API 端点
            data: 表单数据
            json: JSON 数据
            **kwargs: 其他请求参数

        Returns:
            httpx Response 对象
        """
        return await self.client.post(endpoint, data=data, json=json, **kwargs)

    async def put(self, endpoint: str, data: Optional[Dict] = None, json: Optional[Dict] = None, **kwargs) -> Response:
        """
        PUT 请求

        Args:
            endpoint: API 端点
            data: 表单数据
            json: JSON 数据
            **kwargs: 其他请求参数

        Returns:
            httpx Response 对象
        """
        return await self.client.put(endpoint, data=data, json=json, **kwargs)

    async def delete(self, endpoint: str, **kwargs) -> Response:
        """
        DELETE 请求

        Args:
            endpoint: API 端点
            **kwargs: 其他请求参数

        Returns:
            httpx Response 对象
        """
        return await self.client.delete(endpoint, **kwargs)

    async def get_json(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> Dict:
        """
        GET 请求并返回 JSON

        Args:
            endpoint: API 端点
            params: 查询参数
            **kwargs: 其他请求参数

        Returns:
            JSON 响应数据
        """
        response = await self.get(endpoint, params=params, **kwargs)
        return response.json()

    async def post_json(self, endpoint: str, data: Optional[Dict] = None, json: Optional[Dict] = None, **kwargs) -> Dict:
        """
        POST 请求并返回 JSON

        Args:
            endpoint: API 端点
            data: 表单数据
            json: JSON 数据
            **kwargs: 其他请求参数

        Returns:
            JSON 响应数据
        """
        response = await self.post(endpoint, data=data, json=json, **kwargs)
        return response.json()


# ============================================================================
# 断言辅助函数
# ============================================================================

def assert_success_response(response: Response, expected_status_code: int = 200):
    """
    断言响应成功

    Args:
        response: httpx Response 对象
        expected_status_code: 期望的 HTTP 状态码
    """
    assert response.status_code == expected_status_code, (
        f"Expected status {expected_status_code}, got {response.status_code}. "
        f"Response: {response.text}"
    )


def assert_error_response(response: Response, expected_status_code: int, expected_detail: Optional[str] = None):
    """
    断言错误响应

    Args:
        response: httpx Response 对象
        expected_status_code: 期望的 HTTP 状态码
        expected_detail: 期望的错误详情（可选）
    """
    assert response.status_code == expected_status_code, (
        f"Expected status {expected_status_code}, got {response.status_code}. "
        f"Response: {response.text}"
    )

    if expected_detail:
        response_data = response.json()
        assert "detail" in response_data, f"Response missing 'detail' field: {response_data}"
        assert expected_detail in response_data["detail"], (
            f"Expected detail '{expected_detail}', got '{response_data['detail']}'"
        )


def assert_json_keys(response: Response, required_keys: list):
    """
    断言 JSON 响应包含指定的键

    Args:
        response: httpx Response 对象
        required_keys: 必需的键列表
    """
    response_data = response.json()
    missing_keys = [key for key in required_keys if key not in response_data]
    assert not missing_keys, f"Missing keys in response: {missing_keys}. Response: {response_data}"


def assert_list_not_empty(response: Response):
    """
    断言 JSON 响应是非空列表

    Args:
        response: httpx Response 对象
    """
    response_data = response.json()
    assert isinstance(response_data, list), f"Expected list, got {type(response_data)}"
    assert len(response_data) > 0, "Response list is empty"


def assert_field_equals(response: Response, field: str, expected_value: Any):
    """
    断言 JSON 响应中的字段等于期望值

    Args:
        response: httpx Response 对象
        field: 字段名（支持嵌套，如 "data.id"）
        expected_value: 期望的值
    """
    response_data = response.json()

    # 处理嵌套字段
    fields = field.split(".")
    value = response_data
    for f in fields:
        assert f in value, f"Field '{f}' not found in response"
        value = value[f]

    assert value == expected_value, (
        f"Field '{field}' expected {expected_value}, got {value}"
    )


def assert_field_type(response: Response, field: str, expected_type: type):
    """
    断言 JSON 响应中的字段类型

    Args:
        response: httpx Response 对象
        field: 字段名（支持嵌套，如 "data.id"）
        expected_type: 期望的类型
    """
    response_data = response.json()

    # 处理嵌套字段
    fields = field.split(".")
    value = response_data
    for f in fields:
        assert f in value, f"Field '{f}' not found in response"
        value = value[f]

    assert isinstance(value, expected_type), (
        f"Field '{field}' expected type {expected_type}, got {type(value)}"
    )


# ============================================================================
# Stock 模块辅助函数
# ============================================================================

def assert_stock_structure(stock_data: Dict):
    """断言股票数据结构正确"""
    required_fields = ["code", "name", "enabled", "created_at", "updated_at"]
    for field in required_fields:
        assert field in stock_data, f"Stock missing required field: {field}"
    assert isinstance(stock_data["code"], str), "Stock code must be string"
    assert isinstance(stock_data["name"], str), "Stock name must be string"
    assert isinstance(stock_data["enabled"], bool), "Stock enabled must be boolean"


# ============================================================================
# Position 模块辅助函数
# ============================================================================

def assert_position_structure(position_data: Dict):
    """断言持仓数据结构正确"""
    required_fields = ["code", "quantity", "cost_price", "market_value"]
    for field in required_fields:
        assert field in position_data, f"Position missing required field: {field}"
    assert isinstance(position_data["code"], str), "Position code must be string"
    assert isinstance(position_data["quantity"], (int, float)), "Position quantity must be number"
    assert isinstance(position_data["cost_price"], (int, float)), "Position cost_price must be number"
    assert position_data["market_value"] == position_data["quantity"] * position_data["cost_price"], (
        "Position market_value calculation error"
    )


# ============================================================================
# Agent 模块辅助函数
# ============================================================================

def assert_agent_structure(agent_data: Dict):
    """断言代理配置数据结构正确"""
    required_fields = ["agent_id", "agent_url", "agent_token", "agent_name", "is_primary"]
    for field in required_fields:
        assert field in agent_data, f"Agent missing required field: {field}"
    assert isinstance(agent_data["agent_id"], str), "Agent agent_id must be string"
    assert isinstance(agent_data["agent_url"], str), "Agent agent_url must be string"
    assert isinstance(agent_data["is_primary"], bool), "Agent is_primary must be boolean"
