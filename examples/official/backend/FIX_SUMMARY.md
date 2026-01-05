# 修复说明：导出CSV时name列显示英文名

## 问题描述
用户报告在导出股票列表为CSV时，`name` 列显示的是英文名称，而不是中文名称。例如：
- `sz000001` 的 name 显示为 `"Ping An Bank Co., Ltd."`（英文），应该是 `"平安银行"`（中文）
- `sz000002` 的 name 显示为 `"China Vanke Co Ltd"`（英文），应该是 `"万科A"`（中文）

## 根本原因

A500.csv 文件包含两个名称列：
- 第5列：`成份券名称Constituent Name`（中文名称）
- 第6列：`成份券英文名称Constituent Name(Eng)`（英文名称）

原来的列名匹配逻辑使用模糊匹配（`if '成份券名称' in col or 'constituent name' in col_lower`），这会同时匹配到两个名称列。由于列名匹配顺序不确定，可能匹配到英文名称列，导致导出的数据中显示的是英文名。

## 修复内容

### 1. 改进 `import_stocks` 函数
优化列名匹配逻辑，优先匹配中文名称列：
```python
# 查找名称列（优先中文名称）
# 1. 优先匹配常见的标准列名（英文）
for col in df.columns:
    col_lower = col.lower().strip()
    if col_lower in ['name', '股票名称']:
        name_col = col
        break

# 2. 如果没找到，匹配"成份券名称"（但排除英文名列）
if name_col is None:
    for col in df.columns:
        col_lower = col.lower().strip()
        if '成份券名称' in col or 'constituent name' in col_lower:
            # 排除英文名称列
            if 'eng' not in col_lower and 'english' not in col_lower and '(eng)' not in col_lower:
                name_col = col
                break
```

### 2. 改进 `initialize_stocks_from_csv` 函数
使用多级匹配策略，确保准确选择中文名称列：
```python
# 查找名称列（优先中文名称，避免匹配到英文名称）
# 完全匹配优先：成份券名称Constituent Name
for col in df.columns:
    if col == '成份券名称Constituent Name':
        name_col = col
        break

# 如果没有完全匹配，查找包含"成份券名称"的列
if name_col is None:
    for col in df.columns:
        col_lower = col.lower()
        # 包含"成份券名称"但不包含"英文名"或"(eng)"
        if '成份券名称' in col and 'eng' not in col_lower and 'english' not in col_lower:
            name_col = col
            break

# 如果还没找到，尝试其他列名
if name_col is None:
    for col in df.columns:
        col_lower = col.lower()
        if 'constituent name' in col_lower and 'eng' not in col_lower:
            name_col = col
            break
```

## 改进效果

1. **准确识别中文名称列**：通过多级匹配和排除规则，确保选择的是中文名称列而不是英文名称列
2. **支持多种CSV格式**：灵活支持不同的列名格式（标准英文名、中文名、混合格式等）
3. **更详细的日志**：记录找到的列名和示例数据，方便调试
4. **更好的错误提示**：当列名不匹配时，提供清晰的错误信息和实际找到的列名列表

## 测试建议

1. 重新初始化股票列表：调用 `/api/stocks/initialize` 接口
2. 检查日志输出，确认正确识别了列名（应该是 `成份券名称Constituent Name`）
3. 验证导入的数据：
   ```python
   # 从 MongoDB 查询第一条数据，检查 name 字段是否为中文名
   ```
4. 导出 CSV：调用 `/api/stocks/export` 接口
5. 验证导出的 CSV 文件中 `name` 列是否显示中文股票名称

## A500.csv 列结构
```
列索引 | 列名                          | 示例值
-------|-------------------------------|-------------------------
0      | 日期Date                       | 20251231
1      | 指数代码 Index Code            | 000510
2      | 指数名称 Index Name            | 中证A500
3      | 指数英文名称Index Name(Eng)    | CSI A500
4      | 成份券代码Constituent Code      | 000001
5      | 成份券名称Constituent Name      | 平安银行 ← 应使用此列
6      | 成份券英文名称Constituent ...   | Ping An Bank Co., Ltd.
7      | 交易所Exchange                 | 深圳证券交易所
8      | 交易所英文名称Exchange(Eng)    | Shenzhen Stock Exchange
```

## 相关文件
- `/Users/samlty/code/qlib/examples/official/backend/api/stock.py`
- `/Users/samlty/code/qlib/examples/official/backend/A500.csv`

