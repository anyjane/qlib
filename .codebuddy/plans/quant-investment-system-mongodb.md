# 量化投资管理系统实现计划

## 项目概述
在 `examples/official` 目录下创建一个基于 FastAPI 的量化投资管理系统，使用 MongoDB 存储数据，并利用 Qlib 在线模式进行数据管理。

## 核心功能模块

1. **代码管理** - 默认为空，支持从 A500.csv 重新初始化代码列表，支持增删改和批量操作
2. **数据管理** - 腾讯 API 下载日线数据，使用 Qlib 在线模式，支持初始下载和增量更新
3. **预测功能** - 使用 Alpha158 因子 + 多进程加速，支持历史查询、排序和持仓筛选
4. **持仓管理** - 导入导出持仓，管理持仓的添加/删除/修改
5. **日志管理** - 后端日志输出和前端打包下载

## 技术栈

### 后端
- **框架**: FastAPI (Python 3.8+)
- **端口**: 8000
- **数据库**: MongoDB (替代 SQLite)
- **Qlib 模式**: 在线模式 (Online Mode)
- **多进程**: Python multiprocessing
- **数据处理**: Qlib + Alpha158
- **日志**: loguru
- **API数据源**: 腾讯财经 API
- **任务管理**: Qlib TaskManager + MongoDB

### 前端
- **框架**: Vue.js 3 + Element Plus
- **构建**: Vite
- **调试**: 支持前后端联调模式

### 数据存储
- **MongoDB**: 存储股票列表、持仓、预测结果
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
│   │   ├── position.py     # 持仓管理 API
│   │   ├── agent.py        # 交易代理管理 API
│   │   └── log.py        # 日志下载 API
│   ├── services/
│   │   ├── __init__.py
│   │   ├── data_service.py        # 腾讯数据下载服务
│   │   ├── prediction_service.py   # 多进程预测服务
│   │   ├── qlib_service.py      # Qlib 在线模式封装
│   │   └── mongo_service.py      # MongoDB 操作服务
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
│   │   │   └── PositionManager.vue   # 持仓管理
│   │   ├── api/
│   │   │   ├── stock.js
│   │   │   ├── data.js
│   │   │   ├── predict.js
│   │   │   └── position.js
│   │   └── utils/
│   │       └── request.js    # Axios 封装
│   ├── package.json
│   └── vite.config.js
├── A500.csv               # 默认股票列表（中证500成分股）
├── README.md
└── config.yaml            # 系统配置文件
```

---

## Qlib 在线模式配置

### 配置说明
Qlib 支持两种模式：

#### Offline Mode（离线模式）
- 数据本地部署
- 每个客户端独立管理数据
- 默认模式

#### Online Mode（在线模式）
- 数据作为共享服务部署
- 所有客户端共享数据和缓存
- 提高数据检索性能（缓存命中率更高）
- 减少磁盘空间占用
- 需要 Redis 作为缓存层
- 需要独立的数据服务器进程

### 在线模式配置

```python
# backend/config.py
from qlib.config import MODE_CONF

# Qlib 在线模式初始化
mongo_conf = {
    "task_url": "mongodb://localhost:27017/",
    "task_db_name": "quant_system_db",
}

qlib.init(
    provider_uri="~/.qlib/qlib_data/cn_data",
    region=REG_CN,
    mongo=mongo_conf,
)

# 切换到在线模式
from qlib.config import C
C.update(MODE_CONF["server"])  # 使用 server 配置
```

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
    "created_at": datetime,
}

# 4. data_tasks - 数据下载任务（Qlib TaskManager）
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

### MongoDB 操作封装

```python
# backend/database.py
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from typing import List, Optional

class MongoDB:
    client: AsyncIOMotorClient = None
    database = None

    @classmethod
    async def connect_to_database(cls, uri: str, db_name: str):
        cls.client = AsyncIOMotorClient(uri)
        cls.database = cls.client[db_name]
        return cls.database

    @classmethod
    async def close_database(cls):
        cls.client.close()

    @classmethod
    async def get_stock(cls, code: str):
        return await cls.database.stocks.find_one({"code": code})

    @classmethod
    async def get_stocks(cls, enabled_only: bool = False):
        query = {}
        if enabled_only:
            query["enabled"] = True
        cursor = cls.database.stocks.find(query)
        return await cursor.to_list(length=None)

    @classmethod
    async def clear_all_stocks(cls):
        """清空所有股票列表（用于重新初始化）"""
        result = await cls.database.stocks.delete_many({})
        logger.info(f"Cleared all stocks: {result.deleted_count} records")
        return result.deleted_count

    @classmethod
    async def insert_stock(cls, stock: dict):
        result = await cls.database.stocks.insert_one(stock)
        return str(result.inserted_id)

    @classmethod
    async def update_stock(cls, code: str, update: dict):
        result = await cls.database.stocks.update_one(
            {"code": code},
            {"$set": update}
        )
        return result.modified_count > 0

    @classmethod
    async def delete_stock(cls, code: str):
        result = await cls.database.stocks.delete_one({"code": code})
        return result.deleted_count > 0
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
        from ..services.data_service import standardize_stock_codes
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
            "imported": imported
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
- 批量操作（对选中的股票进行操作）
  - 批量启用：将选中的股票全部启用
  - 批量禁用：将选中的股票全部禁用
  - 批量删除：删除选中的所有股票
- 搜索和筛选功能

---

### 2. 数据管理模块（Qlib 在线模式）

#### 后端实现 (backend/api/data.py)
```python
from fastapi import APIRouter, BackgroundTasks
from datetime import datetime
from ..services.data_service import TencentDataService
from ..services.qlib_service import QlibOnlineService

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
    from ..services.mongo_service import MongoDB
    task = await MongoDB.get_data_task(task_id)
    return task
```

#### Qlib 在线服务 (backend/services/qlib_service.py)
```python
import qlib
from qlib.config import MODE_CONF, C
from qlib.data import D
from qlib.constant import REG_CN
from motor.motor_asyncio import AsyncIOMotorClient

class QlibOnlineService:
    def __init__(self):
        # 使用在线模式配置
        mongo_conf = {
            "task_url": "mongodb://localhost:27017/",
            "task_db_name": "quant_system_db",
        }

        # 切换到 server 模式（在线模式）
        C.update(MODE_CONF["server"])

        # 初始化 Qlib 在线模式
        qlib.init(
            provider_uri="~/.qlib/qlib_data/cn_data",
            region=REG_CN,
            mongo=mongo_conf,
        )

    async def get_latest_data_date(self):
        """获取最新数据日期"""
        instruments = D.instruments("all")
        # 获取所有股票的最新数据日期
        df = D.features(
            instruments[:10],  # 采样查询
            ["$close"],
            start_time="2020-01-01",
            end_time=datetime.now().strftime("%Y-%m-%d"),
            freq="day"
        )
        if df is not None and not df.empty:
            return df.index.get_level_values(1).max()
        return None

    async def get_stock_data(self, code: str, start: str, end: str):
        """获取股票数据"""
        df = D.features(
            [code],
            ["$open", "$high", "$low", "$close", "$volume"],
            start_time=start,
            end_time=end,
            freq="day"
        )
        return df
```

#### 数据下载服务 (backend/services/data_service.py)
```python
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from pathlib import Path
import requests
import pandas as pd
from loguru import logger

class TencentDataService:
    BASE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"

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
        })
        return task_id

    @staticmethod
    async def run_download(task_id: str):
        """执行下载任务（后台任务）"""
        from ..services.mongo_service import MongoDB

        # 更新状态为 running
        await MongoDB.update_data_task(task_id, {"status": "running"})

        try:
            # 从 MongoDB 获取任务详情
            task = await MongoDB.get_data_task(task_id)

            # 使用腾讯 API 下载数据
            stocks_to_download = task.get("stocks", [])
            if not stocks_to_download:
                # 从 stocks 集合获取所有启用的股票
                stocks_to_download = await MongoDB.get_stocks(enabled_only=True)
                stocks_to_download = [s["code"] for s in stocks_to_download]

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
                "updated_at": datetime.utcnow()
            })

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
    async def _download_from_tencent(stocks: List[str], start: str, end: str) -> dict:
        """从腾讯 API 下载数据"""
        data_dict = {}
        for code in stocks:
            try:
                # 构造请求参数
                param = f"{code},day,{start},{end},2000,qfq"
                url = f"{TencentDataService.BASE_URL}?param={param}"
                response = requests.get(url, timeout=30)
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

#### 前端界面 (DataManager.vue)
- 显示最新数据日期（从 Qlib 在线服务查询）
- 下载按钮（全量下载，从 2015-01-01 开始）
- 更新按钮（增量下载）
- 下载进度条（从 MongoDB 查询任务状态）
- 下载状态显示
- 批量操作（选择股票下载）

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
    if stocks is None:
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
    # 获取日期范围
    date_range = pd.date_range(start_date, end_date, freq="D")
    tasks = []

    for date in date_range:
        task_id = await PredictionService.create_prediction_task(
            predict_date=date.strftime("%Y-%m-%d"),
            stocks=stocks
        )
        tasks.append(task_id)
        background_tasks.add_task(PredictionService.run_prediction, task_id)

    return {
        "task_ids": tasks,
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
    filter_type: str = "all"  # all, held, not_held
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

    cursor = await MongoDB.get_predictions(
        query=query,
        sort=[(sort_field, sort_order)],
        limit=limit
    )

    predictions = await cursor.to_list(length=None)

    # 标记持仓状态（用于前端显示）
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
```

#### 预测服务 (backend/services/prediction_service.py)
```python
import pickle
import qlib
from qlib.config import MODE_CONF, C
from qlib.constant import REG_CN
from qlib.contrib.data.handler import Alpha158
from multiprocessing import Pool, cpu_count
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

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
        task_id = f"predict_{predict_date}_{datetime.now().timestamp()}"
        await MongoDB.insert_prediction_task({
            "task_id": task_id,
            "status": "pending",
            "predict_date": predict_date,
            "stocks": stocks or [],
            "created_at": datetime.utcnow(),
        })
        return task_id

    @staticmethod
    async def run_prediction(task_id: str):
        """执行预测任务（多进程）"""
        from ..services.mongo_service import MongoDB

        # 更新状态
        await MongoDB.update_prediction_task(task_id, {"status": "running"})

        try:
            task = await MongoDB.get_prediction_task(task_id)
            stocks = task.get("stocks", [])
            predict_date = task["predict_date"]

            if not stocks:
                # 获取所有启用的股票
                stocks_data = await MongoDB.get_stocks(enabled_only=True)
                stocks = [s["code"] for s in stocks_data]

            # 加载模型
            model = await MongoDB.load_latest_model()
            if model is None:
                raise Exception("No trained model found")

            # 多进程预测
            results = await PredictionService._predict_mp(
                stocks, predict_date, model
            )

            # 保存结果到 MongoDB
            for result in results:
                await MongoDB.insert_prediction({
                    "date": predict_date,
                    "code": result["code"],
                    "name": result["name"],
                    "score": result["score"],
                    "rank": result["rank"],
                    "created_at": datetime.utcnow(),
                })

            # 更新状态
            await MongoDB.update_prediction_task(task_id, {
                "status": "completed",
                "updated_at": datetime.utcnow()
            })

        except Exception as e:
            logger.error(f"Prediction task failed: {e}")
            await MongoDB.update_prediction_task(task_id, {
                "status": "failed",
                "updated_at": datetime.utcnow()
            })

    @staticmethod
    async def _predict_mp(stocks: List[str], predict_date: str, model, num_processes: int = 4):
        """多进程预测"""
        from ..workers.predict_worker import predict_worker

        # 将股票列表分批
        batch_size = len(stocks) // num_processes + 1
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
```

#### 预测工作进程 (backend/workers/predict_worker.py)
```python
import pickle
import qlib
from qlib.config import MODE_CONF, C
from qlib.constant import REG_CN, REG_CN_CHILD
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

    # 批量预测
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

            if df is not None and not df.empty:
                # 预测
                pred = model.predict(df)

                results.append({
                    "code": code,
                    "name": code,  # 可以从数据库获取名称
                    "score": float(pred[0]) if len(pred) > 0 else 0.0,
                    "rank": 0,
                })
        except Exception as e:
            print(f"Error predicting {code}: {e}")

    return results
```

#### 前端界面 (PredictResult.vue)
- 日期选择器（默认今天）
- 预测按钮
- 结果表格（日期、代码、名称、预测得分、排名、持仓标记）
- 排序功能（按日期、代码、名称、得分）
- 搜索和筛选：
  - 按股票代码搜索
  - 按日期范围筛选
  - 持仓筛选：显示全部/仅持仓/仅非持仓
- 历史查询功能（批量历史预测）

---

### 4. 持仓管理模块

#### 后端实现 (backend/api/position.py)
```python
from fastapi import APIRouter, UploadFile, File
from typing import List
from ..services.mongo_service import MongoDB
from ..models import PositionCreate, PositionResponse

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

    Args:
        operation: 操作类型（delete/update）
        codes: 选中的持仓代码列表（支持多选）
        update_data: 更新数据（可选，用于批量更新持仓）
            - quantity: 持仓数量
            - cost_price: 成本价

    Returns:
        操作结果统计
    """
    if operation == "delete":
        result = await MongoDB.batch_delete_positions(codes)
    elif operation == "update" and update_data:
        result = await MongoDB.batch_update_positions(codes, update_data)
    else:
        raise HTTPException(status_code=400, detail="Invalid operation")
    return {"modified_count": result}

@router.get("/export")
async def export_positions():
    """导出持仓（CSV 格式）"""
    from fastapi.responses import StreamingResponse
    import pandas as pd
    from io import StringIO

    positions = await MongoDB.get_positions()
    df = pd.DataFrame(positions)

    output = StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=positions.csv"}
    )

@router.post("/batch")
async def batch_operations(operation: str, codes: List[str]):
    """
    批量操作（支持多选和连续多选）

    Args:
        operation: 操作类型（enable/disable/delete/update）
        codes: 选中的持仓代码列表（支持多选）
        update_data: 更新数据（可选，用于批量更新持仓）

    Returns:
        操作结果统计
    """
    if operation == "delete":
        result = await MongoDB.batch_delete_positions(codes)
    elif operation == "update" and update_data:
        result = await MongoDB.batch_update_positions(codes, update_data)
    else:
        raise HTTPException(status_code=400, detail="Invalid operation")
    return {"modified_count": result}
```

#### 前端界面 (PositionManager.vue)
- 持仓列表表格
- 表格功能：
  - 复选框：支持单个选择
  - 全选/取消全选：支持全选和反选
  - 连选：Shift + 点击支持连续多选
- 持仓操作：
  - 添加/删除/修改按钮
  - 导入/导出按钮（CSV 格式）
  - 批量删除：删除选中的所有持仓
  - 批量更新：批量更新选中的持仓（数量、成本价等）
- 搜索和筛选功能

---

### 5. 日志管理模块

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

    from fastapi.responses import FileResponse
    return FileResponse(
        path=log_path,
        filename=filename,
        media_type="text/plain"
    )

@router.post("/download/batch")
async def download_logs_batch(filenames: List[str]):
    """批量下载日志（打包为 ZIP）"""
    from fastapi.responses import StreamingResponse
    from io import BytesIO

    # 创建 ZIP 文件
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for filename in filenames:
            log_path = LOG_DIR / filename
            if log_path.exists():
                zipf.write(log_path, filename)

    zip_buffer.seek(0)

    zip_filename = f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
    )
```

#### 后端日志配置 (backend/config.py)
```python
from loguru import logger
from pathlib import Path

LOG_DIR = Path("log")
LOG_DIR.mkdir(exist_ok=True)

# 移除默认处理器
logger.remove()

# 添加控制台处理器
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True,
)

# 添加文件处理器
logger.add(
    LOG_DIR / "app_{time:YYYYMMDD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="100 MB",
    retention="30 days",
    compression="zip",
    encoding="utf-8",
)

logger.info("Logging initialized")
```

#### 前端日志界面（集成在 PositionManager.vue 或单独页面）
- 日志文件列表
- 下载单个日志按钮
- 批量下载（打包 ZIP）按钮
- 文件大小和修改时间显示

---

## 实现步骤

### 第一步：项目初始化
1. 创建目录结构 `examples/official/`
2. 初始化后端项目
   - 创建 `backend/main.py` FastAPI 应用
   - 配置 CORS 支持前后端联调
   - 配置 MongoDB 连接
   - 配置 Qlib 在线模式
   - 配置日志输出到 `log/` 目录
3. 初始化前端项目
   - 使用 Vite 创建 Vue 3 项目
   - 配置 Element Plus UI 框架
   - 配置代理到 `http://localhost:8000`
4. 启动 MongoDB 服务

### 第二步：MongoDB 和 Qlib 在线模式配置
1. 创建 `backend/database.py`
   - Motor (Async MongoDB) 集成
   - 定义 MongoDB 操作方法
2. 创建 `backend/services/mongo_service.py`
   - 封装 MongoDB 异步操作
   - 定义 Collection 结构
3. 创建 `backend/services/qlib_service.py`
   - Qlib 在线模式初始化
   - 配置 MODE_CONF["server"]
   - 数据查询封装
4. 初始化 MongoDB Collections

### 第三步：代码管理功能
1. 实现 `backend/api/stock.py`
2. 实现 `backend/models.py` (Pydantic 模型)
3. 实现 `frontend/src/components/StockManager.vue`
4. 集成 A500.csv 导入功能
5. 测试增删改查和批量操作

### 第四步：数据管理功能（Qlib 在线模式）
1. 实现 `backend/services/data_service.py`
   - 腾讯 API 集成
   - Qlib 数据转换
   - 支持初始下载和增量下载
2. 实现 `backend/api/data.py`
3. 实现 `frontend/src/components/DataManager.vue`
4. 集成 Qlib 在线模式查询
5. 测试数据下载和查询

### 第五步：预测功能（多进程）
1. 实现 `backend/services/prediction_service.py`
   - Alpha158 特征计算
   - 多进程 Pool 实现
2. 实现 `backend/workers/predict_worker.py`
   - 子进程独立初始化 Qlib
   - Alpha158 数据准备
3. 实现 `backend/api/predict.py`
4. 实现 `frontend/src/components/PredictResult.vue`
5. 集成排序和查询功能
6. 测试多进程预测性能

### 第六步：持仓管理功能
1. 实现 `backend/api/position.py`
2. 实现 `frontend/src/components/PositionManager.vue`
3. 实现持仓的添加、删除、修改功能
4. 实现持仓的导入导出功能
5. 测试持仓管理功能

### 第七步：日志管理功能
1. 配置后端 loguru 日志
   - 输出到 `log/` 目录
   - 日志轮转（100MB，保留30天）
2. 实现 `backend/api/log.py`
3. 前端实现日志下载界面
4. 测试日志文件管理

### 第八步：集成测试和优化
1. 前后端联调测试
2. Qlib 在线模式性能测试
3. 多进程性能测试
4. 数据下载稳定性测试
5. 预测准确性和性能优化

---

## 关键技术实现

### FastAPI + MongoDB 异步配置
```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from .database import MongoDB
from .api import stock, data, predict, position, log

app = FastAPI()

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite 默认端口
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 生命周期事件
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化 MongoDB"""
    await MongoDB.connect_to_database(
        uri="mongodb://localhost:27017/",
        db_name="quant_system_db"
    )
    logger.info("MongoDB connected")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时断开 MongoDB"""
    await MongoDB.close_database()
    logger.info("MongoDB disconnected")

# 注册路由
app.include_router(stock.router)
app.include_router(data.router)
app.include_router(predict.router)
app.include_router(position.router)
app.include_router(log.router)
```

### Qlib 在线模式初始化
```python
import qlib
from qlib.config import C, MODE_CONF
from qlib.constant import REG_CN

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
```

### 多进程预测实现（MongoDB + Alpha158）
```python
# backend/services/prediction_service.py
from multiprocessing import Pool
import pickle
import qlib

def predict_worker(args):
    """子进程预测函数"""
    stock_batch, predict_date, model_pickle, provider_uri = args

    # 子进程独立初始化 Qlib
    import qlib as qlib_child
    from qlib.config import C, MODE_CONF
    from qlib.constant import REG_CN_CHILD
    from qlib.contrib.data.handler import Alpha158

    C.update(MODE_CONF["client"])
    qlib_child.init(provider_uri=provider_uri, region=REG_CN_CHILD)

    # 反序列化模型
    model = pickle.loads(model_pickle)

    results = []
    for code in stock_batch:
        # Alpha158 特征
        dataset = Alpha158(
            instruments=[code],
            start_time="2015-01-01",
            end_time=predict_date,
            fit_start_time="2015-01-01",
            fit_end_time=predict_date,
        )
        df = dataset.prepare("test")

        # 预测
        if df is not None or df.empty:
            continue

        pred = model.predict(df)
        results.append({
            "code": code,
            "score": float(pred[0]) if len(pred) > 0 else 0.0,
        })

    return results
```

### Alpha158 使用
```python
from qlib.contrib.data.handler import Alpha158

# 创建数据集
dataset = Alpha158(
    instruments=stocks,
    start_time="2015-01-01",
    end_time=predict_date,
    fit_start_time="2015-01-01",
    fit_end_time=predict_date,
)

# 准备特征
df = dataset.prepare("test")
# df 包含 158 个 Alpha 因子
```

### MongoDB 异步查询示例
```python
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# 连接
client = AsyncIOMotorClient("mongodb://localhost:27017/")
database = client["quant_system_db"]

# 查询
cursor = database.stocks.find({"enabled": True})
stocks = await cursor.to_list(length=None)

# 插入
result = await database.stocks.insert_one({"code": "sh600000", "name": "平安银行"})
stock_id = str(result.inserted_id)

# 更新
result = await database.stocks.update_one(
    {"code": "sh600000"},
    {"$set": {"enabled": False}}
)

# 删除
result = await database.stocks.delete_one({"code": "sh600000"})

# 排序
cursor = database.predictions.find({}).sort("score", -1).limit(100)
predictions = await cursor.to_list(length=None)
```

---

## 文件清单

### 需要创建的文件

#### 后端
- `examples/official/backend/main.py`
- `examples/official/backend/config.py`
- `examples/official/backend/database.py`
- `examples/official/backend/models.py`
- `examples/official/backend/api/__init__.py`
- `examples/official/backend/api/stock.py`
- `examples/official/backend/api/data.py`
- `examples/official/backend/api/predict.py`
- `examples/official/backend/api/position.py`
- `examples/official/backend/api/log.py`
- `examples/official/backend/services/__init__.py`
- `examples/official/backend/services/data_service.py`
- `examples/official/backend/services/prediction_service.py`
- `examples/official/backend/services/qlib_service.py`
- `examples/official/backend/services/mongo_service.py`
- `examples/official/backend/workers/__init__.py`
- `examples/official/backend/workers/predict_worker.py`
- `examples/official/backend/requirements.txt`

#### 前端
- `examples/official/frontend/index.html`
- `examples/official/frontend/package.json`
- `examples/official/frontend/vite.config.js`
- `examples/official/frontend/src/main.js`
- `examples/official/frontend/src/App.vue`
- `examples/official/frontend/src/components/StockManager.vue`
- `examples/official/frontend/src/components/DataManager.vue`
- `examples/official/frontend/src/components/PredictResult.vue`
- `examples/official/frontend/src/components/PositionManager.vue`
- `examples/official/frontend/src/api/stock.js`
- `examples/official/frontend/src/api/data.js`
- `examples/official/frontend/src/api/predict.js`
- `examples/official/frontend/src/api/position.js`
- `examples/official/frontend/src/utils/request.js`

#### 配置
- `examples/official/README.md`
- `examples/official/config.yaml`
- `examples/official/A500.csv`（需要用户提供或从网上下载）

### 参考文件
- `/Users/samlty/code/qlib/examples/TencentDataSource/tencent_data_source.py`
- `/Users/samlty/code/qlib/examples/TencentDataSource/predict_stocks.py`
- `/Users/samlty/code/qlib/examples/TencentDataSource/workflow.py`
- `/Users/samlty/code/qlib/examples/online_srv/online_management_simulate.py`（在线模式）
- `/Users/samlty/code/qlib/examples/model_rolling/task_manager_rolling.py`（MongoDB + TaskManager）
- `/Users/samlty/code/qlib/qlib/contrib/data/handler.py`（Alpha158）
- `/Users/samlty/code/qlib/qlib/config.py`（MODE_CONF）

---

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

---

## 部署说明

### 环境要求
- Python 3.8+
- MongoDB 5.0+
- Redis 6.0+（Qlib 在线模式缓存）
- Node.js 18+

### 启动步骤
1. 启动 MongoDB 服务
2. 启动 Redis 服务
3. 安装后端依赖：
   ```bash
   cd examples/official/backend
   pip install -r requirements.txt
   ```
4. 启动后端：
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
5. 安装前端依赖：
   ```bash
   cd examples/official/frontend
   npm install
   ```
6. 启动前端（开发模式）：
   ```bash
   npm run dev
   ```

---

## 开发顺序建议

1. **Week 1**: 项目初始化 + MongoDB 配置 + Qlib 在线模式
2. **Week 2**: 代码管理 + 数据管理（腾讯 API 集成）
3. **Week 3**: 预测功能 + 多进程优化 + 持仓筛选
4. **Week 4**: 持仓管理功能（导入导出、添加删除修改）
5. **Week 5**: 日志管理 + 集成测试
