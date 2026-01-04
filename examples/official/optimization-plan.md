# 优化量化投资管理系统实现计划

## 项目概述
在 `examples/official` 目录下创建一个基于 FastAPI 的量化投资管理系统，使用 MongoDB 存储数据，并利用 Qlib 在线模式进行数据管理。

**优化重点：**
1. **代码管理优化** - 支持股票代码的导入导出功能（CSV/Excel格式）
2. **交易代理管理优化** - 直接获取和显示代理的资产信息，包括账号ID、资产、持仓列表等
3. **主从代理机制** - 实现主用/从用代理切换，主用不可用时自动切换到从用，确保交易连续性

---

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
- **Excel 支持**: openpyxl, pandas
- **JWT 认证**: python-jose

### 前端
- **框架**: Vue.js 3 + Element Plus
- **构建**: Vite
- **调试**: 支持前后端联调模式
- **Excel 导入导出**: xlsx 库

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
│   │   ├── stock.py       # 代码管理 API（优化导入导出）
│   │   ├── data.py        # 数据管理 API
│   │   ├── predict.py     # 预测 API
│   │   ├── position.py     # 持仓管理 API（含交易操作）
│   │   ├── agent.py        # 交易代理管理 API（优化资产显示）
│   │   └── log.py        # 日志下载 API
│   ├── services/
│   │   ├── __init__.py
│   │   ├── data_service.py        # 腾讯数据下载服务
│   │   ├── prediction_service.py   # 多进程预测服务
│   │   ├── qlib_service.py      # Qlib 在线模式封装
│   │   ├── mongo_service.py      # MongoDB 操作服务
│   │   ├── agent_service.py      # 交易代理服务（优化主从机制）
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
│   │   │   ├── StockManager.vue      # 代码管理（优化导入导出）
│   │   │   ├── DataManager.vue        # 数据管理
│   │   │   ├── PredictResult.vue     # 预测结果
│   │   │   ├── PositionManager.vue   # 持仓管理（含交易操作）
│   │   │   ├── AgentManager.vue      # 交易代理管理（优化资产显示）
│   │   │   ├── TradeManager.vue       # 交易管理（基于预测结果）
│   │   │   └── LogManager.vue         # 日志管理
│   │   ├── api/
│   │   │   ├── stock.js
│   │   │   ├── data.js
│   │   │   ├── predict.js
│   │   │   ├── position.js
│   │   │   ├── agent.js
│   │   │   └── trade.js            # 交易 API
│   │   └── utils/
│   │       └── request.js    # Axios 封装
│   ├── package.json
│   └── vite.config.js
├── A500.csv               # 默认股票列表（中证500成分股）
├── README.md
├── config.yaml            # 系统配置文件
└── trade_agent.md           # 交易代理接口文档
```

---

## MongoDB 数据库设计（优化）

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

# 4. agent_configs - 代理配置（支持多个代理）
{
    "_id": ObjectId,
    "agent_id": str,             # 代理唯一ID
    "agent_url": str,           # 代理 URL
    "agent_token": str,        # 代理 Token
    "agent_name": str,           # 代理名称
    "is_primary": bool,         # 是否主用代理
    "status": str,             # 状态（active/inactive/unavailable）
    "last_heartbeat": datetime, # 最后心跳时间
    "created_at": datetime,
    "updated_at": datetime,
}

# 5. agent_positions - 代理持仓记录
{
    "_id": ObjectId,
    "agent_id": str,            # 关联的代理ID
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
    "agent_id": str,          # 代理ID
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

## 核心功能实现（优化）

### 1. 代码管理模块（优化导入导出）

#### 后端实现优化 (backend/api/stock.py)

```python
from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from ..database import MongoDB
from ..models import StockCreate, StockUpdate, StockResponse
from datetime import datetime
from ..services.data_service import standardize_stock_codes
from io import BytesIO
import pandas as pd

router = APIRouter(prefix="/api/stocks", tags=["Stocks"])

@router.get("/", response_model=List[StockResponse])
async def get_stocks(enabled_only: bool = False):
    """获取股票列表"""
    return await MongoDB.get_stocks(enabled_only=enabled_only)

@router.get("/export")
async def export_stocks(format: str = "csv"):
    """
    导出股票列表

    Args:
        format: 导出格式（csv/excel）

    Returns:
        文件响应（CSV或Excel）
    """
    stocks = await MongoDB.get_stocks()

    # 转换为 DataFrame
    df = pd.DataFrame(stocks)
    df = df[["code", "name", "enabled", "is_a500"]]

    # 根据格式导出
    if format.lower() == "excel":
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Stocks")
        output.seek(0)

        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=stocks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"}
        )
    else:
        # CSV 格式（默认）
        output = BytesIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')
        output.seek(0)

        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=stocks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
        )

@router.post("/import")
async def import_stocks(file: UploadFile = File(...)):
    """
    导入股票列表（支持 CSV 和 Excel）

    Args:
        file: 上传的文件（CSV 或 Excel）

    Returns:
        导入结果统计
    """
    try:
        content = await file.read()
        filename = file.filename.lower()

        # 读取文件
        if filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(content))
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(BytesIO(content), engine='openpyxl')
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        # 验证必需列
        required_columns = {'code', 'name'}
        if not required_columns.issubset(df.columns):
            raise HTTPException(status_code=400, detail=f"Missing required columns: {required_columns}")

        # 标准化股票代码格式
        df['code'] = standardize_stock_codes(df['code'].tolist())

        # 导入数据
        imported = 0
        updated = 0
        skipped = 0

        for _, row in df.iterrows():
            code = row['code']
            name = row['name']

            # 检查是否已存在
            existing = await MongoDB.get_stock(code)
            if existing:
                # 更新
                await MongoDB.update_stock(code, {
                    "name": name,
                    "enabled": row.get('enabled', True),
                    "is_a500": row.get('is_a500', False),
                    "updated_at": datetime.utcnow()
                })
                updated += 1
            else:
                # 插入新股票
                await MongoDB.insert_stock({
                    "code": code,
                    "name": name,
                    "enabled": row.get('enabled', True),
                    "is_a500": row.get('is_a500', False),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })
                imported += 1

        return {
            "message": f"Successfully imported stocks: {imported} added, {updated} updated, {skipped} skipped",
            "imported": imported,
            "updated": updated,
            "skipped": skipped,
            "total": len(df)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import stocks: {str(e)}")

@router.post("/initialize")
async def initialize_stocks_from_csv():
    """
    重新初始化代码列表
    从 A500.csv 文件读取股票列表，清空现有数据并导入
    """
    try:
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

#### 前端界面优化 (StockManager.vue)

- **导入功能**：
  - 文件上传按钮（支持 CSV 和 Excel）
  - 支持拖拽上传
  - 导入预览（显示将要导入的股票列表）
  - 导入结果统计（新增、更新、跳过）

- **导出功能**：
  - 导出为 CSV 按钮
  - 导出为 Excel 按钮
  - 选择导出内容（全部/仅启用/仅禁用）
  - 支持自定义列选择

- **批量操作优化**：
  - 多选复选框
  - 全选/取消全选
  - Shift+点击连续选择
  - 批量启用/禁用/删除

- **数据验证**：
  - 导入时验证股票代码格式
  - 验证必需列（code, name）
  - 显示导入错误详情

---

### 2. 交易代理管理模块（优化资产显示）

#### 后端实现优化 (backend/api/agent.py)

```python
from fastapi import APIRouter, HTTPException
from ..services.agent_service import AgentService
from ..models import (
    AgentConfigCreate, AgentConfigResponse,
    AgentAssetInfo, AgentPosition,
)
from datetime import datetime

router = APIRouter(prefix="/api/agent", tags=["Agent"])

@router.get("/config")
async def get_agent_configs():
    """
    获取所有代理配置
    """
    return await AgentService.get_agent_configs()

@router.get("/config/{agent_id}")
async def get_agent_config(agent_id: str):
    """
    获取指定代理配置
    """
    config = await AgentService.get_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")
    return config

@router.post("/config")
async def create_agent_config(config: AgentConfigCreate):
    """
    创建代理配置
    """
    return await AgentService.create_agent_config(config)

@router.put("/config/{agent_id}")
async def update_agent_config(agent_id: str, config: AgentConfigCreate):
    """
    更新代理配置
    """
    return await AgentService.update_agent_config(agent_id, config)

@router.delete("/config/{agent_id}")
async def delete_agent_config(agent_id: str):
    """
    删除代理配置
    """
    return await AgentService.delete_agent_config(agent_id)

@router.put("/config/{agent_id}/primary")
async def set_primary_agent(agent_id: str):
    """
    设置主用代理

    Args:
        agent_id: 代理ID

    Returns:
        操作结果
    """
    return await AgentService.set_primary_agent(agent_id)

@router.get("/primary")
async def get_primary_agent():
    """
    获取当前主用代理
    """
    return await AgentService.get_primary_agent()

@router.get("/status")
async def get_agents_status():
    """
    获取所有代理状态
    """
    return await AgentService.get_agents_status()

@router.get("/asset/{agent_id}")
async def get_agent_asset_info(agent_id: str):
    """
    获取代理资产信息（账号ID、资产、持仓列表）

    Args:
        agent_id: 代理ID

    Returns:
        资产信息（账号ID、总资产、可用资金、持仓列表等）
    """
    return await AgentService.get_agent_asset_info(agent_id)

@router.post("/orders")
async def submit_agent_orders(action: str, stocks: List[dict]):
    """
    提交交易订单到代理

    Args:
        action: 交易类型（buy/sell/cancel）
        stocks: 股票列表

    Returns:
        订单提交结果
    """
    return await AgentService.submit_orders(action, stocks)

@router.get("/orders")
async def get_agent_orders(order_id: str = None, limit: int = 100):
    """
    查询代理订单状态

    Args:
        order_id: 订单ID（可选）
        limit: 返回数量限制

    Returns:
        订单列表
    """
    return await AgentService.get_agent_orders(order_id, limit)

@router.get("/positions/{agent_id}")
async def get_agent_positions(agent_id: str):
    """
    查询代理持仓状态

    Args:
        agent_id: 代理ID

    Returns:
        持仓列表
    """
    return await AgentService.get_agent_positions(agent_id)

@router.post("/heartbeat/{agent_id}")
async def heartbeat_agent(agent_id: str):
    """
    代理心跳检测

    Args:
        agent_id: 代理ID

    Returns:
        心跳检测结果
    """
    return await AgentService.heartbeat_agent(agent_id)
```

#### 交易代理服务优化 (backend/services/agent_service.py)

```python
import httpx
from typing import Dict, List, Optional
from datetime import datetime
from ..services.mongo_service import MongoDB
from loguru import logger

class AgentService:
    """交易代理管理服务（优化主从机制）"""

    @staticmethod
    async def get_agent_configs():
        """获取所有代理配置"""
        configs = await MongoDB.get_all_agent_configs()
        return configs

    @staticmethod
    async def get_agent_config(agent_id: str):
        """获取指定代理配置"""
        return await MongoDB.get_agent_config(agent_id)

    @staticmethod
    async def create_agent_config(config: AgentConfigCreate):
        """创建代理配置"""
        return await MongoDB.create_agent_config(config)

    @staticmethod
    async def update_agent_config(agent_id: str, config: AgentConfigCreate):
        """更新代理配置"""
        return await MongoDB.update_agent_config(agent_id, config)

    @staticmethod
    async def delete_agent_config(agent_id: str):
        """删除代理配置"""
        return await MongoDB.delete_agent_config(agent_id)

    @staticmethod
    async def set_primary_agent(agent_id: str):
        """
        设置主用代理

        将指定代理设置为主用，其他代理自动切换为从用
        """
        # 检查代理是否存在
        config = await MongoDB.get_agent_config(agent_id)
        if not config:
            raise HTTPException(status_code=404, detail="Agent not found")

        # 将所有代理的 is_primary 设置为 False
        await MongoDB.update_all_agents_primary(agent_id)

        # 设置主用代理
        result = await MongoDB.update_agent_config(agent_id, {
            "is_primary": True,
            "updated_at": datetime.utcnow()
        })

        logger.info(f"Set primary agent: {agent_id}")
        return {"message": f"Successfully set {agent_id} as primary agent"}

    @staticmethod
    async def get_primary_agent():
        """
        获取当前主用代理

        Returns:
            主用代理配置，如果没有则返回 None
        """
        return await MongoDB.get_primary_agent_config()

    @staticmethod
    async def get_agents_status():
        """
        获取所有代理状态

        Returns:
            代理状态列表（包含是否可用、是否主用）
        """
        configs = await MongoDB.get_all_agent_configs()

        # 检查每个代理的状态
        for config in configs:
            try:
                # 尝试连接代理
                asset_info = await AgentService.get_agent_asset_info(config['agent_id'])
                config['status'] = 'active'
                config['last_heartbeat'] = datetime.utcnow()
            except Exception as e:
                logger.warning(f"Agent {config['agent_id']} is unavailable: {e}")
                config['status'] = 'unavailable'

        return configs

    @staticmethod
    async def get_agent_asset_info(agent_id: str):
        """
        获取代理资产信息（账号ID、资产、持仓列表）

        Args:
            agent_id: 代理ID

        Returns:
            资产信息：
            {
                "account_id": str,        # 账号ID
                "total_assets": float,    # 总资产
                "available_cash": float,  # 可用资金
                "market_value": float,    # 市值
                "positions": [           # 持仓列表
                    {
                        "code": "sh600000",
                        "name": "平安银行",
                        "quantity": 1000,
                        "cost_price": 12.50,
                        "market_value": 12500.00,
                        "pnl": 1250.00,
                        "pnl_percent": 10.00,
                    },
                    ...
                ],
                "updated_at": datetime,
            }
        """
        config = await MongoDB.get_agent_config(agent_id)
        if not config:
            raise HTTPException(status_code=404, detail="Agent not found")

        # 调用代理 API 获取资产信息
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{config['agent_url']}/api/trade/asset",
                headers={
                    "Authorization": f"Bearer {config['agent_token']}",
                },
                timeout=30.0
            )
            response.raise_for_status()
            asset_data = response.json()

        # 调用代理 API 获取持仓列表
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{config['agent_url']}/api/trade/positions_and_trades",
                headers={
                    "Authorization": f"Bearer {config['agent_token']}",
                },
                timeout=30.0
            )
            response.raise_for_status()
            positions_data = response.json()

        # 整合数据
        asset_info = {
            "account_id": asset_data.get("account_id", ""),
            "total_assets": asset_data.get("total_assets", 0.0),
            "available_cash": asset_data.get("available_cash", 0.0),
            "market_value": asset_data.get("market_value", 0.0),
            "positions": positions_data.get("positions", []),
            "updated_at": datetime.utcnow(),
        }

        # 更新心跳时间
        await MongoDB.update_agent_heartbeat(agent_id)

        return asset_info

    @staticmethod
    async def submit_orders(action: str, stocks: List[dict]):
        """
        提交交易订单到代理

        Args:
            action: 交易类型（buy/sell/cancel）
            stocks: 股票列表

        Returns:
            订单提交结果
        """
        # 获取主用代理
        primary_agent = await AgentService.get_primary_agent()
        if not primary_agent:
            raise HTTPException(status_code=503, detail="No primary agent available")

        # 检查主用代理是否可用
        if primary_agent['status'] != 'active':
            # 尝试切换到可用的从用代理
            await AgentService._failover_to_secondary_agent()

            # 重新获取主用代理
            primary_agent = await AgentService.get_primary_agent()
            if not primary_agent or primary_agent['status'] != 'active':
                raise HTTPException(status_code=503, detail="No available agent for trading")

        # 提交订单到主用代理
        payload = {
            "action": action,
            "stocks": stocks,
            "timestamp": datetime.now().isoformat()
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{primary_agent['agent_url']}/api/trade/order_commit",
                json=payload,
                headers={
                    "Authorization": f"Bearer {primary_agent['agent_token']}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def get_agent_orders(order_id: str = None, limit: int = 100):
        """查询代理订单状态"""
        primary_agent = await AgentService.get_primary_agent()
        if not primary_agent:
            raise HTTPException(status_code=503, detail="No primary agent available")

        params = {}
        if order_id:
            params["order_id"] = order_id
        if limit:
            params["limit"] = limit

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{primary_agent['agent_url']}/api/trade/order",
                params=params,
                headers={
                    "Authorization": f"Bearer {primary_agent['agent_token']}",
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def get_agent_positions(agent_id: str):
        """查询代理持仓状态"""
        config = await MongoDB.get_agent_config(agent_id)
        if not config:
            raise HTTPException(status_code=404, detail="Agent not found")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{config['agent_url']}/api/trade/positions_and_trades",
                headers={
                    "Authorization": f"Bearer {config['agent_token']}",
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def heartbeat_agent(agent_id: str):
        """
        代理心跳检测

        Args:
            agent_id: 代理ID

        Returns:
            心跳检测结果（是否可用）
        """
        try:
            # 尝试获取资产信息
            asset_info = await AgentService.get_agent_asset_info(agent_id)
            await MongoDB.update_agent_status(agent_id, "active")
            return {"status": "active", "agent_id": agent_id}
        except Exception as e:
            logger.warning(f"Heartbeat failed for agent {agent_id}: {e}")
            await MongoDB.update_agent_status(agent_id, "unavailable")
            return {"status": "unavailable", "agent_id": agent_id}

    @staticmethod
    async def _failover_to_secondary_agent():
        """
        自动故障转移到从用代理

        将第一个可用的从用代理提升为主用
        """
        configs = await MongoDB.get_all_agent_configs()

        # 找到第一个可用的从用代理
        for config in configs:
            if not config['is_primary']:
                try:
                    # 检查代理是否可用
                    await AgentService.heartbeat_agent(config['agent_id'])
                    # 提升为主用代理
                    await AgentService.set_primary_agent(config['agent_id'])
                    logger.info(f"Failed over to secondary agent: {config['agent_id']}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to failover to {config['agent_id']}: {e}")
                    continue

        logger.error("No available secondary agent for failover")
```

#### MongoDB 服务扩展 (backend/services/mongo_service.py)

```python
# 在后添加以下方法：

@classmethod
async def get_all_agent_configs(cls):
    """获取所有代理配置"""
    configs = await cls.database.agent_configs.find({}).to_list(length=None)
    return configs

@classmethod
async def get_agent_config(cls, agent_id: str):
    """获取指定代理配置"""
    config = await cls.database.agent_configs.find_one({"agent_id": agent_id})
    return config

@classmethod
async def create_agent_config(cls, config: AgentConfigCreate):
    """创建代理配置"""
    agent_id = f"agent_{datetime.now().timestamp()}"

    agent_dict = config.dict()
    agent_dict["agent_id"] = agent_id
    agent_dict["is_primary"] = False  # 默认不是主用
    agent_dict["status"] = "inactive"
    agent_dict["last_heartbeat"] = None
    agent_dict["created_at"] = datetime.utcnow()
    agent_dict["updated_at"] = datetime.utcnow()

    await cls.database.agent_configs.insert_one(agent_dict)
    return agent_dict

@classmethod
async def update_agent_config(cls, agent_id: str, config: AgentConfigCreate):
    """更新代理配置"""
    result = await cls.database.agent_configs.update_one(
        {"agent_id": agent_id},
        {"$set": {
            "agent_url": config.agent_url,
            "agent_token": config.agent_token,
            "agent_name": config.agent_name,
            "updated_at": datetime.utcnow()
        }}
    )
    return result.modified_count > 0

@classmethod
async def delete_agent_config(cls, agent_id: str):
    """删除代理配置"""
    result = await cls.database.agent_configs.delete_one({"agent_id": agent_id})
    return result.deleted_count > 0

@classmethod
async def update_all_agents_primary(cls, primary_agent_id: str):
    """将所有代理的 is_primary 设置为 False，除了指定代理"""
    await cls.database.agent_configs.update_many(
        {"agent_id": {"$ne": primary_agent_id}},
        {"$set": {"is_primary": False}}
    )

@classmethod
async def get_primary_agent_config(cls):
    """获取主用代理配置"""
    config = await cls.database.agent_configs.find_one({"is_primary": True})
    return config

@classmethod
async def update_agent_heartbeat(cls, agent_id: str):
    """更新代理心跳时间"""
    await cls.database.agent_configs.update_one(
        {"agent_id": agent_id},
        {"$set": {
            "last_heartbeat": datetime.utcnow(),
            "status": "active"
        }}
    )

@classmethod
async def update_agent_status(cls, agent_id: str, status: str):
    """更新代理状态"""
    await cls.database.agent_configs.update_one(
        {"agent_id": agent_id},
        {"$set": {"status": status}}
    )
```

#### 前端界面优化 (AgentManager.vue)

- **代理列表**：
  - 显示所有代理（主用/从用）
  - 显示代理状态（可用/不可用）
  - 显示代理连接信息（URL、最后心跳时间）
  - 操作按钮：编辑、删除、设为主用

- **资产信息显示**：
  - 点击代理卡片显示详细资产信息
  - 账号ID
  - 总资产
  - 可用资金
  - 市值
  - 持仓列表（表格形式）

- **主从代理管理**：
  - 添加代理按钮
  - 设置主用代理按钮
  - 代理状态指示器（绿色=可用，红色=不可用）
  - 主用代理标识（星标或标签）

- **自动故障转移提示**：
  - 当主用代理不可用时，显示警告提示
  - 显示自动切换到从用代理的消息
  - 记录故障转移日志

- **代理健康检查**：
  - 定时心跳检测（每30秒）
  - 实时更新代理状态
  - 可用性百分比显示

---

### 3. 主从代理机制实现

#### 核心逻辑

1. **主用代理选择**：
   - 系统启动时，自动选择第一个可用的代理作为主用
   - 用户可以手动设置主用代理
   - 同一时间只能有一个主用代理

2. **故障检测**：
   - 定时心跳检测（每30秒）
   - 检测主用代理是否可用
   - 如果主用代理不可用，触发故障转移

3. **自动故障转移**：
   - 主用代理不可用时，自动切换到第一个可用的从用代理
   - 提示用户代理已切换
   - 记录故障转移日志

4. **交易保护**：
   - 所有交易操作都通过主用代理执行
   - 如果主用代理不可用，先尝试故障转移
   - 故障转移失败，阻止交易操作并提示用户

#### UI 实现

- **状态栏**：显示当前主用代理状态（可用/不可用）
- **警告提示**：当主用代理不可用时，显示警告横幅
- **按钮禁用**：当主用代理不可用时，禁用所有交易相关按钮
- **错误提示**：交易失败时，显示友好的错误消息

---

## 实现步骤（优化）

### Week 1: 基础设施
1. 项目初始化 + MongoDB 配置 + Qlib 在线模式
2. FastAPI 应用结构 + 基础 API 路由

### Week 2: 代码管理
1. 代码管理 API + 数据库模型
2. 导入导出功能（CSV/Excel）
3. 批量操作 + 多选功能
4. 前端界面实现

### Week 3: 数据管理 + 预测
1. 数据管理 API + 腾讯 API 集成
2. 预测功能 + 多进程优化
3. 前端界面实现

### Week 4: 持仓管理
1. 持仓管理 API + 数据库模型
2. 交易操作（买入/卖出/同步）
3. 前端界面实现

### Week 5: 交易代理管理（重点）
1. 代理配置 API + 数据库模型
2. 主从代理机制 + 故障转移
3. 资产信息获取 + 显示
4. 前端界面实现

### Week 6: 集成测试 + 优化
1. 端到端测试
2. 性能优化
3. 文档完善

---

## 关键优化点

### 1. 代码管理优化
- ✅ 支持导入导出（CSV/Excel格式）
- ✅ 灵活的列映射
- ✅ 数据验证
- ✅ 批量操作优化

### 2. 交易代理管理优化
- ✅ 显示代理资产信息（账号ID、资产、持仓列表）
- ✅ 实时资产更新
- ✅ 持仓详细信息

### 3. 主从代理机制
- ✅ 主用/从用代理配置
- ✅ 自动故障转移
- ✅ 心跳检测
- ✅ 交易保护机制
- ✅ UI 状态反馈

---

## 依赖项更新

### backend/requirements.txt

```
# FastAPI
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# Database
motor==3.3.2
pymongo==4.6.0
redis==5.0.1

# Qlib
qlib>=0.9.0

# Data processing
pandas>=2.0.0
numpy>=1.24.0

# HTTP client
httpx==0.25.2
requests==2.31.0

# Excel support
openpyxl==3.1.2
xlsxwriter==3.1.9

# Logging
loguru==0.7.2

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
```

---

## 关键文件路径

### 后端
- `/Users/abc/workspace/qlib/examples/official/backend/api/stock.py` - 代码管理API（优化导入导出）
- `/Users/abc/workspace/qlib/examples/official/backend/api/agent.py` - 代理管理API（优化资产显示）
- `/Users/abc/workspace/qlib/examples/official/backend/services/agent_service.py` - 代理服务（优化主从机制）
- `/Users/abc/workspace/qlib/examples/official/backend/services/mongo_service.py` - MongoDB服务

### 前端
- `/Users/abc/workspace/qlib/examples/official/frontend/src/components/StockManager.vue` - 代码管理（优化导入导出）
- `/Users/abc/workspace/qlib/examples/official/frontend/src/components/AgentManager.vue` - 代理管理（优化资产显示）

---

## 参考文件

- `/Users/abc/workspace/qlib/examples/TencentDataSource/tencent_data_source.py`
- `/Users/abc/workspace/qlib/examples/TencentDataSource/predict_stocks.py`
- `/Users/abc/workspace/qlib/examples/online_srv/online_management_simulate.py`（在线模式）
- `/Users/abc/workspace/qlib/examples/model_rolling/task_manager_rolling.py`（MongoDB + TaskManager）
- `/Users/abc/workspace/qlib/qlib/contrib/data/handler.py`（Alpha158）
- `/Users/abc/workspace/qlib/qlib/config.py`（MODE_CONF）
- `/Users/abc/workspace/qlib/examples/official/trade_agent.md`（交易代理接口文档）
