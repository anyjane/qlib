# QMTMini 代理服务器功能分析报告

本文档提供了 QMTMini 代理服务器项目的详细功能分析，包括入口分析、功能模块以及 API 接口说明。

## 1. 项目概述
该项目是一个基于 **FastAPI** 构建的代理服务器，通过 `xtquant` 库与 **QMT (Quant Master Trader) Mini** 客户端进行交互。它对外提供 RESTful API，用于查询行情数据、账户资产、持仓情况以及执行交易操作。

- **操作系统**: Windows (QMT 运行要求)
- **开发框架**: FastAPI
- **核心库**: `xtquant` (`StockAccount`, `XtQuantTrader`, `xtdata`)
- **数据库**: MongoDB (已配置，当前主要用于扩展)

---

## 2. 入口程序分析
模拟环境的主要入口脚本是 `sim-xtrader-run.sh`。

### 启动流程：
1.  **启动 QMT 客户端**：切换到 QMT 二进制目录，通过 `XtMiniQmt.exe` 启动模拟端。
2.  **环境配置**：生成 `.env.dev` 文件，包含以下关键配置：
    - `DATABASE_URL`: MongoDB 连接字符串。
    - `secret_key`: 用于 JWT 认证。
    - `ACCOUNT`: 证券账号 ID。
    - `QMTMINI_PATH`: QMT 用户数据 (userdata_mini) 路径。
3.  **启动 FastAPI 应用**：激活虚拟环境并执行 `uvicorn app-with-trade:app`。

---

## 3. 接口说明 (API Interfaces)
所有交易相关接口的前缀均为 `/api/trade`。

### 3.1. 账户与持仓查询

#### 获取资产信息
- **URL**: `/api/trade/asset`
- **方法**: `GET`
- **描述**: 获取账户资产详情（可用资金、总资产、市值等）。
- **参数**: 无

#### 获取订单列表
- **URL**: `/api/trade/order`
- **方法**: `GET`
- **描述**: 获取当前账户的所有委托订单及其状态。
- **参数**: 无

#### 获取持仓与成交记录
- **URL**: `/api/trade/positions_and_trades`
- **方法**: `GET`
- **描述**: 获取账户当前的持仓列表以及关联的历史成交记录。
- **参数**: 无

---

### 3.2. 交易操作

#### 提交订单 (order_commit)
- **URL**: `/api/trade/order_commit`
- **方法**: `POST`
- **描述**: 提交股票买卖委托。支持立即执行或设定时间定时执行。
- **参数 (JSON Body)**:
```json
{
  "stock_code": "600000.SH",
  "isBuy": true,
  "order_volume": 100,
  "price_type": "FIX_PRICE",
  "order_price": 7.5,
  "strategy": "default_strategy",
  "order_remark": "test order",
  "order_time_category": "NOW",
  "order_time": "2026-01-04 14:00:00"
}
```
> **注**: `price_type` 可选 `FIX_PRICE` (限价), `LIMIT_UP` (涨停价), `LIMIT_DOWN` (跌停价)。`order_time_category` 若为 `TIME`，则根据 `order_time` 定时触发。

#### 撤销订单 (order_cancel)
- **URL**: `/api/trade/order_cancel`
- **方法**: `GET`
- **描述**: 根据订单 ID 撤销未成交的委托。
- **参数 (Query Params)**:
```json
{
  "order_id": "12345678"
}
```

---

### 3.3. 行情数据接口

#### 获取全量 Tick 数据
- **URL**: `/api/trade/full_tick`
- **方法**: `GET`
- **描述**: 获取指定股票列表的最新实时逐笔数据。
- **参数 (Query Params)**:
```json
{
  "code_list": "600000.SH,000001.SZ"
}
```

#### 获取历史数据
- **URL**: `/api/trade/history_data`
- **方法**: `GET`
- **描述**: 获取指定股票的历史 K 线数据。
- **参数 (Query Params)**:
```json
{
  "code_list": "600000.SH",
  "start_date": "2025-12-01",
  "end_date": "2025-12-31",
  "period": "1d"
}
```

---

## 4. 内部实现说明

### 4.1. `xtquant` 集成
核心逻辑位于 `trader/qmt/xtrader.py`。
- **`XTrader` 类**:
    - 初始化 `StockAccount` 并通过 `XtQuantTrader` 连接 QMT。
    - 采用会话管理机制，在 100-120 范围内尝试不同的 `session_id` 直到连接成功。
    - 将 `xtconstant` 的内部状态码（如 `ORDER_REPORTED`）映射为中文描述（如“已报”）。
- **回调处理**:
    - `MyXtQuantTraderCallback` 监听订单状态变化、成交回报、连接断开等事件，并实时打印日志。

### 4.2. 异常处理
`TradeRouter` 封装了基本的错误捕获。如果 `xtrader` 实例未初始化或 QMT 调用失败，接口将返回如下格式的错误信息：
```json
{
  "status_code": 400,
  "response_type": "error",
  "description": "错误详情描述",
  "data": ""
}
```

