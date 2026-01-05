"""
测试数据 fixtures
提供预定义的测试数据和数据生成器
"""
import pytest
from typing import List, Dict
from datetime import datetime, timedelta


# ============================================================================
# 股票测试数据
# ============================================================================

TEST_STOCKS = [
    {
        "code": "sh600000",
        "name": "浦发银行",
        "enabled": True,
        "is_a500": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "code": "sh600036",
        "name": "招商银行",
        "enabled": True,
        "is_a500": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "code": "sh601318",
        "name": "中国平安",
        "enabled": True,
        "is_a500": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "code": "sz000001",
        "name": "平安银行",
        "enabled": False,
        "is_a500": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "code": "sz000002",
        "name": "万科A",
        "enabled": True,
        "is_a500": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
]


@pytest.fixture
def sample_stocks():
    """提供示例股票数据列表"""
    return TEST_STOCKS.copy()


@pytest.fixture
async def populated_stocks_db():
    """
    填充股票数据的数据库
    返回填充后的股票代码列表
    """
    from database import MongoDB

    stock_codes = []
    for stock in TEST_STOCKS:
        await MongoDB.insert_stock(stock)
        stock_codes.append(stock["code"])

    yield stock_codes

    # 清理会在 setup_test_db fixture 中自动处理


@pytest.fixture
def sample_stock_create():
    """提供创建股票的请求数据"""
    return {
        "code": "sh601988",
        "name": "中国银行",
        "is_a500": False
    }


@pytest.fixture
def sample_stock_update():
    """提供更新股票的请求数据"""
    return {
        "name": "浦发银行（更新）",
        "enabled": False,
        "is_a500": False
    }


# ============================================================================
# 持仓测试数据
# ============================================================================

TEST_POSITIONS = [
    {
        "code": "sh600000",
        "name": "浦发银行",
        "quantity": 1000.0,
        "cost_price": 10.50,
        "market_value": 10500.0,
        "pnl": 500.0,
        "pnl_percent": 5.0,
        "added_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "code": "sh600036",
        "name": "招商银行",
        "quantity": 500.0,
        "cost_price": 35.80,
        "market_value": 17900.0,
        "pnl": -900.0,
        "pnl_percent": -4.8,
        "added_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
]


@pytest.fixture
def sample_positions():
    """提供示例持仓数据列表"""
    return TEST_POSITIONS.copy()


@pytest.fixture
async def populated_positions_db():
    """
    填充持仓数据的数据库
    返回填充后的持仓代码列表
    """
    from database import MongoDB

    position_codes = []
    for position in TEST_POSITIONS:
        await MongoDB.insert_position(position)
        position_codes.append(position["code"])

    yield position_codes


@pytest.fixture
def sample_position_create():
    """提供创建持仓的请求数据"""
    return {
        "code": "sh601318",
        "quantity": 200.0,
        "cost_price": 50.25,
        "name": "中国平安"
    }


@pytest.fixture
def sample_position_update():
    """提供更新持仓的请求数据"""
    return {
        "quantity": 300.0,
        "cost_price": 48.50
    }


# ============================================================================
# 代理配置测试数据
# ============================================================================

TEST_AGENTS = [
    {
        "agent_id": "agent_primary_001",
        "agent_url": "http://primary-agent.example.com",
        "agent_token": "primary_token_abc123",
        "agent_name": "Primary Agent",
        "is_primary": True,
        "status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "agent_id": "agent_backup_001",
        "agent_url": "http://backup-agent.example.com",
        "agent_token": "backup_token_def456",
        "agent_name": "Backup Agent",
        "is_primary": False,
        "status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
]


@pytest.fixture
def sample_agents():
    """提供示例代理配置列表"""
    return TEST_AGENTS.copy()


@pytest.fixture
async def populated_agents_db():
    """
    填充代理配置的数据库
    返回填充后的代理 ID 列表
    """
    from database import MongoDB

    agent_ids = []
    for agent in TEST_AGENTS:
        await MongoDB.database.agent_configs.insert_one(agent)
        agent_ids.append(agent["agent_id"])

    yield agent_ids


@pytest.fixture
def sample_agent_config_create():
    """提供创建代理配置的请求数据"""
    return {
        "agent_url": "http://new-agent.example.com",
        "agent_token": "new_token_xyz789",
        "agent_name": "New Test Agent"
    }


# ============================================================================
# 预测测试数据
# ============================================================================

def generate_test_predictions(date: str = None, count: int = 5) -> List[Dict]:
    """
    生成测试预测数据

    Args:
        date: 预测日期（默认为今天）
        count: 生成数量

    Returns:
        预测数据列表
    """
    if date is None:
        date = datetime.utcnow().strftime("%Y-%m-%d")

    execution_timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    stocks = [
        ("sh600000", "浦发银行"),
        ("sh600036", "招商银行"),
        ("sh601318", "中国平安"),
        ("sz000001", "平安银行"),
        ("sz000002", "万科A"),
    ]

    predictions = []
    for i in range(min(count, len(stocks))):
        predictions.append({
            "date": date,
            "code": stocks[i][0],
            "name": stocks[i][1],
            "score": 0.95 - (i * 0.1),
            "rank": i + 1,
            "is_held": False,
            "execution_timestamp": execution_timestamp,
            "data_date": date,
            "created_at": datetime.utcnow()
        })

    return predictions


@pytest.fixture
def sample_predictions():
    """提供示例预测数据列表"""
    return generate_test_predictions()


@pytest.fixture
async def populated_predictions_db():
    """
    填充预测数据的数据库
    返回填充后的预测数据列表
    """
    from database import MongoDB

    predictions = generate_test_predictions()
    for prediction in predictions:
        await MongoDB.database.predictions.insert_one(prediction)

    yield predictions


# ============================================================================
# 数据下载任务测试数据
# ============================================================================

@pytest.fixture
def sample_data_task():
    """提供示例数据下载任务"""
    return {
        "task_id": "task_20250104_001",
        "status": "completed",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "total_stocks": 5,
        "progress": 100,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }


@pytest.fixture
async def populated_data_tasks_db():
    """
    填充数据下载任务的数据库
    返回任务 ID
    """
    from database import MongoDB

    task = {
        "task_id": "task_20250104_001",
        "status": "completed",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "total_stocks": 5,
        "completed": 5,
        "failed": 0,
        "progress": 100,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    await MongoDB.database.data_tasks.insert_one(task)
    yield task["task_id"]


# ============================================================================
# 边界测试数据
# ============================================================================

@pytest.fixture
def boundary_test_stocks():
    """边界测试股票数据（空字符串、极值等）"""
    return [
        {
            "code": "sh999999",
            "name": "测试",
            "enabled": True,
            "is_a500": False
        },
        {
            "code": "sz000001",
            "name": "A" * 100,  # 超长名称
            "enabled": True,
            "is_a500": False
        },
    ]


@pytest.fixture
def boundary_test_positions():
    """边界测试持仓数据（零值、负值等）"""
    return [
        {
            "code": "sh999999",
            "quantity": 0.0,  # 零持仓
            "cost_price": 10.0,
            "name": "测试"
        },
        {
            "code": "sz000001",
            "quantity": 1.0,  # 最小单位
            "cost_price": 0.01,  # 最小价格
            "name": "测试"
        },
    ]


# ============================================================================
# CSV 文件测试数据
# ============================================================================

@pytest.fixture
def sample_csv_content():
    """提供示例 CSV 文件内容"""
    return """code,name,enabled,is_a500
sh600000,浦发银行,True,True
sh600036,招商银行,True,True
sz000001,平安银行,False,False"""


@pytest.fixture
def sample_excel_content():
    """提供示例 Excel 文件（使用 BytesIO）"""
    from io import BytesIO
    import pandas as pd

    data = {
        "code": ["sh600000", "sh600036", "sz000001"],
        "name": ["浦发银行", "招商银行", "平安银行"],
        "enabled": [True, True, False],
        "is_a500": [True, True, False]
    }

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)

    return output
