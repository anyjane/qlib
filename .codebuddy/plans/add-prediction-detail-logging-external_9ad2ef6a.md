---
name: add-prediction-detail-logging-external
overview: 在examples/TencentDataSource目录下添加详细的预测日志输出功能，通过配置开关控制是否记录每个交易日的预测详情（日期、预测分数统计、TopK股票、持仓信息、买卖信号）。
todos:
  - id: explore-codebase
    content: 使用[code-explorer]探索examples/TencentDataSource目录结构和现有代码
    status: completed
  - id: create-logger-module
    content: 创建prediction_logger.py模块实现日志记录功能
    status: completed
    dependencies:
      - explore-codebase
  - id: add-config-switch
    content: 在config.py中添加日志配置开关参数
    status: completed
    dependencies:
      - explore-codebase
  - id: integrate-logging
    content: 在workflow.py中集成日志记录功能
    status: completed
    dependencies:
      - create-logger-module
      - add-config-switch
  - id: test-logging
    content: 测试日志输出功能和配置开关有效性
    status: completed
    dependencies:
      - integrate-logging
---

## 产品概述

在examples/TencentDataSource目录下实现可配置的详细预测日志输出功能，支持记录每个交易日的预测详情信息。

## 核心功能

- 添加配置开关控制日志输出
- 记录交易日期信息
- 记录预测分数统计数据
- 记录TopK股票列表
- 记录持仓信息
- 记录买卖信号
- 仅在examples/TencentDataSource目录下修改，不修改qlib核心代码

## 技术栈

- Python（qlib项目基于Python）
- 日志记录：Python标准logging模块

## 技术架构

### 系统架构

在examples/TencentDataSource目录下添加独立的日志模块，通过配置参数控制是否启用详细日志记录。

### 模块划分

- **配置模块**: 添加配置参数控制日志开关
- **日志记录模块**: 实现预测详情的日志输出逻辑
- **数据收集模块**: 在预测过程中收集需要记录的数据

### 数据流

配置读取 → 判断日志开关 → 预测执行 → 数据收集 → 格式化输出 → 日志写入

## 实现细节

### 核心目录结构

```
examples/TencentDataSource/
├── prediction_logger.py  # 新增：预测日志记录模块
├── config.py             # 修改：添加日志配置开关
└── workflow.py           # 修改：集成日志记录功能
```

### 关键代码结构

**配置参数定义**: 控制日志开关和详细程度

```python
# 配置参数
ENABLE_PREDICTION_LOG = True  # 是否启用预测日志
LOG_TOP_K = 10                # 记录TopK股票数量
```

**PredictionLogger类**: 负责格式化和输出预测详情

```python
class PredictionLogger:
    def __init__(self, enabled: bool = False)
    def log_prediction(self, date: str, scores: Dict, topk: List, position: Dict, signals: List)
```

### 技术实施计划

1. **问题陈述**: 需要在预测过程中记录详细的交易信息，但不影响qlib核心逻辑
2. **解决方案**: 在examples目录下创建独立的日志模块，通过装饰器或回调函数集成到现有流程
3. **关键技术**: Python logging模块、装饰器模式、配置管理
4. **实施步骤**:

- 创建prediction_logger.py模块
- 在config.py中添加配置开关
- 在workflow.py中集成日志记录
- 测试日志输出格式和完整性

5. **测试策略**: 验证开关功能、日志格式准确性、数据完整性

### 集成点

- 与workflow.py集成：在预测回调中触发日志记录
- 与config.py集成：读取配置开关
- 数据格式：使用JSON格式记录结构化数据，便于后续分析

## Agent Extensions

### SubAgent

- **code-explorer**
- Purpose: 探索examples/TencentDataSource目录下的现有代码结构
- Expected outcome: 了解workflow.py和config.py的当前实现，确定最佳的日志集成点