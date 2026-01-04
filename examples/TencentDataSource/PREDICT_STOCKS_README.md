# 股票预测功能使用说明

## 功能概述

`predict_stocks.py` 提供了基于 `a500.csv` 中股票列表的预测功能，支持：

- ✅ 单个日期预测
- ✅ 多个日期预测
- ✅ 日期段预测
- ✅ 最近N天预测
- ✅ 多进程并行处理（默认8个进程）
- ✅ 自动防止数据泄露
- ✅ 预测结果保存为 CSV 文件

## 核心特性

### 1. 防止数据泄露
- 训练数据严格截止到最早预测日期的前一天
- 特征计算不包含预测日期之后的数据
- 确保预测结果的真实性和可靠性

### 2. 多进程并行处理
- 默认8个进程并行处理500只股票
- 充分利用多核 CPU
- 显著提升预测速度
- 支持自定义进程数

### 3. 灵活的日期选择
支持四种日期模式，满足不同需求场景

## 安装依赖

```bash
# 确保已安装所需的包
pip install fire pandas numpy loguru

# Qlib 和模型依赖应该已经安装
pip install pyqlib lightgbm xgboost catboost torch
```

## 使用方法

### 基本用法

#### 1. 使用最后一天预测（默认）

```bash
python predict_stocks.py
```

**说明：**
- 自动使用数据中最后一个交易日
- 使用8个进程并行处理
- 结果保存到 `predictions.csv`

#### 2. 指定单个日期

```bash
python predict_stocks.py --dates 2024-12-31
```

**说明：**
- 预测指定日期（必须是交易日）
- 训练数据截止到该日期的前一天
- 结果保存到 `predictions.csv`

#### 3. 指定多个日期

```bash
python predict_stocks.py --dates "2024-12-30,2024-12-31,2025-01-02"
```

**说明：**
- 可以指定多个日期（逗号分隔）
- 自动过滤非交易日
- 训练数据截止到最早预测日期的前一天

#### 4. 指定日期段

```bash
python predict_stocks.py --start_date 2024-12-01 --end_date 2024-12-31
```

**说明：**
- 预测指定时间段内的所有交易日
- 适用于回测或批量预测
- 训练数据截止到时间段开始的前一天

#### 5. 指定最近N个交易日

```bash
python predict_stocks.py --last_n_days 5
```

**说明：**
- 预测最近的N个交易日
- 常用于实时预测场景
- 训练数据截止到最早预测日期的前一天

### 高级用法

#### 1. 自定义进程数

```bash
# 使用4个进程（低资源消耗）
python predict_stocks.py --num_processes 4

# 使用16个进程（高性能）
python predict_stocks.py --num_processes 16

# 自动检测最优进程数（使用所有CPU核心）
python predict_stocks.py --num_processes auto

# 单进程顺序处理（调试模式）
python predict_stocks.py --num_processes 1
```

**性能对比（500只股票 × 5个日期）：**
| 进程数 | 预计时间 | 适用场景 |
|--------|----------|----------|
| 1 | 10-15 分钟 | 调试、低内存 |
| 4 | 3-5 分钟 | 平衡性能和资源 |
| 8 | 2-3 分钟 | 默认配置 |
| 16 | 1-2 分钟 | 高性能服务器 |

#### 2. 自定义输出路径

```bash
python predict_stocks.py --output_path my_predictions.csv
python predict_stocks.py --output_path ./results/pred_202412.csv
```

#### 3. 指定数据目录

```bash
python predict_stocks.py --provider_uri ~/.qlib/tencent_data/qlib_data
python predict_stocks.py --provider_uri /path/to/qlib_data
```

#### 4. 组合使用

```bash
# 日期段 + 高性能 + 自定义输出
python predict_stocks.py \
    --start_date 2024-12-01 \
    --end_date 2024-12-31 \
    --num_processes 16 \
    --output_path dec_2024_high_perf.csv \
    --provider_uri ~/.qlib/tencent_data/qlib_data

# 最近5天 + 自动检测进程 + 自定义输出
python predict_stocks.py \
    --last_n_days 5 \
    --num_processes auto \
    --output_path recent_5days.csv

# 多个日期 + 低资源 + 自定义输出
python predict_stocks.py \
    --dates "2024-12-29,2024-12-30,2024-12-31" \
    --num_processes 4 \
    --output_path year_end_predictions.csv
```

## 命令行参数

| 参数 | 简写 | 类型 | 默认值 | 说明 |
|------|--------|--------|--------|
| `--csv_path` | `-c` | str | `a500.csv` | 股票列表CSV文件路径 |
| `--dates` | `-d` | str | `None` | 单个或多个日期（逗号分隔） |
| `--start_date` | `-s` | str | `None` | 日期段开始日期 |
| `--end_date` | `-e` | str | `None` | 日期段结束日期 |
| `--last_n_days` | `-l` | int | `None` | 最近N个交易日 |
| `--num_processes` | `-n` | int | `8` | 进程数（1或更多，或'auto'） |
| `--output_path` | `-o` | str | `predictions.csv` | 输出CSV文件路径 |
| `--provider_uri` | `-p` | str | `~/.qlib/tencent_data/qlib_data` | Qlib数据目录路径 |
| `--experiment_name` | | str | `stock_prediction` | 实验名称（用于日志） |

**日期参数优先级：**
1. `--dates`：指定特定日期
2. `--start_date` 和 `--end_date`：指定日期段
3. `--last_n_days`：指定最近N天
4. 无参数：使用最后一天

## 输出文件格式

预测结果保存为 CSV 文件，包含以下列：

### 单日期预测

```csv
date,stock_code,stock_name,prediction
2024-12-31,sz000001,平安银行,0.0234
2024-12-31,sz000002,万科A,0.0189
2024-12-31,sh600000,平安银行,0.0456
...
```

### 多日期预测

```csv
date,stock_code,stock_name,prediction
2024-12-01,sz000001,平安银行,0.0234
2024-12-01,sz000002,万科A,0.0189
2024-12-01,sh600000,平安银行,0.0456
2024-12-02,sz000001,平安银行,0.0245
2024-12-02,sz000002,万科A,0.0198
2024-12-02,sh600000,平安银行,0.0467
...
```

**排序规则：**
- 按 `date` 升序排列
- 同一日期内按 `stock_code` 升序排列

## 使用场景示例

### 场景1：实时预测

每天收盘后预测第二天：

```bash
# 创建定时任务脚本
#!/bin/bash
# daily_predict.sh

cd /Users/abc/workspace/qlib/examples/TencentDataSource

# 预测最近1个交易日（今天）
python predict_stocks.py \
    --last_n_days 1 \
    --output_path "predictions_$(date +%Y%m%d).csv"
```

**使用 cron 每天自动运行：**
```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天18:00运行）
0 18 * * * /path/to/daily_predict.sh >> /path/to/predict.log 2>&1
```

### 场景2：历史回测

预测历史某个月份的所有交易日：

```bash
# 预测2024年12月所有交易日
python predict_stocks.py \
    --start_date 2024-12-01 \
    --end_date 2024-12-31 \
    --output_path predictions_202412.csv
```

### 场景3：批量预测关键日期

预测关键时间点：

```bash
# 预测年末最后几个交易日
python predict_stocks.py \
    --dates "2024-12-27,2024-12-30,2024-12-31" \
    --output_path year_end_predictions.csv
```

### 场景4：高性能批量处理

使用服务器多核CPU加速：

```bash
# 使用所有CPU核心进行大规模预测
python predict_stocks.py \
    --start_date 2024-01-01 \
    --end_date 2024-12-31 \
    --num_processes auto \
    --output_path full_year_predictions.csv
```

### 场景5：低资源模式

在资源受限的环境运行：

```bash
# 使用单进程，降低内存消耗
python predict_stocks.py \
    --last_n_days 1 \
    --num_processes 1 \
    --output_path prediction.csv
```

## 注意事项

### 1. 数据泄露防护

本功能内置严格的数据泄露防护：
- ✅ 训练数据不包含任何预测日期
- ✅ 特征计算使用历史数据
- ✅ 日期验证确保只使用交易日

**警告：** 不要修改 `train_end_date` 的计算逻辑，否则可能导致预测结果不准确。

### 2. 日期格式

- 日期格式：`YYYY-MM-DD`（例如：2024-12-31）
- 必须是交易日（会在 calendar 中验证）
- 非交易日会被自动跳过并记录警告

### 3. 股票代码

- a500.csv 中的代码会自动标准化
- 上海：sh + 6位代码（例如：sh600000）
- 深圳：sz + 6位代码（例如：sz000001）
- 未知格式的代码会被跳过并记录警告

### 4. 性能优化

**进程数选择建议：**
- 4核CPU：使用4进程
- 8核CPU：使用8进程（默认）
- 16核CPU：使用16进程
- 更多核心：使用 `--num_processes auto`

**内存管理：**
- 500只股票 × 多日期会占用较多内存
- 如果内存不足，减少进程数
- 或分批次预测不同时间段

### 5. 错误处理

常见错误及解决方案：

| 错误 | 原因 | 解决方案 |
|------|--------|----------|
| `CSV file not found` | a500.csv 不存在 | 确认文件路径正确 |
| `No valid dates provided` | 指定的日期都不是交易日 | 使用正确的交易日日期 |
| `No trading days in date range` | 日期段内没有交易日 | 检查日期范围是否有效 |
| `No trading day available before...` | 最早的预测日期之前没有足够的历史数据 | 使用更晚的预测日期 |
| `Model training failed` | 训练数据不足或配置错误 | 检查数据是否足够训练模型 |

## 测试

运行单元测试验证功能：

```bash
# 运行所有单元测试
python test_predict_stocks.py
```

测试包括：
- ✅ 股票列表加载
- ✅ 股票名称映射
- ✅ 批次划分
- ✅ 进程数优化

## 性能基准

基于500只股票的预测性能：

| 场景 | 日期数 | 进程数 | 预计时间 |
|------|--------|----------|----------|
| 单日预测 | 1 | 1 | 2-3 分钟 |
| 单日预测 | 1 | 8 | 30-60 秒 |
| 单日预测 | 1 | 16 | 20-40 秒 |
| 月度预测 | ~20 | 1 | 10-15 分钟 |
| 月度预测 | ~20 | 8 | 2-3 分钟 |
| 月度预测 | ~20 | 16 | 1-2 分钟 |

**说明：** 实际时间取决于硬件配置和数据量。

## 集成到现有工作流

可以将预测功能集成到 `run_example.py`：

```python
# 在 run_example.py 中添加
from predict_stocks import main as predict_main

def predict(
    csv_path: str = "a500.csv",
    dates: str = None,
    start_date: str = None,
    end_date: str = None,
    last_n_days: int = None,
    num_processes: int = 8,
    output_path: str = "predictions.csv",
    provider_uri: str = "~/.qlib/tencent_data/qlib_data",
):
    """
    运行股票预测
    """
    predict_main(
        csv_path=csv_path,
        dates=dates,
        start_date=start_date,
        end_date=end_date,
        last_n_days=last_n_days,
        num_processes=num_processes,
        output_path=output_path,
        provider_uri=provider_uri,
    )

# 添加到 fire.Fire
if __name__ == "__main__":
    fire.Fire({
        "collect": collect_data,
        "workflow": run_workflow,
        "all": run_all,
        "predict": predict,  # 新增
    })
```

使用方式：
```bash
# 通过 run_example.py 调用
python run_example.py predict \
    --last_n_days 5 \
    --num_processes 8 \
    --output_path predictions.csv
```

## 故障排除

### 问题1：进程卡住或无响应

**症状：** 程序运行但没有输出

**可能原因：**
- 临时文件权限问题
- qlib 初始化问题

**解决方案：**
```bash
# 使用单进程模式调试
python predict_stocks.py --num_processes 1 --dates 2024-12-31

# 检查临时目录权限
ls -la /tmp/
```

### 问题2：预测结果为空

**症状：** 输出的 CSV 文件为空或只有表头

**可能原因：**
- 指定的日期都不是交易日
- 股票数据缺失

**解决方案：**
```bash
# 检查数据中的可用日期
python -c "
import qlib
qlib.init(provider_uri='~/.qlib/tencent_data/qlib_data', region='cn')
from qlib.data import D
calendar = D.calendar()
print('Last 10 trading days:', calendar[-10:])
"

# 使用有效的交易日
python predict_stocks.py --dates "2024-12-30,2024-12-31"
```

### 问题3：内存不足

**症状：** 程序崩溃或系统响应缓慢

**可能原因：**
- 进程数过多
- 日期范围过大

**解决方案：**
```bash
# 减少进程数
python predict_stocks.py --start_date 2024-12-01 --end_date 2024-12-10 --num_processes 4

# 分批预测
# 先预测12月前半月，再预测后半月
python predict_stocks.py --start_date 2024-12-01 --end_date 2024-12-15 --output_path dec_first_half.csv
python predict_stocks.py --start_date 2024-12-16 --end_date 2024-12-31 --output_path dec_second_half.csv
```

## 总结

`predict_stocks.py` 提供了一个强大、灵活、高效的股票预测工具：

✅ **功能完整**：支持多种日期模式
✅ **防止数据泄露**：严格的时序控制
✅ **高性能**：多进程并行处理
✅ **易用性**：简洁的命令行接口
✅ **灵活性**：可自定义各种参数
✅ **可靠性**：完善的错误处理和日志

现在就可以开始使用这个工具进行股票预测了！
