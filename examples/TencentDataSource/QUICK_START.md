# 股票预测功能快速开始指南

## 5分钟快速开始

### 步骤1：确认依赖（1分钟）

```bash
# 检查是否已安装所需依赖
python -c "import qlib, pandas, numpy, fire, loguru; print('All dependencies OK')"
```

如果提示错误，运行：
```bash
pip install fire pandas numpy loguru
pip install pyqlib lightgbm xgboost catboost torch
```

### 步骤2：运行单元测试（1分钟）

```bash
cd /Users/abc/workspace/qlib/examples/TencentDataSource
python test_predict_stocks.py
```

预期输出：
```
TEST SUMMARY
✓ PASSED: Load stock list
✓ PASSED: Load stock names
✓ PASSED: Split batches
✓ PASSED: Optimize processes

Total: 4/4 tests passed
```

### 步骤3：运行首次预测（3分钟）

```bash
# 使用最后一天预测（默认8进程）
python predict_stocks.py
```

预期输出：
```
================================================================================
STOCK PREDICTION FUNCTION
================================================================================
INFO: Loading stock list from a500.csv
INFO: Loaded 461 stocks from a500.csv
INFO: Loading stock names map from a500.csv
INFO: Loaded 461 stock names from a500.csv
INFO: No date specified, using last trading day
INFO: Training data will end at 2024-12-30
INFO: Training model for prediction...
INFO: Model trained successfully using data until 2024-12-30
INFO: Starting parallel prediction with 8 processes
INFO: Parallel prediction completed: 461 total predictions
INFO: Saving predictions to predictions.csv
================================================================================
PREDICTION COMPLETED SUCCESSFULLY
Total predictions: 461
Output file: predictions.csv
================================================================================
```

### 步骤4：查看预测结果（30秒）

```bash
# 查看前10行预测结果
head -20 predictions.csv

# 使用 Excel 查看（可选）
open predictions.csv  # macOS
# 或
start predictions.csv  # Windows
```

预期输出格式：
```csv
date,stock_code,stock_name,prediction
2024-12-31,sz000001,平安银行,0.0234
2024-12-31,sz000002,万科A,0.0189
...
```

## 常用命令速查

### 基本命令

| 需求 | 命令 |
|--------|--------|
| 使用最后一天预测 | `python predict_stocks.py` |
| 指定单个日期 | `python predict_stocks.py --dates 2024-12-31` |
| 指定多个日期 | `python predict_stocks.py --dates "2024-12-30,2024-12-31"` |
| 指定日期段 | `python predict_stocks.py --start_date 2024-12-01 --end_date 2024-12-31` |
| 最近5天 | `python predict_stocks.py --last_n_days 5` |

### 进程数控制

| 场景 | 命令 |
|--------|--------|
| 低资源（4进程） | `python predict_stocks.py --num_processes 4` |
| 默认（8进程） | `python predict_stocks.py --num_processes 8` |
| 高性能（16进程） | `python predict_stocks.py --num_processes 16` |
| 自动检测 | `python predict_stocks.py --num_processes auto` |

### 输出控制

| 需求 | 命令 |
|--------|--------|
| 自定义输出路径 | `python predict_stocks.py --output_path my_predictions.csv` |
| 自定义数据目录 | `python predict_stocks.py --provider_uri /path/to/qlib_data` |

## 实际使用场景

### 场景1：每日收盘后预测明天

```bash
# 创建预测脚本
cat > daily_predict.sh << 'EOF'
#!/bin/bash
cd /Users/abc/workspace/qlib/examples/TencentDataSource
python predict_stocks.py \
    --last_n_days 1 \
    --output_path "predictions_$(date +%Y%m%d).csv"
EOF

chmod +x daily_predict.sh

# 运行
./daily_predict.sh
```

**设置定时任务（可选）：**
```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天18:00运行）
0 18 * * * /Users/abc/workspace/qlib/examples/TencentDataSource/daily_predict.sh >> predict.log 2>&1
```

### 场景2：批量预测历史月份

```bash
# 预测2024年12月所有交易日
python predict_stocks.py \
    --start_date 2024-12-01 \
    --end_date 2024-12-31 \
    --output_path predictions_202412.csv
```

**预计时间：** 2-3 分钟（8进程）

### 场景3：高性能批量预测

```bash
# 使用所有CPU核心进行大规模预测
python predict_stocks.py \
    --start_date 2024-01-01 \
    --end_date 2024-12-31 \
    --num_processes auto \
    --output_path predictions_2024_full.csv
```

**预计时间：** 10-15 分钟（取决于CPU核心数）

### 场景4：预测关键时间点

```bash
# 预测年末最后几个交易日
python predict_stocks.py \
    --dates "2024-12-27,2024-12-30,2024-12-31" \
    --output_path year_end_predictions.csv
```

### 场景5：低资源模式

```bash
# 在内存受限的环境运行
python predict_stocks.py \
    --last_n_days 1 \
    --num_processes 1 \
    --output_path prediction.csv
```

**预计时间：** 2-3 分钟

## 故障排除速查

### 问题1：找不到 a500.csv

**错误：**
```
FileNotFoundError: CSV file not found: a500.csv
```

**解决方案：**
```bash
# 确认文件存在
ls -la a500.csv

# 如果不存在，使用完整路径
python predict_stocks.py --csv_path /full/path/to/a500.csv
```

### 问题2：日期不是交易日

**错误：**
```
WARNING: Date 2024-12-29 is not a trading day, skipping
ValueError: No valid dates provided.
```

**解决方案：**
```bash
# 查看可用的交易日
python -c "
import qlib
qlib.init(provider_uri='~/.qlib/tencent_data/qlib_data', region='cn')
from qlib.data import D
calendar = D.calendar()
print('Last 20 trading days:')
for d in calendar[-20:]:
    print(f'  {d}')
"

# 使用有效的交易日
python predict_stocks.py --dates "2024-12-30,2024-12-31"
```

### 问题3：内存不足

**症状：** 程序崩溃或系统缓慢

**解决方案：**
```bash
# 减少进程数
python predict_stocks.py --last_n_days 1 --num_processes 4

# 或使用单进程
python predict_stocks.py --last_n_days 1 --num_processes 1
```

### 问题4：进程卡住

**症状：** 程序运行但没有输出

**解决方案：**
```bash
# 使用单进程调试
python predict_stocks.py --num_processes 1 --dates 2024-12-31

# 检查临时文件权限
ls -la /tmp/
```

## 性能优化技巧

### 技巧1：选择合适的进程数

```bash
# 检查CPU核心数
python -c "import multiprocessing; print(f'CPU cores: {multiprocessing.cpu_count()}')"

# 根据核心数选择
# 4核心：使用 4 进程
# 8核心：使用 8 进程（默认）
# 16核心：使用 16 进程
# 更多：使用 auto
```

### 技巧2：分批预测大量日期

```bash
# 不要一次性预测一年，分月度预测
python predict_stocks.py --start_date 2024-01-01 --end_date 2024-01-31 --output_path jan.csv
python predict_stocks.py --start_date 2024-02-01 --end_date 2024-02-29 --output_path feb.csv
# ... 继续其他月份

# 或预测季度
python predict_stocks.py --start_date 2024-01-01 --end_date 2024-03-31 --output_path q1.csv
python predict_stocks.py --start_date 2024-04-01 --end_date 2024-06-30 --output_path q2.csv
# ... 继续其他季度
```

### 技巧3：合并预测结果

```bash
# 如果分批预测，合并结果
cat predictions_*.csv > all_predictions.csv

# 或使用 pandas
python -c "
import pandas as pd
import glob

files = glob.glob('predictions_*.csv')
dfs = [pd.read_csv(f) for f in files]
result = pd.concat(dfs, ignore_index=True)
result = result.sort_values(['date', 'stock_code'])
result.to_csv('all_predictions.csv', index=False)
print(f'Merged {len(files)} files into all_predictions.csv')
"
```

## 下一步

### 查看详细文档

```bash
# 查看完整的使用文档
cat PREDICT_STOCKS_README.md

# 或在浏览器中打开
open PREDICT_STOCKS_README.md  # macOS
```

### 查看实施总结

```bash
# 查看实施完成总结
cat IMPLEMENTATION_SUMMARY.md
```

### 集成到现有工作流

```bash
# 通过 run_example.py 调用
python run_example.py predict --last_n_days 1

# 或修改 run_example.py 添加预测命令
# 参考 PREDICT_STOCKS_README.md 中的集成说明
```

## 常见问题

### Q1：预测结果准确吗？

**A：** 预测结果取决于：
- 训练数据的质量和数量
- 模型配置和参数
- 市场环境和波动性

建议：
- 使用足够长的历史数据（至少1-2年）
- 定期重新训练模型
- 结合其他分析工具验证结果

### Q2：如何提高预测速度？

**A：** 方法包括：
1. 增加进程数（不超过CPU核心数）
2. 使用更高性能的硬件
3. 减少预测的日期范围
4. 分批预测大量日期

### Q3：可以预测未来多天吗？

**A：** 可以！使用日期段或最近N天模式：
```bash
# 预测未来5个交易日
python predict_stocks.py --last_n_days 5

# 预测特定日期范围
python predict_stocks.py --start_date 2025-01-01 --end_date 2025-01-31
```

### Q4：如何选择要预测的股票？

**A：** 默认使用 a500.csv 中的500只股票。要使用自定义股票列表：

1. 创建自己的 CSV 文件（格式同 a500.csv）
2. 使用 `--csv_path` 参数指定：
```bash
python predict_stocks.py --csv_path my_stocks.csv
```

### Q5：预测结果如何使用？

**A：** 预测结果可用于：
1. 选股策略：选择预测值最高的股票
2. 风险管理：结合预测值和风险指标
3. 回测分析：验证历史预测的准确性
4. 实时决策：基于预测做出交易决策

## 获取帮助

### 命令行帮助

```bash
# 查看所有参数说明
python predict_stocks.py --help
```

### 查看文档

```bash
# 快速开始
cat QUICK_START.md

# 详细文档
cat PREDICT_STOCKS_README.md

# 实施总结
cat IMPLEMENTATION_SUMMARY.md
```

## 成功标志

如果成功完成以上步骤，你应该：

✅ 所有依赖已安装
✅ 单元测试全部通过（4/4）
✅ 成功运行首次预测
✅ 生成 predictions.csv 文件
✅ 文件包含461只股票的预测结果

**恭喜！你现在可以使用这个强大的股票预测工具了！** 🎉

---

**最后更新：** 2026-01-04
**状态：** ✅ 完成并测试通过
