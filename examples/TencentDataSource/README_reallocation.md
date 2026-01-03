# TopkDropoutWithReallocation Strategy 使用说明

## 概述

`TopkDropoutWithReallocation` 是基于 Qlib 内置 `TopkDropoutStrategy` 的改进版本，通过**剩余资金重分配**机制，显著提高了小资金场景下的资金利用率。

## 核心特性

✅ **等额分配** - 保持原策略的简单性，资金平均分配给选中的股票  
✅ **独立取整** - 每只股票按100股独立向下取整（符合A股交易规则）  
✅ **剩余资金重分配** - 收集取整损失的资金，重新分配给低价股  
✅ **高资金利用率** - 从94%提升到99%+  

## 性能提升

### 验证结果（100万资金）

| 场景 | 原策略利用率 | 新策略利用率 | 提升 |
|------|------------|------------|------|
| 100万/52只股票 | 94.56% | **99.88%** | **+5.32%** |
| 100万/30只股票 | 97.47% | **99.94%** | **+2.47%** |
| 50万/20只股票 | 95.50% | **99.67%** | **+4.18%** |

### 实际效果

**100万资金，52只股票**：
- 原策略剩余现金：**51,637.50元**
- 新策略剩余现金：**1,122.23元**
- **额外利用资金：50,515.27元**

## 使用方法

### 方法1：修改 config.py

在 `examples/TencentDataSource/config.py` 中修改策略配置：

```python
PORT_ANALYSIS_CONFIG = {
    "strategy": {
        "class": "TopkDropoutWithReallocation",
        "module_path": "examples.TencentDataSource.topk_dropout_with_reallocation",
        "kwargs": {
            "signal": "<PRED>",
            "topk": 50,
            "n_drop": 5,
            # 新策略参数（可选）
            "verbose": True,              # 打印资金利用率统计
            "max_reallocation_rounds": 3,  # 最大重分配轮数
        },
    },
    "backtest": {
        # ... 其他配置保持不变
    },
}
```

### 方法2：修改 YAML 配置文件

在 `examples/TencentDataSource/workflow_config_tencent_alpha158.yaml` 中修改：

```yaml
port_analysis_config: &port_analysis_config
    strategy:
        class: TopkDropoutWithReallocation
        module_path: examples.TencentDataSource.topk_dropout_with_reallocation
        kwargs:
            signal: <PRED>
            topk: 50
            n_drop: 5
            verbose: true
            max_reallocation_rounds: 3
    
    backtest:
        # ... 其他配置保持不变
```

## 策略参数说明

### 继承自 TopkDropoutStrategy 的参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `topk` | int | 必需 | 持仓股票数量 |
| `n_drop` | int | 必需 | 每个交易日替换的股票数量 |
| `method_sell` | str | "bottom" | 卖出方法："bottom" 或 "random" |
| `method_buy` | str | "top" | 买入方法："top" 或 "random" |
| `hold_thresh` | int | 1 | 最小持有天数 |
| `only_tradable` | bool | False | 是否只考虑可交易股票 |
| `forbid_all_trade_at_limit` | bool | True | 涨跌停时是否禁止所有交易 |

### 新增参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `verbose` | bool | True | 是否打印资金利用率统计 |
| `max_reallocation_rounds` | int | 3 | 最大重分配轮数 |

## 算法流程

```
第一步：等额分配（与原策略相同）
    ↓
计算每只股票分配金额 = 总资金 / 股票数
    ↓
第二步：独立取整
    ↓
按100股向下取整（应用A股交易单位限制）
    ↓
第三步：收集剩余资金
    ↓
剩余资金 = 分配总额 - 取整后实际总额
    ↓
第四步：剩余资金重分配
    ↓
按股价排序，优先分配给低价股
    ↓
重复第三、四步直到资金充分利用
    ↓
第五步：生成订单
    ↓
根据最终分配结果生成买卖订单
```

## 运行验证脚本

```bash
cd /home/abc.linux/workspace/qlib/examples/TencentDataSource
python test_reallocation_strategy.py
```

该脚本会模拟不同资金和股票数量场景，对比原策略和新策略的资金利用率。

## 输出示例

```python
=== First Round Allocation ===
  Available cash: 950,000.00 元
  Stocks to buy: 52
  Cash per Stock: 18,269.23 元
  Remaining cash after rounding: 51,637.50 元

Second Round: Redistributing Remaining Cash
  Round 1: Allocated 50,515.27 to SH000011 (price: 18.04)

Final Allocation:
  Total Value: 948,877.77 元
  Remaining Cash: 1,122.23 元
  Capital Utilization: 99.88%

COMPARISON SUMMARY
Metric                         Original             With Reallocation
Capital Utilization                         94.56%              99.88%
Remaining Cash                          51,637.50           1,122.23
Utilization Improvement                                           5.32%

✓ Capital utilization improved by 5.32%
✓ Additional capital utilized: 50,515.27 元
```

## 注意事项

1. **不修改 qlib 核心代码**：策略文件位于 `examples/TencentDataSource/` 目录下，不涉及 qlib 核心库的修改

2. **兼容性**：新策略完全兼容现有的回测框架和配置系统

3. **虚拟环境**：如果项目使用了虚拟环境，请确保已激活虚拟环境后再运行：
   ```bash
   source /path/to/.venv/bin/activate
   python workflow.py
   ```

4. **性能影响**：重分配逻辑在每次调仓时执行，对回测速度影响很小（通常<1%）

## 文件结构

```
examples/TencentDataSource/
├── topk_dropout_with_reallocation.py    # 新策略实现
├── test_reallocation_strategy.py        # 验证脚本
├── config.py                            # 策略配置
├── workflow.py                          # 工作流脚本
└── README_reallocation.md               # 本文档
```

## 常见问题

**Q: 为什么权重完全相同？**  
A: 原TopkDropoutStrategy采用等额分配+独立取整，所有股票经过相同处理流程后实际持仓金额几乎一致，导致权重完全相同。新策略通过重分配剩余资金打破了这一现象。

**Q: 重分配是否会增加交易成本？**  
A: 重分配只是将取整损失的资金重新分配给其他股票，不会增加额外的交易次数和成本。

**Q: 是否适用于大资金场景？**  
A: 大资金场景下取整损失占比很小，效果不如小资金场景明显，但仍然有效。

**Q: 如何关闭详细输出？**  
A: 设置 `verbose=False` 即可关闭资金利用率统计输出。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交 Issue 到 Qlib 项目仓库
- 参考策略源码：`examples/TencentDataSource/topk_dropout_with_reallocation.py`
