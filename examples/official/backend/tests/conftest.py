"""
pytest 配置文件和共享 fixtures
"""
import pytest
import asyncio
from pathlib import Path
from typing import AsyncGenerator
from datetime import datetime
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from database import MongoDB
from config import settings


# ============================================================================
# 异步事件循环
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于所有测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# FastAPI 测试客户端
# ============================================================================

@pytest.fixture
async def client():
    """异步 HTTP 测试客户端"""
    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# ============================================================================
# MongoDB 测试数据库连接
# ============================================================================

@pytest.fixture(scope="function", autouse=True)
async def setup_test_db():
    """
    设置测试数据库
    每个测试函数执行前自动调用，执行后清理数据
    """
    # 连接到测试数据库
    original_db_name = settings.MONGODB_DB_NAME
    settings.MONGODB_DB_NAME = f"{original_db_name}_test"

    await MongoDB.connect_to_mongodb()

    yield

    # 清理测试数据
    await cleanup_test_data()

    # 关闭连接
    await MongoDB.close_mongodb()

    # 恢复原始数据库名称
    settings.MONGODB_DB_NAME = original_db_name


async def cleanup_test_data():
    """清理测试数据库中的所有集合"""
    if MongoDB.database:
        collections = await MongoDB.database.list_collection_names()
        for collection in collections:
            await MongoDB.database[collection].delete_many({})


# ============================================================================
# 测试日志目录
# ============================================================================

@pytest.fixture
def log_dir():
    """创建临时日志目录"""
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    original_log_dir = settings.LOG_DIR
    settings.LOG_DIR = str(temp_dir)

    yield temp_dir

    # 清理
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    settings.LOG_DIR = original_log_dir


# ============================================================================
# A500.csv 测试文件
# ============================================================================

@pytest.fixture
def a500_csv_file():
    """创建临时 A500.csv 测试文件"""
    import tempfile
    import csv

    temp_dir = Path(tempfile.mkdtemp())
    csv_path = temp_dir / "A500.csv"

    # 创建测试数据
    test_stocks = [
        ["成份券代码Constituent Code", "成份券名称Constituent Name"],
        ["600000", "浦发银行"],
        ["600036", "招商银行"],
        ["601318", "中国平安"],
        ["000001", "平安银行"],
        ["000002", "万科A"],
    ]

    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerows(test_stocks)

    original_cwd = Path.cwd()
    import os
    try:
        os.chdir(temp_dir)
        yield csv_path
    finally:
        os.chdir(original_cwd)
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# Mock httpx 客户端（用于模拟外部 API 调用）
# ============================================================================

@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient 用于模拟外部 API 调用"""
    from unittest.mock import AsyncMock, patch

    with patch('httpx.AsyncClient') as mock:
        async_client = AsyncMock()
        mock.return_value.__aenter__.return_value = async_client
        yield async_client


# ============================================================================
# 测试数据工厂函数
# ============================================================================

def create_test_stock(code: str = "sh600000", name: str = "测试股票", enabled: bool = True):
    """创建测试股票数据"""
    return {
        "code": code,
        "name": name,
        "enabled": enabled,
        "is_a500": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }


def create_test_position(code: str = "sh600000", quantity: float = 1000.0, cost_price: float = 10.0):
    """创建测试持仓数据"""
    return {
        "code": code,
        "name": "测试股票",
        "quantity": quantity,
        "cost_price": cost_price,
        "market_value": quantity * cost_price,
        "pnl": 0.0,
        "pnl_percent": 0.0,
        "added_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }


def create_test_agent_config(agent_id: str = "test_agent_001"):
    """创建测试代理配置"""
    return {
        "agent_id": agent_id,
        "agent_url": "http://test-agent.example.com",
        "agent_token": "test_token_123",
        "agent_name": "Test Agent",
        "is_primary": False,
        "status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }


def create_test_prediction(date: str = "2025-01-04", code: str = "sh600000", score: float = 0.85):
    """创建测试预测数据"""
    return {
        "date": date,
        "code": code,
        "name": "测试股票",
        "score": score,
        "rank": 1,
        "is_held": False,
        "created_at": datetime.utcnow()
    }


# ============================================================================
# 辅助函数
# ============================================================================

@pytest.fixture
def stock_factory():
    """股票数据工厂 fixture"""
    return create_test_stock


@pytest.fixture
def position_factory():
    """持仓数据工厂 fixture"""
    return create_test_position


@pytest.fixture
def agent_factory():
    """代理配置工厂 fixture"""
    return create_test_agent_config


@pytest.fixture
def prediction_factory():
    """预测数据工厂 fixture"""
    return create_test_prediction
