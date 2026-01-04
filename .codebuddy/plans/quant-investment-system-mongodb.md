# 量化投资管理系统实现计划

## 项目概述
在 `examples/official` 目录下创建一个基于 FastAPI 的量化投资管理系统，使用 MongoDB 存储数据，并利用 Qlib 在线模式进行数据管理。

## 技术栈

### 后端
- **框架**: FastAPI (Python 3.8+)
- **端口**: 8000
- **数据库**: MongoDB (Motor 异步)
- **Qlib 模式**: 在线模式 (Online Mode)
- **多进程**: Python multiprocessing
- **数据处理**: Qlib + Alpha158
- **日志**: loguru
- **API数据源**: 腾讯财经 API
- **HTTP 客户端**: httpx

### 前端
- **框架**: Vue.js 3 + Element Plus
- **构建**: Vite
- **调试**: 支持前后端联调模式

### 数据存储
- **MongoDB**: 存储股票列表、持仓、预测结果、代理配置、交易订单
- **Qlib数据**: 在线模式共享数据服务
- **Redis**: Qlib 表达式缓存和数据集缓存（在线模式）

---

## 项目目录结构

```
examples/official/
├── backend/                 # 后端代码
│   ├── __init__.py
│   ├── main.py            # FastAPI 应用入口
│   ├── config.py          # 配置管理
│   ├── database.py         # MongoDB 操作
│   ├── models.py          # 数据模型（Pydantic）
│   ├── api/
│   │   ├── __init__.py
│   │   ├── stock.py       # 代码管理 API
│   │   ├── data.py        # 数据管理 API
│   │   ├── predict.py     # 预测 API
│   │   ├── position.py     # 持仓管理 API（含交易操作）
│   │   ├── agent.py        # 交易代理管理 API
│   │   └── log.py        # 日志下载 API
│   ├── services/
│   │   ├── __init__.py
│   │   ├── data_service.py        # 腾讯数据下载服务
│   │   ├── prediction_service.py   # 多进程预测服务
│   │   ├── qlib_service.py      # Qlib 在线模式封装
│   │   ├── mongo_service.py      # MongoDB 操作服务
│   │   ├── agent_service.py      # 交易代理服务
│   │   └── agent_client.py       # 交易代理 HTTP 客户端
│   ├── workers/
│   │   ├── __init__.py
│   │   └── predict_worker.py      # 多进程预测工作进程
│   └── requirements.txt
├── frontend/                # 前端代码
│   ├── index.html
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── components/
│   │   │   ├── StockManager.vue      # 代码管理
│   │   │   ├── DataManager.vue        # 数据管理
│   │   │   ├── PredictResult.vue     # 预测结果
│   │   │   ├── PositionManager.vue   # 持仓管理（含交易操作）
│   │   ├── AgentManager.vue      # 交易代理管理
│   │   ├── TradeManager.vue       # 交易管理（基于预测结果）
│   │   └── LogManager.vue         # 日志管理
│   │   ├── api/
│   │   │   ├── stock.js
│   │   │   ├── data.js
│   │   │   ├── predict.js
│   │   ├── position.js
│   │   ├── agent.js
│   │   └── trade.js            # 交易 API
│   │   └── utils/
│   │       └── request.js    # Axios 封装
│   ├── package.json
│   └── vite.config.js
├── A500.csv               # 默认股票列表（中证500成分股）
├── README.md
└── config.yaml            # 系统配置文件
└── trade_agent.md           # 交易代理接口文档
```

---

## 核心功能模块

1. **代码管理** - 默认为空，支持从 A500.csv 重新初始化代码列表，支持增删改和批量操作（支持多选和连续多选）
2. **数据管理** - 腾讯 API 下载日线数据，使用 Qlib 在线模式，支持初始下载和增量更新
3. **预测功能** - 使用 Alpha158 因子 + 多进程加速，支持历史查询、排序和持仓筛选
4. **持仓管理** - 导入导出持仓，管理持仓的添加/删除/修改（支持多选和批量操作），支持买入/卖出/同步操作
5. **交易代理管理** - 配置管理（URL、Token、状态查询），查询代理持仓，提交/查询订单
6. **交易管理** - 基于预测结果的买入/卖出操作，按预测得分排序
7. **日志管理** - 后端日志输出和前端打包下载

---

## Qlib 在线模式配置

### 配置说明
Qlib 支持两种模式：

#### Online Mode（在线模式）
- 数据作为共享服务部署
- 所有客户端共享数据和缓存
- 提高数据检索性能（缓存命中率更高）
- 减少磁盘空间占用
- 需要 Redis 作为缓存层
- 需要独立的数据服务器进程

### Server 模式配置项
```python
"server": {
    "provider_uri": "",  # 数据路径
    "redis_host": "127.0.0.1",  # Redis 主机
    "redis_port": 6379,  # Redis 端口
    "redis_task_db": 1,  # Redis 任务数据库
    "expression_cache": "DiskExpressionCache",  # 表达式缓存
    "dataset_cache": "DiskDatasetCache",  # 数据集缓存
    "local_cache_path": Path("~/.cache/qlib_simple_cache").expanduser().resolve(),
    "mount_path": None,
}
```

---

## MongoDB 数据库设计

### 数据库结构

```python
# Collections:

# 1. stocks - 股票列表
{
    "_id": ObjectId,
    "code": "sh600000",      # 股票代码
    "name": "平安银行",        # 股票名称
    "enabled": true,           # 是否启用
    "is_a500": true,          # 是否来自 A500
    "created_at": datetime,
    "updated_at": datetime,
}

# 2. positions - 持仓列表
{
    "_id": ObjectId,
    "code": "sh600000",      # 股票代码
    "name": "平安银行",        # 股票名称
    "quantity": 1000,        # 持仓数量
    "cost_price": 12.50,     # 成本价
    "market_value": 12500.00,  # 市值
    "pnl": 1250.00,            # 盈亏
    "pnl_percent": 10.00,  # 盈亏百分比
    "added_at": datetime,
    "updated_at": datetime,
}

# 3. predictions - 预测结果
{
    "_id": ObjectId,
    "date": "2024-01-15",    # 预测日期
    "code": "sh600000",        # 股票代码
    "name": "平安银行",          # 股票名称
    "score": 0.85,            # 预测得分
    "rank": 5,                # 排名
    "is_held": False,           # 是否持仓
    "created_at": datetime,
}

# 4. agent_config - 代理配置
{
    "_id": ObjectId,
    "agent_url": str,           # 代理 URL
    "agent_token": str,        # 代理 Token
    "agent_name": str,           # 代理名称
    "status": str,             # 状态（active/inactive）
    "created_at": datetime,
    "updated_at": datetime,
}

# 5. agent_positions - 代理持仓记录
{
    "_id": ObjectId,
    "code": "sh600000",      # 股票代码
    "name": "平安银行",        # 股票名称
    "quantity": 1000,        # 持仓数量
    "cost_price": 12.50,     # 成本价
    "market_value": 12500.00,  # 市值
    "pnl": 1250.00,            # 盈亏
    "pnl_percent": 10.00,  # 盈亏百分比
    "added_at": datetime,
    "synced_at": datetime,    # 同步时间
}

# 6. local_positions - 本地持仓（与代理持仓不同步）
{
    "_id": ObjectId,
    "code": "sh600000",      # 股票代码
    "name": "平安银行",        # 股票名称
    "quantity": 1000,        # 持仓数量
    "cost_price": 12.50,     # 成本价
    "market_value": 12500.00,  # 市值
    "pnl": 1250.00,            # 盈亏
    "pnl_percent": 10.00,  # 盈亏百分比
    "added_at": datetime,
    "updated_at": datetime,
}

# 7. agent_logs - 代理请求日志
{
    "_id": ObjectId,
    "request": dict,          # 请求数据
    "response": dict,         # 响应数据
    "timestamp": datetime,
}

# 8. data_tasks - 数据下载任务
{
    "_id": ObjectId,
    "task_id": "task_001",
    "status": "pending",  # pending, running, completed, failed
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "created_at": datetime,
    "updated_at": datetime,
}
```

---

## 核心功能实现

### 1. 代码管理模块

#### 后端实现 (backend/api/stock.py)
```python
from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from ..database import MongoDB
from ..models import StockCreate, StockUpdate, StockResponse
from datetime import datetime
from ..services.data_service import standardize_stock_codes

router = APIRouter(prefix="/api/stocks", tags=["Stocks"])

@router.get("/", response_model=List[StockResponse])
async def get_stocks(enabled_only: bool = False):
    """获取股票列表（默认返回空列表）"""
    return await MongoDB.get_stocks(enabled_only=enabled_only)

@router.post("/initialize")
async def initialize_stocks_from_csv():
    """
    重新初始化代码列表
    从 A500.csv 文件读取股票列表，清空现有数据并导入
    """
    try:
        import pandas as pd
        from pathlib import Path

        csv_path = Path("A500.csv")
        if not csv_path.exists():
            raise HTTPException(status_code=404, detail="A500.csv file not found")

        # 读取 A500.csv
        df = pd.read_csv(csv_path)
        stock_codes = df['成份券代码Constituent Code'].tolist()

        # 标准化股票代码格式
        standardized_codes = standardize_stock_codes(stock_codes)

        # 清空现有股票列表
        await MongoDB.clear_all_stocks()

        # 批量导入新股票
        imported = 0
        for code, name in zip(standardized_codes, stock_codes):
            await MongoDB.insert_stock({
                "code": code,
                "name": name,
                "enabled": True,
                "is_a500": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            })
            imported += 1

        return {
            "message": f"Successfully initialized {imported} stocks from A500.csv",
            "imported": imported,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize stocks: {str(e)}")

@router.post("/", response_model=StockResponse)
async def create_stock(stock: StockCreate):
    """添加股票"""
    existing = await MongoDB.get_stock(stock.code)
    if existing:
        raise HTTPException(status_code=400, detail="Stock already exists")

    stock_dict = stock.dict()
    stock_dict["created_at"] = datetime.utcnow()
    stock_dict["updated_at"] = datetime.utcnow()
    await MongoDB.insert_stock(stock_dict)
    return StockResponse(**stock_dict)

@router.delete("/{code}")
async def delete_stock(code: str):
    """删除股票"""
    success = await MongoDB.delete_stock(code)
    if not success:
        raise HTTPException(status_code=404, detail="Stock not found")
    return {"message": "Stock deleted successfully"}

@router.put("/{code}/enable")
async def enable_stock(code: str, enabled: bool):
    """使能/去使能股票"""
    success = await MongoDB.update_stock(code, {"enabled": enabled})
    if not success:
        raise HTTPException(status_code=404, detail="Stock not found")
    return {"message": f"Stock {code} {'enabled' if enabled else 'disabled'} successfully"}

@router.post("/batch")
async def batch_operations(operation: str, codes: List[str]):
    """
    批量操作（支持多选和连续多选）

    Args:
        operation: 操作类型（enable/disable/delete）
        codes: 选中的股票代码列表（支持多选）

    Returns:
        操作结果统计
    """
    if operation == "enable":
        result = await MongoDB.batch_update_stocks(codes, {"enabled": True})
    elif operation == "disable":
        result = await MongoDB.batch_update_stocks(codes, {"enabled": False})
    elif operation == "delete":
        result = await MongoDB.batch_delete_stocks(codes)
    else:
        raise HTTPException(status_code=400, detail="Invalid operation")
    return {"modified_count": result}
```

#### 数据模型 (backend/models.py)
```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class StockCreate(BaseModel):
    code: str = Field(..., description="股票代码，格式: sh600000")
    name: str = Field(..., description="股票名称")
    is_a500: bool = Field(default=False, description="是否来自 A500")

class StockUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None

class StockResponse(StockCreate):
    enabled: bool = Field(default=True, description="是否启用")
    created_at: datetime
    updated_at: datetime
```

#### 前端界面 (StockManager.vue)
- 初始状态：股票列表为空
- "重新初始化代码列表"按钮（从 A500.csv 读取并清空现有数据）
- 表格功能：
  - 复选框：支持单个选择
  - 全选/取消全选：支持全选和反选
  - 连选：Shift + 点击支持连续多选
- 添加/删除按钮
- 启用/禁用开关
- 批量操作：
  - 批量启用：将选中的股票全部启用
  - 批量禁用：将选中的股票全部禁用
  - 批量删除：删除选中的所有股票
- 搜索和筛选功能

---

### 2. 数据管理模块

#### 后端实现 (backend/api/data.py)
```python
from fastapi import APIRouter, BackgroundTasks
from datetime import datetime
from ..services.data_service import TencentDataService
from ..services.qlib_service import QlibOnlineService
from ..services.mongo_service import MongoDB

router = APIRouter(prefix="/api/data", tags=["Data"])

@router.get("/latest_date")
async def get_latest_data_date():
    """获取最新数据日期"""
    qlib_service = QlibOnlineService()
    return await qlib_service.get_latest_data_date()

@router.post("/download")
async def download_data(
    background_tasks: BackgroundTasks,
    start_date: str = "2015-01-01",
    end_date: str = None,
    stocks: List[str] = None
):
    """下载数据"""
    task_id = await TencentDataService.create_download_task(
        start_date=start_date,
        end_date=end_date,
        stocks=stocks
    )
    background_tasks.add_task(TencentDataService.run_download, task_id)
    return {
        "task_id": task_id,
        "status": "started",
        "message": "Data download task started"
    }

@router.post("/update")
async def update_data(
    background_tasks: BackgroundTasks,
    stocks: List[str] = None
):
    """增量更新数据"""
    task_id = await TencentDataService.create_update_task(stocks=stocks)
    background_tasks.add_task(TencentDataService.run_update, task_id)
    return {
        "task_id": task_id,
        "status": "started",
        "message": "Data update task started"
    }

@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """查询任务状态"""
    task = await MongoDB.get_data_task(task_id)
    return task

@router.get("/status")
async def get_all_tasks():
    """查询所有下载任务状态"""
    return await MongoDB.get_all_data_tasks()
```

#### 腾讯数据下载服务 (backend/services/data_service.py)
```python
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from pathlib import Path
import requests
import pandas as pd
from loguru import logger
from ..services.mongo_service import MongoDB

class TencentDataService:
    BASE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    INTERVAL_DAY = "day"
    REQUEST_TIMEOUT = 30
    RETRY_COUNT = 3
    RETRY_DELAY = 1

    @staticmethod
    def standardize_stock_codes(codes: List[str]) -> List[str]:
        """
        标准化股票代码格式

        将数字股票代码转换为 Qlib 需要的格式：
        - 上海股票（60开头，688开头）：sh600000
        - 深圳股票（00开头，30开头）：sz000001

        Args:
            codes: 原始股票代码列表

        Returns:
            标准化后的股票代码列表
        """
        standardized = []
        for code in codes:
            code_str = str(code).zfill(6)  # 补零到6位
            if code_str.startswith('6') or code_str.startswith('688'):
                # 上海股票
                standardized.append(f'sh{code_str}')
            elif code_str.startswith('00') or code_str.startswith('30'):
                # 深圳股票
                standardized.append(f'sz{code_str}')
            else:
                logger.warning(f"Unknown stock code format: {code_str}")
        return standardized

    @staticmethod
    async def create_download_task(start_date: str, end_date: str, stocks: List[str]) -> str:
        """创建下载任务并保存到 MongoDB"""
        from ..services.mongo_service import MongoDB

        task_id = f"download_{datetime.now().timestamp()}"
        await MongoDB.insert_data_task({
            "task_id": task_id,
            "status": "pending",
            "start_date": start_date,
            "end_date": end_date or datetime.now().strftime("%Y-%m-%d"),
            "stocks": stocks or [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })
        return task_id

    @staticmethod
    async def create_update_task(stocks: List[str]) -> str:
        """创建更新任务并保存到 MongoDB"""
        from ..services.mongo_service import MongoDB

        task_id = f"update_{datetime.now().timestamp()}"
        await MongoDB.insert_data_task({
            "task_id": task_id,
            "status": "pending",
            "start_date": None,
            "end_date": None,
            "stocks": stocks or [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })
        return task_id

    @staticmethod
    async def run_download(task_id: str):
        """执行下载任务（后台任务）"""
        from ..services.mongo_service import MongoDB

        try:
            # 更新状态为 running
            await MongoDB.update_data_task(task_id, {"status": "running"})

            # 从 MongoDB 获取任务详情
            task = await MongoDB.get_data_task(task_id)

            # 使用腾讯 API 下载数据
            stocks_to_download = task.get("stocks", [])
            if not stocks_to_download:
                # 获取所有启用的股票
                stocks_data = await MongoDB.get_stocks(enabled_only=True)
                stocks_to_download = [s["code"] for s in stocks_data]

            data_dict = await TencentDataService._download_from_tencent(
                stocks_to_download,
                task["start_date"],
                task["end_date"]
            )

            # 转换为 Qlib 格式
            await TencentDataService._convert_to_qlib_format(data_dict)

            # 更新状态为 completed
            await MongoDB.update_data_task(task_id, {
                "status": "completed",
                "updated_at": datetime.utcnow()
            })

        except Exception as e:
            logger.error(f"Download task failed: {e}")
            await MongoDB.update_data_task(task_id, {
                "status": "failed",
                "updated_at": datetime.utcnow(),
            })

    @staticmethod
    async def run_update(task_id: str):
        """执行更新任务（后台任务）"""
        from ..services.mongo_service import MongoDB

        try:
            # 更新状态为 running
            await MongoDB.update_data_task(task_id, {"status": "running"})

            # 从 MongoDB 获取任务详情
            task = await MongoDB.get_data_task(task_id)

            # 使用腾讯 API 下载数据
            stocks_to_download = task.get("stocks", [])

            data_dict = await TencentDataService._download_from_tencent(
                stocks_to_download,
                "2015-01-01",  # 从 2015-01-01 开始
                datetime.now().strftime("%Y-%m-%d")  # 增量下载到今天
            )

            # 转换为 Qlib 格式
            await TencentDataService._convert_to_qlib_format(data_dict)

            # 更新状态为 completed
            await MongoDB.update_data_task(task_id, {
                "status": "completed",
                "updated_at": datetime.utcnow(),
            })

        except Exception as e:
            logger.error(f"Update task failed: {e}")
            await MongoDB.update_data_task(task_id, {
                "status": "failed",
                "updated_at": datetime.utcnow(),
            })

    @staticmethod
    async def _download_from_tencent(stocks: List[str], start: str, end: str) -> dict:
        """从腾讯 API 下载数据"""
        data_dict = {}
        for code in stocks:
            try:
                # 构造请求参数
                param = f"{code},day,{start},{end},2000,qfq"
                url = f"{TencentDataService.BASE_URL}?param={param}"
                response = requests.get(url, timeout=TencentDataService.REQUEST_TIMEOUT)
                response.raise_for_status()
                data_dict[code] = response.json()
            except Exception as e:
                logger.error(f"Failed to download {code}: {e}")
        return data_dict

    @staticmethod
    async def _convert_to_qlib_format(data_dict: dict):
        """转换为 Qlib 格式并保存"""
        # 参考 scripts/dump_bin.py 的实现
        # 将数据保存到 Qlib 目录
        pass
```

#### Qlib 在线服务 (backend/services/qlib_service.py)
```python
import qlib
from qlib.config import MODE_CONF, C
from qlib.constant import REG_CN
from qlib.data import D

class QlibOnlineService:
    def __init__(self):
        # 使用在线模式配置
        C.update(MODE_CONF["server"])

        # 初始化 Qlib
        mongo_conf = {
            "task_url": "mongodb://localhost:27017/",
            "task_db_name": "quant_system_db",
        }

        qlib.init(
            provider_uri="~/.qlib/qlib_data/cn_data",
            region=REG_CN,
            mongo=mongo_conf,
        )

    async def get_latest_data_date(self):
        """获取最新数据日期"""
        try:
            # 获取所有股票
            instruments = D.instruments("all")[:10]

            # 获取所有股票的最新数据日期
            df = D.features(
                instruments,
                ["$close"],
                start_time="2020-01-01",
                end_time=datetime.now().strftime("%Y-%m-%d"),
                freq="day"
            )

            if df is not None and not df.empty:
                # 获取最新日期
                latest_date = df.index.get_level_values(1).max()
                return latest_date.strftime("%Y-%m-%d")
        except Exception as e:
            logger.error(f"Failed to get latest data date: {e}")
            return None
```

---

### 3. 预测模块

#### 后端实现 (backend/api/predict.py)
```python
from fastapi import APIRouter, BackgroundTasks
from datetime import datetime
from ..services.prediction_service import PredictionService
from ..services.mongo_service import MongoDB

router = APIRouter(prefix="/api/predict", tags=["Predict"])

@router.post("/")
async def predict(
    background_tasks: BackgroundTasks,
    predict_date: str = None,
    stocks: List[str] = None
):
    """执行预测（默认最新数据）"""
    if predict_date is None:
        predict_date = datetime.now().strftime("%Y-%m-%d")

    # 获取所有启用的股票
    stocks_data = await MongoDB.get_stocks(enabled_only=True)
    stocks = [s["code"] for s in stocks_data]

    # 创建预测任务
    task_id = await PredictionService.create_prediction_task(
        predict_date=predict_date,
        stocks=stocks
    )

    # 后台执行预测
    background_tasks.add_task(PredictionService.run_prediction, task_id)

    return {
        "task_id": task_id,
        "status": "started",
        "message": "Prediction task started"
    }

@router.post("/history")
async def predict_history(
    background_tasks: BackgroundTasks,
    start_date: str,
    end_date: str,
    stocks: List[str] = None
):
    """历史数据预测"""
    import pandas as pd
    from datetime import timedelta

    date_range = pd.date_range(start_date, end_date, freq="D")
    tasks = []

    for date in date_range:
        task_id = f"predict_{date.strftime('%Y%m%d')}"
        tasks.append({
            "task_id": task_id,
            "predict_date": date.strftime("%Y-%m-%d"),
            "stocks": stocks or [],
            "created_at": datetime.utcnow(),
        })
        background_tasks.add_task(PredictionService.run_prediction, task_id)

    return {
        "task_ids": [t["task_id"] for t in tasks],
        "status": "started",
        "message": f"Batch prediction started for {len(tasks)} dates"
    }

@router.get("/results")
async def get_predictions(
    date: str = None,
    code: str = None,
    sort_by: str = "score",
    sort_order: str = "desc",
    limit: int = 100,
    filter_type: str = "all"
):
    """
    查询预测结果

    Args:
        date: 预测日期
        code: 股票代码
        sort_by: 排序字段（date, code, name, score）
        sort_order: 排序方式（asc, desc）
        limit: 返回数量限制
        filter_type: 筛选类型
            - all: 显示全部
            - held: 仅显示持仓
            - not_held: 仅显示非持仓

    Returns:
        预测结果列表
    """
    query = {}
    if date:
        query["date"] = date
    if code:
        query["code"] = code

    # 持仓筛选
    if filter_type != "all":
        positions = await MongoDB.get_positions()
        position_codes = set(p["code"] for p in positions)

        if filter_type == "held":
            query["code"] = {"$in": list(position_codes)}
        elif filter_type == "not_held":
            query["code"] = {"$nin": list(position_codes)}

    # 排序
    sort_order = -1 if sort_order == "desc" else 1
    sort_field = {
        "date": "date",
        "code": "code",
        "name": "name",
        "score": "score",
    }.get(sort_by, "score")

    # 查询预测结果
    cursor = await MongoDB.get_predictions(
        query=query,
        sort=[(sort_field, sort_order)],
        limit=limit
    )

    predictions = await cursor.to_list(length=None)

    # 标记持仓状态
    if filter_type != "all":
        positions = await MongoDB.get_positions()
        position_codes = set(p["code"] for p in positions)

        for pred in predictions:
            pred["is_held"] = pred["code"] in position_codes

    return predictions

@router.get("/results/{date}")
async def get_predictions_by_date(date: str):
    """查询指定日期的预测结果"""
    return await MongoDB.get_predictions({"date": date})

@router.get("/status/{task_id}")
async def get_prediction_status(task_id: str):
    """查询预测任务状态"""
    task = await MongoDB.get_prediction_task(task_id)
    return task

@router.get("/status")
async def get_all_prediction_tasks():
    """查询所有预测任务"""
    return await MongoDB.get_all_prediction_tasks()
```

#### 预测服务 (backend/services/prediction_service.py)
```python
import pickle
import qlib
from qlib.config import MODE_CONF, C
from qlib.constant import REG_CN, REG_CN_CHILD
from qlib.contrib.data.handler import Alpha158
from multiprocessing import Pool, cpu_count
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from ..services.mongo_service import MongoDB
from ..services.qlib_service import QlibOnlineService
from loguru import logger

class PredictionService:
    def __init__(self):
        # 使用在线模式
        mongo_conf = {
            "task_url": "mongodb://localhost:27017/",
            "task_db_name": "quant_system_db",
        }

        C.update(MODE_CONF["server"])

        qlib.init(
            provider_uri="~/.qlib/qlib_data/cn_data",
            region=REG_CN,
            mongo=mongo_conf,
        )

    @staticmethod
    async def create_prediction_task(predict_date: str, stocks: List[str]) -> str:
        """创建预测任务"""
        from ..services.mongo_service import MongoDB

        task_id = f"predict_{predict_date.replace('-', '')}_{datetime.now().timestamp()}"
        await MongoDB.insert_prediction_task({
            "task_id": task_id,
            "status": "pending",
            "predict_date": predict_date,
            "stocks": stocks or [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })
        return task_id

    @staticmethod
    async def run_prediction(task_id: str):
        """执行预测任务（多进程）"""
        from ..services.mongo_service import MongoDB

        try:
            # 更新状态为 running
            await MongoDB.update_prediction_task(task_id, {"status": "running"})

            # 从 MongoDB 获取任务详情
            task = await MongoDB.get_prediction_task(task_id)

            # 加载模型
            model = await MongoDB.get_latest_model()
            if model is None:
                raise Exception("No trained model found")

            # 多进程预测
            results = await PredictionService._predict_mp(
                stocks=task.get("stocks", []),
                predict_date=task["predict_date"],
                model=model
            )

            # 保存预测结果
            for result in results:
                await MongoDB.insert_prediction({
                    "date": task["predict_date"],
                    "code": result["code"],
                    "score": result["score"],
                    "rank": result["rank"],
                    "is_held": False,  # 初始标记
                    "created_at": datetime.utcnow(),
                })

            # 更新状态为 completed
            await MongoDB.update_prediction_task(task_id, {
                "status": "completed",
                "updated_at": datetime.utcnow(),
            })

        except Exception as e:
            logger.error(f"Prediction task failed: {e}")
            await MongoDB.update_prediction_task(task_id, {
                "status": "failed",
                "updated_at": datetime.utcnow(),
            })

    @staticmethod
    async def _predict_mp(stocks: List[str], predict_date: str, model, num_processes: int = 4):
        """多进程预测"""
        from ..workers.predict_worker import predict_worker

        # 将股票列表分批
        batch_size = max(len(stocks) // num_processes + 1)
        batches = [
            stocks[i:i + batch_size]
            for i in range(0, len(stocks), batch_size)
        ]

        # 序列化模型
        model_pickle = pickle.dumps(model)

        # 准备参数
        args_list = [
            (batch, predict_date, model_pickle, "~/.qlib/qlib_data/cn_data")
            for batch in batches
        ]

        # 使用进程池
        with Pool(processes=num_processes) as pool:
            results_list = pool.map(predict_worker, args_list)

        # 合并结果
        all_results = []
        for results in results_list:
            all_results.extend(results)

        # 排序
        all_results.sort(key=lambda x: x["score"], reverse=True)

        # 添加排名
        for i, result in enumerate(all_results):
            result["rank"] = i + 1

        return all_results

    @staticmethod
    async def get_latest_model():
        """获取最新模型"""
        return await MongoDB.get_latest_model()
```

#### 多进程预测工作进程 (backend/workers/predict_worker.py)
```python
import pickle
import qlib
from qlib.config import MODE_CONF, C
from qlib.constant import REG_CN_CHILD
from qlib.contrib.data.handler import Alpha158
import pandas as pd

def predict_worker(args):
    """
    多进程预测工作函数

    注意：每个子进程必须独立初始化 Qlib
    """
    stock_batch, predict_date, model_pickle, provider_uri = args

    # 在子进程中重新初始化 Qlib
    C.update(MODE_CONF["client"])
    qlib.init(provider_uri=provider_uri, region=REG_CN_CHILD)

    # 反序列化模型
    model = pickle.loads(model_pickle)

    results = []
    for code in stock_batch:
        try:
            # 使用 Alpha158 获取特征
            dataset = Alpha158(
                instruments=[code],
                start_time="2015-01-01",
                end_time=predict_date,
                fit_start_time="2015-01-01",
                fit_end_time=predict_date,
            )

            # 准备数据
            df = dataset.prepare("test")

            # 预测
            if df is not None or df.empty:
                continue

            pred = model.predict(df)
            results.append({
                "code": code,
                "score": float(pred[0]) if len(pred) > 0 else 0.0,
                "rank": 0,
            })

        except Exception as e:
            print(f"Error predicting {code}: {e}")

    return results
```

---

### 4. 持仓管理模块（含交易操作）

#### 后端实现 (backend/api/position.py)
```python
from fastapi import APIRouter, UploadFile, File
from typing import List
from ..services.mongo_service import MongoDB
from ..services.trade_service import TradeService
from ..models import PositionCreate, PositionUpdate, PositionResponse
from datetime import datetime

router = APIRouter(prefix="/api/positions", tags=["Positions"])

@router.get("/", response_model=List[PositionResponse])
async def get_positions():
    """获取持仓列表"""
    return await MongoDB.get_positions()

@router.post("/", response_model=PositionResponse)
async def create_position(position: PositionCreate):
    """添加持仓"""
    existing = await MongoDB.get_position(position.code)
    if existing:
        raise HTTPException(status_code=400, detail="Position already exists")

    # 从数据库获取股票名称
    stock = await MongoDB.get_stock(position.code)
    if stock:
        position.name = stock["name"]

    position_dict = position.dict()
    position_dict["added_at"] = datetime.utcnow()
    position_dict["updated_at"] = datetime.utcnow()
    await MongoDB.insert_position(position_dict)
    return PositionResponse(**position_dict)

@router.put("/{code}")
async def update_position(code: str, position: PositionUpdate):
    """修改持仓（数量、成本价等）"""
    # 从数据库获取股票名称
    stock = await MongoDB.get_stock(code)
    if stock:
        position.name = stock["name"]

    position_dict = position.dict()
    position_dict["updated_at"] = datetime.utcnow()
    if position.name:
        position_dict["name"] = position.name

    success = await MongoDB.update_position(code, position_dict)
    if not success:
        raise HTTPException(status_code=404, detail="Position not found")
    return {"message": "Position updated successfully", "data": PositionResponse(**position_dict)}

@router.delete("/{code}")
async def delete_position(code: str):
    """删除持仓"""
    success = await MongoDB.delete_position(code)
    if not success:
        raise HTTPException(status_code=404, detail="Position not found")
    return {"message": "Position deleted successfully"}

@router.post("/import")
async def import_positions(file: UploadFile = File(...)):
    """导入持仓（CSV 格式）"""
    import pandas as pd
    from io import BytesIO

    content = await file.read()
    df = pd.read_csv(BytesIO(content))

    imported = 0
    for _, row in df.iterrows():
        try:
            position = PositionCreate(
                code=row["code"],
                quantity=row["quantity"],
                cost_price=row["cost_price"],
                name=row.get("name", "")
            )
            await MongoDB.insert_position(position.dict())
            imported += 1
        except Exception as e:
            logger.error(f"Failed to import position: {e}")

    return {"imported": imported, "total": len(df)}

@router.post("/batch")
async def batch_operations(operation: str, codes: List[str], update_data: dict = None):
    """
    批量操作（支持多选和连续多选）
    """
    if operation == "delete":
        result = await MongoDB.batch_delete_positions(codes)
    elif operation == "update" and update_data:
        result = await MongoDB.batch_update_positions(codes, update_data)
    else:
        raise HTTPException(status_code=400, detail="Invalid operation")
    return {"modified_count": result}

# ============================================================================
# 交易操作 API（基于持仓和预测结果）
# ============================================================================

@router.post("/positions/trade/buy")
async def trade_stocks_buy(stocks: List[str]):
    """
    买入操作：对选中的持仓代码执行买入
    """
    return await TradeService.trade_stocks_buy(stocks)

@router.post("/positions/trade/sell")
async def trade_stocks_sell(stocks: List[str]):
    """
    卖出操作：对选中的持仓代码执行卖出
    """
    return await TradeService.trade_stocks_sell(stocks)

@router.post("/positions/trade/sync")
async def sync_positions():
    """
    从交易代理同步持仓到本地数据库
    """
    return await TradeService.sync_positions()

@router.get("/positions/trade/top")
async def get_trade_candidates():
    """
    获取交易候选（根据预测得分排序）
    """
    return await TradeService.get_trade_candidates()
```

#### 交易服务 (backend/services/trade_service.py)
```python
from datetime import datetime
from ..services.mongo_service import MongoDB
from ..services.agent_service import AgentService
from ..services.qlib_service import QlibOnlineService
from loguru import logger

class TradeService:
    @staticmethod
    async def trade_stocks_buy(stocks: List[str]):
        """
        买入操作：对选中的持仓代码执行买入

        Args:
            stocks: 持仓代码列表（支持多选）

        Returns:
            交易结果
        """
        # 获取持仓信息
        positions = await MongoDB.get_positions()
        position_dict = {p["code"]: 1 for p in positions}

        # 提交买入订单到代理
        response = await AgentService.submit_orders("buy", [
            {
                "code": pos["code"],
                "quantity": pos["quantity"],
                "price": await TradeService._get_market_price(pos["code"]),
                "timestamp": datetime.now().isoformat()
            }
            for code in stocks
        ])

        # 保存交易记录
        return {
            "executed": len(stocks),
            "message": f"Successfully executed {len(stocks)} buy orders"
        }

    @staticmethod
    async def trade_stocks_sell(stocks: List[str]):
        """
        卖出操作：对选中的持仓代码执行卖出
        """
        # 获取持仓信息
        positions = await MongoDB.get_positions()

        # 提交卖出订单到代理
        response = await AgentService.submit_orders("sell", [
            {
                "code": pos["code"],
                "quantity": pos["quantity"],
                "price": await TradeService._get_market_price(pos["code"]),
                "timestamp": datetime.now().isoformat()
            }
            for code in stocks
        ])

        # 保存交易记录
        return {
            "executed": len(stocks),
            "message": f"Successfully executed {len(stocks)} sell orders"
        }

    @staticmethod
    async def sync_positions():
        """
        从交易代理同步持仓到本地数据库
        """
        # 获取代理持仓
        response = await AgentService.get_positions()

        if not response["success"]:
            raise HTTPException(status_code=500, detail="Failed to sync positions from agent")

        agent_positions = response["data"]["positions"]

        # 清空本地持仓
        await MongoDB.clear_all_local_positions()

        # 同步代理持仓到本地
        imported = 0
        for agent_pos in agent_positions:
            # 检查是否已存在
            existing = await MongoDB.get_position(agent_pos["code"])

            if existing:
                # 更新持仓信息
                await MongoDB.update_position(
                    agent_pos["code"],
                    {
                        "quantity": agent_pos["quantity"],
                        "cost_price": agent_pos["cost_price"],
                        "synced_at": datetime.utcnow(),
                    }
                )
            else:
                # 插入新持仓
                await MongoDB.insert_position({
                    "code": agent_pos["code"],
                    "name": agent_pos["name"],
                    "quantity": agent_pos["quantity"],
                    "cost_price": agent_pos["cost_price"],
                    "market_value": agent_pos["market_value"],
                    "pnl": agent_pos["pnl"],
                    "pnl_percent": agent_pos["pnl_percent"],
                    "synced_at": datetime.utcnow(),
                })
                imported += 1

        return {
            "imported": imported,
            "total": len(agent_positions),
        "message": "Successfully synced positions from agent"
        }

    @staticmethod
    async def get_trade_candidates(limit: int = 10, filter_held: bool = None):
        """
        获取交易候选（根据预测得分排序）

        Args:
            limit: 返回数量限制
            filter_held: 是否只包含持仓

        Returns:
            交易候选列表
        """
        # 获取所有预测结果
        query = {}
        query["date"] = datetime.now().strftime("%Y-%m-%d")

        # 获取所有持仓
        positions = await MongoDB.get_positions()
        position_codes = set(p["code"] for p in positions)

        # 筛选：只显示持仓
        if filter_held:
            query["code"] = {"$in": list(position_codes)}
        elif filter_held is False:
            query["code"] = {"$nin": list(position_codes)}

        # 查询预测结果
        cursor = await MongoDB.get_predictions(
            query=query,
            sort=[("score", -1)],
            limit=limit
        )

        predictions = await cursor.to_list(length=None)

        # 按是否是持仓标记
        for pred in predictions:
            pred["is_held"] = pred["code"] in position_codes

        # 添加持仓信息到预测结果
        for pred in predictions:
            pos = next((p for p in positions if p["code"] == pred["code"]), None)
            if pos:
                pred["position"] = {
                    "code": pos["code"],
                    "name": pos["name"],
                    "quantity": pos["quantity"],
                    "cost_price": pos["cost_price"],
                    "market_value": pos["market_value"],
                    "pnl": pos["pnl"],
                    "pnl_percent": pos["pnl_percent"],
                }

        # 排序（预测得分降序）
        predictions.sort(key=lambda x: x.get("score", 0), reverse=True)

        return predictions[:limit]

    @staticmethod
    async def _get_market_price(code: str):
        """
        获取当前市场价格（用于交易）
        """
        # 从 Qlib 获取最新价格
        df = D.features(
            [code],
            ["$close"],
            start_time=datetime.now().strftime("%Y-%m-%d"),
            end_time=datetime.now().strftime("%Y-%m-%d"),
            freq="day"
        )

        if df is not None or df.empty:
            return None

        return float(df["$close"].iloc[-1])
```

#### 持仓管理数据模型 (backend/models.py)
```python
# ============================================================================
# 交易代理管理模型
# ============================================================================

class AgentConfigCreate(BaseModel):
    agent_url: str = Field(..., description="代理 URL")
    agent_token: str = Field(..., description="代理 Token")
    agent_name: str = Field(default="Default Agent", description="代理名称")

class AgentConfigResponse(BaseModel):
    agent_url: str
    agent_token: str
    agent_name: str
    status: str = Field(default="active", description="状态")
    created_at: datetime
    updated_at: datetime

class AgentOrderSubmit(BaseModel):
    action: str = Field(..., description="操作类型（buy/sell/cancel）")
    stocks: List[dict] = Field(..., description="股票列表")
    timestamp: str = Field(default_factory=datetime.now().isoformat, description="时间戳")

class AgentOrder(BaseModel):
    order_id: str
    action: str
    code: str
    name: str
    price: float
    quantity: int
    status: str = Field(default="submitted", description="状态")

class AgentOrder(BaseModel):
    order_id: str
    action: str
    code: str
    name: str
    price: float
    quantity: int
    status: str = Field(default="submitted", description="状态")
    created_at: datetime
    updated_at: datetime

class AgentPosition(BaseModel):
    code: str
    name: str
    quantity: float
    cost_price: float
    market_value: float = Field(default=0.0, description="市值")
    pnl: float = Field(default=0.0, description="盈亏")
    pnl_percent: float = Field(default=0.0, description="盈亏百分比")
    synced_at: datetime

class AgentOrdersResponse(BaseModel):
    total: int
    orders: List[AgentOrder]

class PositionCreate(BaseModel):
    code: str = Field(..., description="股票代码")
    quantity: float = Field(..., description="持仓数量")
    cost_price: float = Field(..., description="成本价")
    name: Optional[str] = Field(default="", description="股票名称")

class PositionUpdate(BaseModel):
    quantity: Optional[float] = None
    cost_price: Optional[float] = None

class PositionResponse(PositionCreate):
    added_at: datetime
    updated_at: datetime

# ============================================================================
# 持仓管理模型（扩展，包含交易操作）
# ============================================================================

class TradeStocksRequest(BaseModel):
    stocks: List[str] = Field(..., description="持仓代码列表（支持多选）")

class TradeResponse(BaseModel):
    executed: int
    message: str
```

class TradeCandidatesItem(BaseModel):
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    score: float = Field(..., description="预测得分")
    rank: int = Field(..., description="排名")
    is_held: bool = Field(default=False, description="是否持仓")
    position: Optional[dict] = None  # 持仓信息（如果有）
```

class TradeCandidates(BaseModel):
    items: List[TradeCandidatesItem]
```

#### 前端界面 (PositionManager.vue)
- 持仓列表表格
- 交易操作区：
  - 买入按钮：对选中的持仓代码执行买入操作
  - 卖出按钮：对选中的持仓代码执行卖出操作
  - 同步按钮：从交易代理同步持仓
- 持仓筛选：仅显示持仓/仅显示非持仓
- 持仓管理操作：
  - 添加/删除/修改按钮
  - 导入/导出按钮
  - 批量删除
  - 批量更新（更新数量、成本价等）
- 交易候选列表：显示根据预测得分排序的交易候选（含持仓信息）
- 表格排序：按预测得分、代码、数量、市值等
- 状态提示：
  - 代理状态（主用代理可用/不可用）
  - 交易状态（可执行/不可执行）

---

### 5. 交易代理管理模块

#### 后端实现 (backend/api/agent.py)
```python
from fastapi import APIRouter
from ..services.agent_service import AgentService
from ..models import (
    AgentConfigCreate, AgentConfigResponse,
    AgentOrderSubmit, AgentOrder, AgentOrder,
    AgentPosition, AgentOrdersResponse, TradeCandidates, TradeCandidates
)

router = APIRouter(prefix="/api/agent", tags=["Agent"])

@router.post("/config")
async def get_agent_config():
    """获取交易代理配置"""
    return await AgentService.get_agent_config()

@router.post("/config")
async def update_agent_config(agent_url: str, agent_token: str, agent_name: str):
    """更新代理配置"""
    return await AgentService.update_agent_config(agent_url, agent_token, agent_name)

@router.post("/orders")
async def submit_agent_orders(action: str, stocks: List[dict]):
    """提交交易订单到代理"""
    return await AgentService.submit_orders(action, stocks)

@router.get("/orders")
async def get_agent_orders(order_id: str = None, limit: int = 100):
    """查询代理订单状态"""
    return await AgentService.get_agent_orders(order_id, limit)

@router.get("/positions")
async def get_agent_positions():
    """查询代理持仓状态"""
    return await AgentService.get_agent_positions()
```

#### 交易代理服务 (backend/services/agent_service.py)
```python
import httpx
from typing import Dict, List
from datetime import datetime
from ..services.mongo_service import MongoDB
from loguru import logger

class AgentService:
    """交易代理管理服务"""

    @staticmethod
    async def get_agent_config():
        """获取代理配置"""
        config = await MongoDB.get_agent_config()
        return config

    @staticmethod
    async def update_agent_config(agent_url: str, agent_token: str, agent_name: str):
        """更新代理配置"""
        await MongoDB.update_agent_config({
            "agent_url": agent_url,
            "agent_token": agent_token,
            "agent_name": agent_name,
            "updated_at": datetime.utcnow()
        })

    @staticmethod
    async def submit_orders(action: str, stocks: List[dict]):
        """提交交易订单到代理"""
        config = await AgentService.get_agent_config()

        payload = {
            "action": action,
            "stocks": stocks,
            "timestamp": datetime.now().isoformat()
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config['agent_url']}/api/agent/trade",
                json=payload,
                headers={
                    "Authorization": f"Bearer {config['agent_token']}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def get_agent_orders(order_id: str = None, limit: int = 100):
        """查询代理订单状态"""
        config = await AgentService.get_agent_config()

        params = {}
        if order_id:
            params["order_id"] = order_id
        if limit:
            params["limit"] = limit

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{config['agent_url']}/api/agent/orders",
                params=params,
                headers={
                    "Authorization": f"Bearer {config['agent_token']}",
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def get_agent_positions():
        """查询代理持仓状态"""
        config = await AgentService.get_agent_config()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{config['agent_url']}/api/agent/positions",
                headers={
                    "Authorization": f"Bearer {config['agent']}",
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
```

#### 交易代理客户端 (backend/services/agent_client.py)
```python
import httpx
from typing import List, Dict

class AgentClient:
    """交易代理 HTTP 客户端"""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token

    async def submit_orders(self, action: str, stocks: List[dict]) -> dict:
        """提交交易订单"""
        payload = {
            "action": action,
            "stocks": stocks,
            "timestamp": datetime.now().isoformat()
        }

        async with httpx.AsyncClient() as client:
            response = await self.post("/api/agent/trade", json=payload)
            return response.json()

    async def get_orders(self, order_id: str = None, limit: int = 100) -> dict:
        """查询订单状态"""
        params = {}
        if order_id:
            params["order_id"] = order_id
        if limit:
            params["limit"] = limit

        async with httpx.AsyncClient() as client:
            response = await self.get("/api/agent/orders", params=params)
            return response.json()

    async def get_positions(self) -> dict:
        """查询持仓状态"""
        async with httpx.AsyncClient() as client:
            response = await self.get("/api/agent/positions")
            return response.json()
```

#### MongoDB 操作扩展 (backend/services/mongo_service.py)
```python
# 在后添加以下方法：

@classmethod
async def get_agent_config(cls):
    """获取代理配置"""
    config = await cls.database.agent_config.find_one({})
    if config is None:
        # 创建默认配置
        config = {
            "agent_url": "",
            "agent_token": "",
            "agent_name": "Default Agent",
            "status": "inactive",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        await cls.database.agent_config.insert_one(config)

    return config

@classmethod
async def update_agent_config(cls, agent_url: str, agent_token: str, agent_name: str):
    """更新代理配置"""
    result = await cls.database.agent_config.update_one(
        {},
        {"$set": {
            "agent_url": agent_url,
            "agent_token": agent_token,
            "agent_name": agent_name,
            "updated_at": datetime.utcnow()
        }}
    )
    return result.modified_count > 0

@classmethod
async def clear_all_local_positions(cls):
    """清空所有本地持仓"""
    result = await cls.database.local_positions.delete_many({})
    logger.info(f"Cleared all local positions: {result.deleted_count} records")
    return result.deleted_count

@classmethod
async def batch_delete_positions(cls, codes: List[str]):
    """批量删除持仓"""
    result = await cls.database.local_positions.delete_many({"code": {"$in": codes}})
    logger.info(f"Batch deleted {result.deleted_count} positions")
    return result.deleted_count

@classmethod
async def batch_update_positions(cls, codes: List[str], update_data: dict):
    """批量更新持仓"""
    result = await cls.database.local_positions.update_many(
        {"code": {"$in": codes}},
        {"$set": update_data}
    )
    logger.info(f"Batch updated {result.modified_count} positions")
    return result.modified_count
```

# 在后端添加以下 Collections:
# - agent_config: 代理配置
# - agent_positions: 代理持仓
# - local_positions: 本地持仓
# - agent_logs: 代理请求日志
# - local_predictions: 本地预测结果（用于生成交易信号）
```

---

### 6. 交易管理模块（基于预测结果）

#### 后端实现 (backend/api/trade.py)
```python
from fastapi import APIRouter
from ..services.trade_service import TradeService
from ..models import TradeStocksRequest, TradeResponse, TradeCandidates

router = APIRouter(prefix="/api/trade", tags=["Trade"])

@router.post("/stocks")
async def trade_stocks(request: TradeStocksRequest):
    """
    交易操作：买入或卖出指定的持仓代码
    """
    return await TradeService.trade_stocks(request.stocks)

@router.get("/candidates")
async def get_trade_candidates(limit: int = 10, filter_held: bool = None):
    """
    获取交易候选（根据预测得分排序）

    Args:
        limit: 返回数量限制
        filter_held: 是否只包含持仓

    Returns:
            交易候选列表（按预测得分降序，包含持仓信息）
        """
    return await TradeService.get_trade_candidates(limit=limit, filter_held=filter_held)
```

#### 交易服务 (backend/services/trade_service.py)
```python
from datetime import datetime
from ..services.mongo_service import MongoDB
from ..services.agent_service import AgentService
from ..services.qlib_service import QlibOnlineService
from loguru import logger

class TradeService:
    """交易管理服务"""

    @staticmethod
    async def trade_stocks(stocks: List[str]):
        """
        买入操作：对选中的持仓代码执行买入

        Args:
            stocks: 持仓代码列表（支持多选）

        Returns:
            交易执行结果
        """
        # 获取持仓信息
        positions = await MongoDB.get_positions()
        position_dict = {p["code"]: 1 for p in positions}

        # 提交买入订单到代理
        response = await AgentService.submit_orders("buy", [
            {
                "code": pos["code"],
                "quantity": pos["quantity"],
                "price": await TradeService._get_market_price(pos["code"]),
                "timestamp": datetime.now().isoformat()
            }
            for code in stocks
        ])

        # 保存交易记录
        return {
            "executed": len(stocks),
            "message": f"Successfully executed {len(stocks)} buy orders"
        }

    @staticmethod
    async def trade_stocks_sell(stocks: List[str]):
        """
        卖出操作：对选中的持仓代码执行卖出
        """
        # 获取持仓信息
        positions = await MongoDB.get_positions()
        position_dict = {p["code"]: 1 for p in positions}

        # 提交卖出订单到代理
        response = await AgentService.submit_orders("sell", [
            {
                "code": pos["code"],
                "quantity": pos["quantity"],
                "price": await TradeService._get_market_price(pos["code"]),
                "timestamp": datetime.now().isoformat()
            }
            for code in stocks
        ])

        # 保存交易记录
        return {
            "executed": len(stocks),
            "message": f"Successfully executed {len(stocks)} sell orders"
        }

    @staticmethod
    async def sync_positions():
        """
        从交易代理同步持仓到本地数据库
        """
        return await TradeService.sync_positions()

    @staticmethod
    async def get_trade_candidates(limit: int = 10, filter_held: bool = None):
        """
        获取交易候选（根据预测得分排序）

        Args:
            limit: 返回数量限制
            filter_held: 是否只包含持仓

        Returns:
            交易候选列表（按预测得分降序，包含持仓信息）
        """
        return await TradeService.get_trade_candidates(limit=limit, filter_held=filter_held)

    @staticmethod
    async def _get_market_price(code: str):
        """
        获取当前市场价格（用于交易）
        """
        # 从 Qlib 获取最新价格
        df = D.features(
            [code],
            ["$close"],
            start_time=datetime.now().strftime("%Y-%m-%d"),
            end_time=datetime.now().strftime("%Y-%m-%d"),
            freq="day"
        )

        if df is not None or df.empty:
            return None

        return float(df["$close"].iloc[-1])
```

#### 交易管理前端 (frontend/src/components/TradeManager.vue)
- 交易候选列表：显示根据预测得分排序的买入/卖出候选
- 表格内容：
  - 股票代码、名称
  - 预测得分、排名
  - 持仓信息：持有数量、成本价、市值、盈亏、盈亏百分比
  - 持仓标记（是否在持仓中）
  - 排序功能：按预测得分、市值、盈亏
- 筛选功能：
  - 全部/持仓
  - 仅显示持仓
  - 仅显示非持仓
- 交易操作：
  - 买入按钮：执行买入
  - 卖出按钮：执行卖出
  - 同步按钮：从交易代理同步持仓

---

### 7. 日志管理模块

#### 后端实现 (backend/api/log.py)
```python
from fastapi import APIRouter
from pathlib import Path
import zipfile
from datetime import datetime

router = APIRouter(prefix="/api/logs", tags=["Logs"])

LOG_DIR = Path("log")

@router.get("/")
async def list_logs():
    """列出所有日志文件"""
    if not LOG_DIR.exists():
        return []

    log_files = []
    for file in LOG_DIR.glob("*.log"):
        stat = file.stat()
        log_files.append({
            "filename": file.name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime),
        })

    # 按修改时间倒序排列
    log_files.sort(key=lambda x: x["modified"], reverse=True)
    return log_files

@router.get("/download/{filename}")
async def download_log(filename: str):
    """下载单个日志文件"""
    log_path = LOG_DIR / filename
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Log file not found")

    return FileResponse(
        path=log_path,
        filename=filename
    )

@router.post("/download/batch")
async def download_logs_batch(filenames: List[str]):
    """批量下载日志（打包为 ZIP）"""
    from fastapi.responses import StreamingResponse
    import zipfile
    from io import BytesIO

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for filename in filenames:
            log_path = LOG_DIR / filename
            if log_path.exists():
                zipf.write(log_path, arcname=filename)

    zip_buffer.seek(0)

    zip_filename = f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}{}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
    )
```

#### 前端日志管理界面 (frontend/src/components/LogManager.vue)
- 日志文件列表
- 下载单个日志按钮
- 批量下载（打包 ZIP）按钮
- 文件大小和修改时间显示

---

## 实现步骤

1. **Week 1**: 项目初始化 + MongoDB 配置 + Qlib 在线模式
2. **Week 2**: 代码管理 + 数据管理（腾讯 API 集成）
3. **Week 3**: 预测功能 + 多进程优化 + 持仓筛选 + 交易代理集成
4. **Week 4**: 持仓管理功能（导入导出、添加删除修改 + 交易操作 + 多选）
5. **Week 5**: 交易管理（基于预测结果的买入/卖出）+ 日志管理
6. **Week 6**: 集成测试和优化

## 关键特性

- **代码管理**: 默认空列表 + A500.csv 重新初始化 + 批量操作 + 多选
- **数据管理**: 腾讯 API + Qlib 在线模式 + 增量下载
- **预测功能**: Alpha158 + 多进程 + 排序 + 持仓筛选
- **持仓管理**: CRUD + 导入导出 + 多选 + 买入/卖出/同步
- **交易代理管理**: 配置 + 订单管理 + 持仓查询
- **交易管理**: 基于预测结果的买入/卖出 + 候选候选列表
- **日志管理**: 文件列表 + 单个/批量下载

## 参考文件

- `/Users/samlty/code/qlib/examples/TencentDataSource/tencent_data_source.py`
- `/Users/samlty/code/qlib/examples/TencentDataSource/predict_stocks.py`
- `/Users/samlty/code/qlib/examples/online_srv/online_management_simulate.py`（在线模式）
- `/Users/samlty/code/qlib/examples/model_rolling/task_manager_rolling.py`（MongoDB + TaskManager）
- `/Users/samlty/code/qlib/qlib/contrib/data/handler.py`（Alpha158）
- `/Users/samlty/code/qlib/qlib/config.py`（MODE_CONF）
- `/Users/samlty/code/qlib/examples/official/trade_agent.md`（交易代理接口文档）

## 注意事项

1. **MongoDB 配置**: 需要安装 MongoDB 服务（localhost:27017）
2. **A500.csv 格式**: 需要确认 CSV 文件的列名（如：成份券代码、成分券名称等）
3. **股票代码格式**: Qlib 使用 `sh600000`, `sz000001` 格式
4. **多进程限制**: 每个子进程需要独立初始化 Qlib，不能共享对象
5. **Qlib 在线模式**: 配置 Redis 作为缓存层，提高性能
6. **MongoDB 异步操作**: 使用 Motor 库进行异步 MongoDB 操作
7. **线程安全**: Qlib 对象不是线程安全的，多线程需要谨慎使用
8. **前端开发模式**: Vite 运行在 5173 端口，需要配置代理
9. **日志文件权限**: 确保 log 目录有写权限
10. **数据备份**: 定期备份 MongoDB 数据和 Qlib 数据
11. **代理状态检查**: 在执行交易前检查代理是否可用
12. **持仓同步**: 每次同步操作会清空并重新导入

计划包含详细的代码示例、API 设计、MongoDB 异步操作、交易代理集成、多进程实现方式、以及完整的文件列表。