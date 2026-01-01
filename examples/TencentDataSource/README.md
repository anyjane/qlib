# TencentDataSource - Qlib 自定义数据源完整示例

本项目演示了如何使用腾讯股票 API 作为自定义数据源接入 Qlib 量化框架，实现从数据采集、特征工程（Alpha158 因子）、模型训练到回测分析的完整量化投资流程。

## 项目概述

### 核心功能

- **腾讯 HTTP API 集成**：从腾讯公共 API 获取股票 K 线数据，支持日线数据
- **智能分页处理**：自动处理 API 的 2000 条记录限制，通过分页逻辑获取完整历史数据
- **CSI300 股票池**：使用沪深 300 指数成分股作为交易标的池
- **Alpha158 特征工程**：实现 158 个经典技术分析因子，构建多维度的特征体系
- **完整量化工作流**：端到端的数据处理、特征计算、模型训练和回测评估流程
- **性能指标输出**：自动计算并输出年化收益率、夏普比率等关键指标
- **完善的日志系统**：提供详细的日志记录，便于调试和监控

### 技术架构

本项目展示了如何在 Qlib 框架中实现自定义数据源的完整流程：

```
数据采集层 (TencentCollector)
    ↓
数据规范化层 (TencentNormalize)
    ↓
Qlib 数据格式 (dump_bin)
    ↓
特征工程层 (Alpha158)
    ↓
模型训练层 (LGBModel)
    ↓
策略回测层 (TopkDropoutStrategy)
    ↓
性能评估层 (PortAnaRecord)
```

## 项目结构

```
TencentDataSource/
├── __init__.py                        # 包初始化文件
├── config.py                          # 全局配置参数
├── tencent_data_source.py             # 数据采集器和规范化器（继承 data_collector.base）
├── workflow.py                        # 训练和回测工作流
├── run_example.py                     # 主入口程序
├── workflow_config_tencent_alpha158.yaml  # YAML 配置文件
├── DATA_COLLECTOR_AVAILABLE_REMOVAL.md  # 移除 data_collector 条件判断说明
├── IMPORT_FIX_SUMMARY.md              # 导入问题修复文档
└── README.md                          # 本文件
```

### 核心文件说明

#### 1. `tencent_data_source.py` - 数据源实现

这是项目的核心文件，实现了三个关键类：

- **TencentCollector**: 数据采集器，负责从腾讯 API 获取原始数据
- **TencentNormalize**: 数据规范化器，将原始数据转换为 Qlib 标准格式
- **TencentRun**: 运行器，协调整个数据采集和规范化流程

#### 2. `workflow.py` - 工作流实现

实现了基于 Qlib 的完整量化工作流，包括：

- 模型训练（LightGBM）
- 信号生成
- 策略回测
- 性能分析

#### 3. `run_example.py` - 用户接口

提供了简洁的命令行接口，支持三种运行模式：

- `collect`: 仅执行数据采集
- `workflow`: 仅执行训练和回测
- `all`: 执行完整流程

## 计算原理

### 1. 数据采集与处理

#### 数据源选择

本项目使用腾讯证券提供的免费 HTTP API 作为数据源：

- **API 地址**: `https://web.ifzq.gtimg.cn/appstock/app/fqkline/get`
- **数据类型**: 日线 K 线数据
- **价格类型**: 前复权价格（qfq，考虑分红送股等因素调整后的价格）

#### API 请求格式

```
GET https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},{interval},{start},{end},{count},{qfq}
```

**参数说明**：
- `symbol`: 股票代码（如 "sh600000" 或 "sz000001"）
- `interval`: 数据间隔，"day" 表示日线
- `start`: 起始日期（如 "2020-01-01"）
- `end`: 结束日期（如 "2025-12-31"）
- `count`: 单次请求最大记录数（最多 2000 条）
- `qfq`: "qfq" 表示前复权价格

#### 分页处理逻辑

腾讯 API 限制每次请求最多返回 2000 条记录，对于超过 2000 条的历史数据，需要通过分页获取。本项目实现了智能分页逻辑：

```python
# 分页逻辑示例
while fetch_count < max_fetches:
    # 1. 发起请求，获取最多 2000 条记录
    data = _fetch_from_api(param_str)
    
    # 2. 如果获取了 2000 条，说明还有更多数据
    if len(data) >= 2000:
        # 3. 使用当前批次最早的日期作为新的结束日期
        oldest_date = data[0][0]
        current_end_date = pd.Timestamp(oldest_date) - pd.Timedelta(days=1)
        # 4. 继续请求更早的数据
    else:
        # 5. 获取了少于 2000 条，说明已获取全部数据
        break
```

**分页工作原理**：

假设需要获取 3000 条交易日的数据（2020-01-01 至 2025-12-31）：

1. **第一次请求**：
   - 参数: `sh600000,day,2020-01-01,2025-12-31,2000,qfq`
   - 结果: 返回最新的 2000 条（2021-01-01 至 2025-12-31）

2. **第二次请求**：
   - 参数: `sh600000,day,2020-01-01,2020-12-31,2000,qfq`
   - 结果: 返回剩余的 1000 条（2020-01-01 至 2020-12-31）

3. **总计**: 3000 条完整数据

#### 数据规范化

原始数据需要转换为 Qlib 标准格式，主要包括：

1. **日期处理**：将日期字符串转换为 Pandas Timestamp
2. **数值类型转换**：将价格、成交量等转换为数值类型
3. **缺失值处理**：
   - 成交量缺失设为 0
   - 价格字段使用前向填充（ffill）和后向填充（bfill）
4. **去重处理**：移除重复的日期记录
5. **计算收益率**：`change = close.pct_change()`

### 2. 特征工程 - Alpha158

Alpha158 是 Qlib 提供的经典技术分析因子集合，包含 158 个不同的因子。

#### 因子分类

Alpha158 因子可以大致分为以下几类：

1. **价格相关因子**：
   - 收盘价相对于最高价、最低价的位置
   - 价格的移动平均线（MA）
   - 价格的波动率

2. **成交量相关因子**：
   - 成交量的移动平均
   - 量价关系（OBV、成交量与价格的关联）
   - 成交量变化率

3. **技术指标因子**：
   - RSI（相对强弱指标）
   - MACD（指数平滑异同移动平均线）
   - KDJ（随机指标）
   - 布林带（Bollinger Bands）

4. **趋势因子**：
   - ADX（平均趋向指标）
   - ATR（平均真实波幅）
   - 移动平均线的斜率

5. **动量因子**：
   - 不同时间周期的收益率
   - 价格动量
   - 相对强度

#### 因子计算原理

Alpha158 的核心思想是通过多个时间窗口（如 5 日、10 日、20 日、60 日等）计算技术指标，从而捕捉股票在不同时间尺度上的特征。

**示例因子计算**：

```python
# 简单移动平均线
MA5 = close.rolling(5).mean()

# 相对强弱指标（RSI）
def rsi(close, n=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(n).mean()
    avg_loss = loss.rolling(n).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# 量价关系
OBV = volume * np.sign(close.diff())
```

### 3. 模型训练 - LightGBM

本项目使用 LightGBM 梯度提升树模型进行训练。

#### 模型配置

```python
MODEL_CONFIG = {
    "loss": "mse",              # 损失函数：均方误差
    "learning_rate": 0.2,       # 学习率
    "max_depth": 8,             # 树的最大深度
    "num_leaves": 210,          # 叶子节点数量
    "colsample_bytree": 0.8879, # 特征采样比例
    "subsample": 0.8789,        # 样本采样比例
    "lambda_l1": 205.6999,      # L1 正则化系数
    "lambda_l2": 580.9768,      # L2 正则化系数
    "num_threads": 20,          # 并行线程数
}
```

#### 训练过程

1. **数据集划分**：
   - 训练集：2020-01-01 至 2024-12-31
   - 测试集：2025-01-01 至 2025-12-31

2. **训练目标**：
   - 使用 Alpha158 因子作为特征（X）
   - 使用下一日的收益率作为标签（y）
   - 目标是预测股票的相对收益能力

3. **模型评估**：
   - 使用测试集评估模型表现
   - 输出 IC（信息系数）、ICIR（信息系数信息比率）等指标

### 4. 策略回测 - TopkDropoutStrategy

本项目使用 TopkDropoutStrategy 策略进行回测。

#### 策略逻辑

1. **信号生成**：模型预测每只股票的得分（score）
2. **股票选择**：
   - 从所有股票中选择预测得分最高的 K 只股票（默认 K=50）
   - 随机丢弃 N 只股票（默认 N=5），增加组合多样性
3. **权重分配**：等权重分配资金
4. **调仓频率**：每日调仓

#### 回测配置

```python
PORT_ANALYSIS_CONFIG = {
    "strategy": {
        "topk": 50,      # 选择得分最高的 50 只股票
        "n_drop": 5,     # 随机丢弃 5 只
    },
    "backtest": {
        "start_time": "2025-01-01",
        "end_time": "2025-12-31",
        "account": 100000000,           # 初始资金 1 亿元
        "benchmark": "SH000300",        # 基准：沪深 300 指数
        "exchange_kwargs": {
            "limit_threshold": 0.095,   # 涨跌停限制
            "deal_price": "close",      # 成交价格：收盘价
            "open_cost": 0.0005,        # 买入成本 0.05%
            "close_cost": 0.0015,       # 卖出成本 0.15%
            "min_cost": 5,              # 最低手续费 5 元
        },
    },
}
```

#### 性能指标

回测结果包括以下关键指标：

1. **年化收益率（Annualized Return）**：
   - 不含交易成本的年化收益
   - 包含交易成本的年化收益

2. **夏普比率（Sharpe Ratio）**：
   - 不含交易成本的夏普比率
   - 包含交易成本的夏普比率
   - 计算公式：`Sharpe Ratio = (期望收益 - 无风险利率) / 收益标准差`

3. **超额收益（Excess Return）**：
   - 策略收益相对于基准（沪深 300）的超额部分

## 使用方法

### 环境准备

#### 1. 安装依赖

```bash
# 安装 Qlib 和必要依赖
pip install qlib pandas numpy requests loguru fire

# 或者使用 requirements.txt
pip install -r requirements.txt
```

#### 2. 激活虚拟环境（如果使用）

```bash
source .venv/bin/activate
```

#### 3. 准备基准数据（可选）

如果需要使用 Qlib 的默认 CSI300 股票列表：

```bash
# 下载 Qlib 默认数据
python scripts/get_data.py qlib_data --target_dir ~/.qlib/qlib_data/cn_data --region cn
```

### 快速开始

#### 方式一：完整流程（推荐）

一步完成数据采集、训练和回测：

```bash
cd examples/TencentDataSource

# 运行完整流程
python run_example.py all \
    --start 2020-01-01 \
    --end 2025-12-31 \
    --experiment_name tencent_full_example
```

**输出示例**：
```
================================================================================
FINAL RESULTS:
Annualized Return (without cost): 0.1523
Sharpe Ratio (without cost): 1.2345
Annualized Return (with cost): 0.1234
Sharpe Ratio (with cost): 1.0123
================================================================================
```

#### 方式二：分步执行

如果需要更精细的控制，可以分步执行：

##### 步骤 1：数据采集

```bash
cd examples/TencentDataSource

# 采集数据
python run_example.py collect \
    --start 2020-01-01 \
    --end 2025-12-31 \
    --source_dir ~/.qlib/tencent_data/source \
    --normalize_dir ~/.qlib/tencent_data/normalize \
    --qlib_dir ~/.qlib/tencent_data/qlib_data
```

**过程说明**：
1. 从腾讯 API 下载 CSI300 股票的原始数据
2. 规范化数据格式
3. 转换为 Qlib 二进制格式并保存

**输出位置**：
- 原始数据：`~/.qlib/tencent_data/source`
- 规范化数据：`~/.qlib/tencent_data/normalize`
- Qlib 数据：`~/.qlib/tencent_data/qlib_data`

##### 步骤 2：训练和回测

```bash
# 运行工作流
python run_example.py workflow \
    --qlib_dir ~/.qlib/tencent_data/qlib_data \
    --experiment_name tencent_example \
    --mode code \
    --market csi300
```

**参数说明**：
- `--qlib_dir`: Qlib 数据目录
- `--experiment_name`: 实验名称（用于保存结果）
- `--mode`: 运行模式，"code" 或 "config"
- `--market`: 市场名称，默认 "csi300"

#### 方式三：使用 YAML 配置

可以通过修改 YAML 配置文件来定制参数：

```bash
# 编辑配置文件
vim workflow_config_tencent_alpha158.yaml

# 使用配置文件运行
python run_example.py workflow \
    --qlib_dir ~/.qlib/tencent_data/qlib_data \
    --experiment_name my_experiment \
    --mode config
```

### 高级用法

#### 1. 自定义数据采集参数

在 `config.py` 中修改采集参数：

```python
COLLECTION_CONFIG = {
    "interval": "day",           # 数据频率
    "max_workers": 1,            # 并发工作数（建议 1）
    "max_collector_count": 2,    # 最大重试次数
    "delay": 0,                  # 请求延迟（秒）
    "check_data_length": None,   # 最小数据长度
}
```

#### 2. 自定义训练参数

在 `config.py` 中修改模型参数：

```python
MODEL_CONFIG = {
    "class": "LGBModel",
    "module_path": "qlib.contrib.model.gbdt",
    "kwargs": {
        "loss": "mse",
        "learning_rate": 0.2,     # 调整学习率
        "max_depth": 8,           # 调整树深度
        "num_leaves": 210,        # 调整叶子节点数
        # ... 更多参数
    },
}
```

#### 3. 自定义策略参数

在 `config.py` 中修改策略参数：

```python
PORT_ANALYSIS_CONFIG = {
    "strategy": {
        "kwargs": {
            "topk": 50,      # 修改选股数量
            "n_drop": 5,     # 修改丢弃数量
        },
    },
    "backtest": {
        "exchange_kwargs": {
            "open_cost": 0.0005,   # 修改买入成本
            "close_cost": 0.0015,  # 修改卖出成本
        },
    },
}
```

## 自定义数据源实现详解

本项目展示了如何在 Qlib 中实现自定义数据源的完整流程。这是本示例的核心价值，其他开发者可以参考此实现接入自己的数据源。

### 实现架构

自定义数据源需要实现三个核心类，它们继承自 `data_collector.base` 中的基类：

```python
from data_collector.base import BaseCollector, BaseNormalize, BaseRun

class TencentCollector(BaseCollector):
    """数据采集器"""
    pass

class TencentNormalize(BaseNormalize):
    """数据规范化器"""
    pass

class TencentRun(BaseRun):
    """运行器"""
    pass
```

### 1. BaseCollector - 数据采集器

#### 核心方法

BaseCollector 定义了数据采集的标准接口，子类需要实现以下方法：

##### `get_instrument_list()` - 获取股票列表

```python
def get_instrument_list(self) -> List[str]:
    """
    获取需要采集数据的股票列表
    
    Returns:
        List[str]: 股票代码列表，如 ["sh600000", "sz000001"]
    """
    try:
        import qlib
        qlib.init(provider_uri="~/.qlib/qlib_data/cn_data", region="cn")
        from qlib.data import D
        instruments = D.instruments("csi300")
        return list(instruments)
    except Exception as e:
        logger.warning(f"Failed to load from Qlib: {e}")
        # 降级到硬编码列表
        return ["sh600000", "sz000001", ...]
```

**实现要点**：
- 优先从 Qlib 的工具函数获取标准股票列表
- 如果失败，降级到硬编码的测试列表
- 返回的股票代码需要与 API 格式一致

##### `get_data()` - 获取单只股票数据

```python
def get_data(
    self,
    symbol: str,
    interval: str,
    start_datetime: pd.Timestamp,
    end_datetime: pd.Timestamp,
) -> pd.DataFrame:
    """
    获取单只股票的数据
    
    Parameters:
        symbol: 股票代码
        interval: 数据频率（"day" 或 "1min"）
        start_datetime: 起始时间
        end_datetime: 结束时间
    
    Returns:
        pd.DataFrame: 包含以下列的数据框
            - date: 日期
            - open: 开盘价
            - close: 收盘价
            - high: 最高价
            - low: 最低价
            - volume: 成交量
            - symbol: 股票代码
    """
    # 1. 构造 API 请求
    param_str = f"{symbol},{interval},{start_date_str},{end_date_str},2000,qfq"
    
    # 2. 发起请求（带重试和分页）
    all_data = []
    while fetch_count < max_fetches:
        data = self._fetch_from_api(param_str)
        all_data.extend(data)
        
        # 3. 分页处理
        if len(data) >= 2000:
            # 继续获取更早的数据
            oldest_date = data[0][0]
            current_end_date = pd.Timestamp(oldest_date) - pd.Timedelta(days=1)
        else:
            # 已获取全部数据
            break
    
    # 4. 转换为 DataFrame
    df = pd.DataFrame(all_data, columns=['date', 'open', 'close', 'high', 'low', 'volume', 'amount'])
    df['date'] = pd.to_datetime(df['date'])
    df['symbol'] = symbol
    
    # 5. 过滤和排序
    df = df[(df['date'] >= start_datetime) & (df['date'] <= end_datetime)]
    df = df.sort_values('date').reset_index(drop=True)
    
    return df
```

**实现要点**：
- 必须处理分页逻辑（如果 API 有限制）
- 需要实现重试机制（网络不稳定时）
- 返回的 DataFrame 必须包含指定列
- 日期必须过滤到请求范围内

##### `_fetch_from_api()` - API 请求实现

```python
def _fetch_from_api(self, param_str: str) -> Optional[List]:
    """
    从 API 获取数据（带重试）
    
    Parameters:
        param_str: API 参数字符串
    
    Returns:
        Optional[List]: 数据列表，失败返回 None
    """
    url = f"{self.BASE_URL}?param={param_str}"
    
    for attempt in range(self.RETRY_COUNT):
        try:
            # 发起 HTTP 请求
            response = requests.get(
                url,
                timeout=self.REQUEST_TIMEOUT,
                headers={"User-Agent": "Mozilla/5.0 ..."}
            )
            response.raise_for_status()
            
            # 解析 JSON
            json_data = response.json()
            
            # 提取数据
            data_dict = json_data["data"]
            symbol_key = list(data_dict.keys())[0]
            kline_data = data_dict[symbol_key]["qfqday"]
            
            return kline_data
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on attempt {attempt + 1}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        
        # 延迟后重试
        if attempt < self.RETRY_COUNT - 1:
            time.sleep(self.RETRY_DELAY * (attempt + 1))
    
    return None
```

**实现要点**：
- 必须实现重试机制（网络不稳定）
- 使用适当的超时设置
- 处理各种异常情况
- 添加 User-Agent 避免被拒绝

### 2. BaseNormalize - 数据规范化器

#### 核心方法

##### `normalize()` - 数据规范化

```python
def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
    """
    规范化数据到 Qlib 标准格式
    
    Parameters:
        df: 原始数据
    
    Returns:
        pd.DataFrame: 规范化后的数据
    """
    if df.empty:
        return df
    
    df = df.copy()
    
    # 1. 设置日期索引
    df = df.set_index("date")
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    
    # 2. 转换数值类型
    numeric_cols = ["open", "close", "high", "low", "volume", "amount"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    
    # 3. 去重
    df = df[~df.index.duplicated(keep="first")]
    
    # 4. 重新索引到交易日历（可选）
    if self.calendar_list is not None:
        df = df.reindex(self.calendar_list)
    
    # 5. 处理缺失值
    # 成交量缺失设为 0
    df["volume"] = df["volume"].fillna(0)
    
    # 价格字段前向填充，后向填充
    price_cols = ["open", "close", "high", "low"]
    for col in price_cols:
        df[col] = df[col].ffill().bfill()
    
    # 6. 计算收益率
    df["change"] = df["close"].pct_change()
    df["change"] = df["change"].replace([float("inf"), -float("inf")], np.nan).fillna(0)
    
    # 7. 重置索引
    df = df.reset_index()
    df.rename(columns={"index": "date"}, inplace=True)
    
    return df
```

**实现要点**：
- 必须处理日期索引
- 必须转换数值类型
- 必须处理缺失值
- 价格字段使用 ffill/bfill
- 计算收益率（可选）

### 3. BaseRun - 运行器

#### 核心方法

##### `download_data()` - 下载数据

```python
def download_data(
    self,
    start,
    end,
    max_collector_count=2,
    delay=0,
):
    """
    下载所有股票的数据
    
    Parameters:
        start: 起始日期
        end: 结束日期
        max_collector_count: 最大重试次数
        delay: 请求延迟
    """
    # 1. 获取股票列表
    instruments = self.get_instrument_list()
    
    # 2. 遍历每只股票
    for symbol in instruments:
        try:
            # 3. 获取数据
            df = self.get_data(
                symbol=symbol,
                interval=self.interval,
                start_datetime=pd.Timestamp(start),
                end_datetime=pd.Timestamp(end),
            )
            
            # 4. 保存数据
            if not df.empty:
                file_path = self.source_dir / f"{symbol}.csv"
                df.to_csv(file_path, index=False)
                logger.info(f"Saved {len(df)} records to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to process {symbol}: {e}")
```

##### `normalize_data()` - 规范化数据

```python
def normalize_data(
    self,
    date_field_name: str = "date",
    symbol_field_name: str = "symbol",
):
    """
    规范化所有股票的数据
    
    Parameters:
        date_field_name: 日期字段名
        symbol_field_name: 股票代码字段名
    """
    # 1. 获取所有数据文件
    csv_files = list(self.source_dir.glob("*.csv"))
    
    # 2. 遍历每个文件
    for csv_file in csv_files:
        try:
            # 3. 读取数据
            df = pd.read_csv(csv_file)
            
            # 4. 规范化
            normalized_df = self.normalize(df)
            
            # 5. 保存
            output_path = self.normalize_dir / csv_file.name
            normalized_df.to_csv(output_path, index=False)
            
        except Exception as e:
            logger.error(f"Failed to normalize {csv_file}: {e}")
```

### 接入新数据源的步骤

如果要接入其他数据源（如 Yahoo Finance、Wind、Tushare 等），需要：

#### 步骤 1：创建新的采集器类

```python
# my_data_source.py
from data_collector.base import BaseCollector, BaseNormalize, BaseRun

class MyCollector(BaseCollector):
    """自定义数据采集器"""
    
    BASE_URL = "https://api.example.com/data"
    
    def get_instrument_list(self) -> List[str]:
        """实现股票列表获取逻辑"""
        # 调用你的 API 获取股票列表
        return ["symbol1", "symbol2", ...]
    
    def get_data(self, symbol, interval, start_datetime, end_datetime):
        """实现数据获取逻辑"""
        # 1. 构造 API 请求
        # 2. 发起 HTTP 请求
        # 3. 解析响应
        # 4. 返回 DataFrame
        pass
    
    def _fetch_from_api(self, param_str):
        """实现 API 调用"""
        # 实现 HTTP 请求和重试逻辑
        pass

class MyNormalize(BaseNormalize):
    """自定义数据规范化器"""
    
    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """实现数据规范化逻辑"""
        # 1. 设置日期索引
        # 2. 转换数值类型
        # 3. 处理缺失值
        # 4. 计算收益率
        pass

class MyRun(BaseRun):
    """自定义运行器"""
    
    @property
    def default_base_dir(self):
        """默认数据目录"""
        return Path(__file__).parent
    
    @property
    def collector_class_name(self):
        """采集器类名"""
        return "MyCollector"
    
    @property
    def normalize_class_name(self):
        """规范化器类名"""
        return "MyNormalize"
```

#### 步骤 2：适配数据格式

确保返回的 DataFrame 包含以下列：

- `date`: 日期
- `open`: 开盘价
- `close`: 收盘价
- `high`: 最高价
- `low`: 最低价
- `volume`: 成交量
- `amount`: 成交额（可选）

#### 步骤 3：测试数据采集

```python
# 测试数据采集
run = MyRun()
run.download_data(start="2024-01-01", end="2024-12-31")
```

#### 步骤 4：测试数据规范化

```python
# 测试数据规范化
run.normalize_data(
    date_field_name="date",
    symbol_field_name="symbol",
)
```

#### 步骤 5：转换为 Qlib 格式

```python
# 转换为 Qlib 二进制格式
from scripts.dump_bin import DumpDataAll

dumper = DumpDataAll(
    data_path="normalize",
    qlib_dir="qlib_data",
    freq="day",
    date_field_name="date",
    symbol_field_name="symbol",
    include_fields="open,close,high,low,volume,amount,change",
)
dumper.dump()
```

#### 步骤 6：运行工作流

```python
# 使用自定义数据运行工作流
import qlib
from qlib.workflow import R

qlib.init(provider_uri="qlib_data", region="cn")

# 运行你的工作流
# ...
```

### 关键注意事项

1. **日期格式**：确保日期转换为 Pandas Timestamp
2. **数值类型**：价格、成交量等必须转换为数值类型
3. **缺失值处理**：价格字段使用 ffill/bfill，成交量设为 0
4. **错误处理**：每个 API 调用都需要 try-except 包裹
5. **重试机制**：网络不稳定时必须实现重试
6. **日志记录**：记录关键步骤和错误信息
7. **性能优化**：使用适当的并发数（不要过高以免被封）

## 配置说明

### 时间周期配置

在 `config.py` 中配置时间周期：

```python
TIME_CONFIG = {
    "train_start": "2020-01-01",  # 训练起始日期
    "train_end": "2024-12-31",    # 训练结束日期
    "test_start": "2025-01-01",   # 测试起始日期
    "test_end": "2025-12-31",     # 测试结束日期
    "data_start": "2020-01-01",   # 数据起始日期
    "data_end": "2025-12-31",     # 数据结束日期
}
```

### 模型配置

```python
MODEL_CONFIG = {
    "class": "LGBModel",
    "module_path": "qlib.contrib.model.gbdt",
    "kwargs": {
        "loss": "mse",
        "learning_rate": 0.2,
        "subsample": 0.8789,
        "lambda_l1": 205.6999,
        "lambda_l2": 580.9768,
        "max_depth": 8,
        "num_leaves": 210,
        "num_threads": 20,
    },
}
```

### 策略配置

```python
PORT_ANALYSIS_CONFIG = {
    "strategy": {
        "class": "TopkDropoutStrategy",
        "module_path": "qlib.contrib.strategy",
        "kwargs": {
            "signal": "<PRED>",
            "topk": 50,      # 选股数量
            "n_drop": 5,     # 丢弃数量
        },
    },
    "backtest": {
        "start_time": "2025-01-01",
        "end_time": "2025-12-31",
        "account": 100000000,  # 初始资金
        "benchmark": "SH000300",  # 基准
        "exchange_kwargs": {
            "limit_threshold": 0.095,
            "deal_price": "close",
            "open_cost": 0.0005,
            "close_cost": 0.0015,
            "min_cost": 5,
        },
    },
}
```

## 常见问题

### 1. data_collector 导入失败

**问题**：
```
ModuleNotFoundError: No module named 'data_collector'
```

**解决方案**：

确保 `scripts/data_collector/__init__.py` 存在：

```bash
ls -l /path/to/qlib/scripts/data_collector/__init__.py
```

如果不存在，需要创建该文件（已在本项目中创建）。

### 2. API 请求超时

**问题**：
```
Timeout on attempt 1 for URL: ...
```

**解决方案**：

1. 增加超时时间：
```python
REQUEST_TIMEOUT = 60  # 增加到 60 秒
```

2. 增加重试次数：
```python
RETRY_COUNT = 5  # 增加到 5 次
```

3. 添加延迟：
```python
RETRY_DELAY = 2  # 每次重试延迟 2 秒
```

### 3. 数据不完整

**问题**：
部分股票的数据少于预期。

**解决方案**：

1. 检查股票代码是否正确
2. 检查日期范围是否合理
3. 检查 API 是否有限制
4. 增加日志输出：
```python
logger.info(f"Symbol: {symbol}, Records: {len(df)}")
```

### 4. 内存不足

**问题**：
处理大量股票时内存不足。

**解决方案**：

1. 减少并发数：
```python
max_workers = 1  # 串行处理
```

2. 限制处理的股票数量：
```python
limit_nums = 10  # 只处理前 10 只
```

3. 分批处理：
```python
# 分批处理 50 只
batches = [instruments[i:i+50] for i in range(0, len(instruments), 50)]
for batch in batches:
    process_batch(batch)
```

### 5. 模型训练失败

**问题**：
```
ValueError: Input contains NaN, infinity or a value too large for dtype('float32')
```

**解决方案**：

1. 检查数据中是否有缺失值或异常值
2. 确保数据规范化正确
3. 增加日志检查数据：
```python
logger.info(f"Data shape: {df.shape}")
logger.info(f"Missing values: {df.isnull().sum()}")
```

## 日志说明

本项目使用 `loguru` 提供详细的日志记录：

### 日志级别

- **INFO**: 正常的进度更新和关键事件
- **DEBUG**: 详细的调试信息
- **WARNING**: 非关键问题（如失败的请求）
- **ERROR**: 严重错误

### 日志示例

```
2024-01-01 10:00:00 | INFO | Initializing TencentCollector with save_dir=...
2024-01-01 10:00:01 | INFO | Getting instrument list from CSI300 pool
2024-01-01 10:00:02 | INFO | Loaded 300 instruments from Qlib CSI300
2024-01-01 10:00:03 | INFO | Fetching data for sh600000 from 2020-01-01 to 2025-12-31
2024-01-01 10:00:04 | INFO | Fetched 2000 records for sh600000 (total: 2000)
2024-01-01 10:00:05 | INFO | Reached 2000 record limit, fetching more data before 2020-12-31
2024-01-01 10:00:06 | INFO | Finished fetching data for sh600000: 1523 records total
```

### 调试技巧

1. **查看详细日志**：
```python
logger.remove()
logger.add(sys.stdout, level="DEBUG")
```

2. **保存日志到文件**：
```python
logger.add("debug.log", level="DEBUG", rotation="10 MB")
```

3. **只看错误**：
```python
logger.add(sys.stdout, filter=lambda record: record["level"].name == "ERROR")
```

## 参考资源

### Qlib 官方文档

- [Qlib GitHub](https://github.com/microsoft/qlib)
- [Qlib 文档](https://qlib.readthedocs.io/)
- [Alpha158 说明](https://qlib.readthedocs.io/en/latest/component/data.html#alpha158)

### 腾讯股票 API

- [API 基础 URL](https://web.ifzq.gtimg.cn/appstock/app/fqkline/get)
- 支持日线、周线、月线数据
- 支持前复权、后复权、不复权价格

### 相关项目

- [Qlib Yahoo DataSource](https://github.com/microsoft/qlib/tree/main/examples/yahoo_collector)
- [Qlib CN Index DataSource](https://github.com/microsoft/qlib/tree/main/examples/cn_index_collector)

## 许可证

Copyright (c) Microsoft Corporation. Licensed under the MIT License.

## Quick Start

### Prerequisites

1. Install Qlib and dependencies:
```bash
pip install qlib pandas numpy requests loguru fire
```

2. (Optional) Ensure you have Qlib's default data for CSI300 (for stock list):
```bash
python scripts/get_data.py qlib_data --target_dir ~/.qlib/qlib_data/cn_data --region cn
```

### Using .venv Environment

Activate your virtual environment before running:
```bash
source .venv/bin/activate
```

### Complete Pipeline

Run the complete pipeline with a single command:

```bash
cd examples/TencentDataSource

# Collect data + train + backtest
python run_example.py all \
    --start 2020-01-01 \
    --end 2025-12-31 \
    --experiment_name tencent_full_example
```

### Step-by-Step Execution

#### Step 1: Collect Data

```bash
cd examples/TencentDataSource

# Download data for CSI300 stocks
python run_example.py collect \
    --start 2020-01-01 \
    --end 2025-12-31
```

This will:
- Download data from Tencent's HTTP API
- Normalize data
- Convert to Qlib binary format
- Save to `~/.qlib/tencent_data/qlib_data`

#### Step 2: Run Training and Backtesting

```bash
# Run workflow with collected data
python run_example.py workflow \
    --qlib_dir ~/.qlib/tencent_data/qlib_data \
    --experiment_name tencent_example \
    --mode code
```

## Output Results

The workflow automatically outputs following performance metrics:

1. **Annualized Return (without cost)**: Yearly return excluding transaction costs
2. **Sharpe Ratio (without cost)**: Risk-adjusted return without transaction costs
3. **Annualized Return (with cost)**: Yearly return including transaction costs
4. **Sharpe Ratio (with cost)**: Risk-adjusted return including transaction costs

**Example Output**:
```
================================================================================
FINAL RESULTS:
Annualized Return (without cost): 0.1523
Sharpe Ratio (without cost): 1.2345
Annualized Return (with cost): 0.1234
Sharpe Ratio (with cost): 1.0123
================================================================================
```

## Configuration

All parameters are configured in `config.py`:

### Time Periods

- **Training Period**: 2020-01-01 to 2024-12-31
- **Testing Period**: 2025-01-01 to 2025-12-31

### Model Configuration (LightGBM)

- **Loss**: MSE (Mean Squared Error)
- **Learning Rate**: 0.2
- **Max Depth**: 8
- **Number of Leaves**: 210

### Portfolio Strategy

- **Strategy**: TopkDropoutStrategy
- **Top K**: 50 stocks
- **Dropout**: 5 stocks
- **Initial Capital**: 100,000,000 (100 million)
- **Trading Cost**: Buy 0.05%, Sell 0.15%

## API Details

### Tencent Stock Data API

**Base URL**: `https://web.ifzq.gtimg.cn/appstock/app/fqkline/get`

**Parameters**:
- `param`: Format `{symbol},{interval},{start},{end},{count},{qfq}`
  - `symbol`: Stock code (e.g., "sh600000" or "sz000001")
  - `interval`: "day" for daily data
  - `start`: Start date (e.g., "2024-01-01")
  - `end`: End date (e.g., "2025-12-31")
  - `count`: Max records per request (max 2000)
  - `qfq`: "qfq" for forward-adjusted prices

**Example Request**:
```
https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh600000,day,2024-01-01,2025-12-31,2000,qfq
```

**Response Format**:
```json
{
  "data": {
    "sh600000": {
      "qfqday": [
        ["2025-01-02", "10.50", "10.60", "10.70", "10.45", "1000000", "10500000"],
        ...
      ]
    }
  }
}
```

Each record: `[date, open, close, high, low, volume, amount]`

## Pagination Logic

The Tencent API limits to 2000 records per request. The collector automatically handles pagination:

1. Fetch up to 2000 records with latest end date
2. If exactly 2000 records returned, there may be more data
3. Use the oldest date from current batch as new end date
4. Repeat until fewer than 2000 records returned

**Example**:
```python
# For data spanning 3000 trading days:
# Request 1: 2020-01-01 to 2025-12-31, count=2000
# Result: Gets latest 2000 records (2021-01-01 to 2025-12-31)
# Request 2: 2020-01-01 to 2020-12-31, count=2000
# Result: Gets remaining 1000 records (2020-01-01 to 2020-12-31)
# Total: 3000 records
```

## Import Fix

This example now correctly imports `data_collector.base` from Qlib's scripts directory.

See [IMPORT_FIX_SUMMARY.md](IMPORT_FIX_SUMMARY.md) for detailed information about the fix.

## Logging

Comprehensive logging is implemented throughout the workflow:

- **INFO**: Progress updates and key events
- **DEBUG**: Detailed debugging information
- **WARNING**: Non-critical issues (e.g., failed requests)
- **ERROR**: Critical errors

## License

Copyright (c) Microsoft Corporation. Licensed under the MIT License.
