# Official Backend API Tests

这是 official 后端项目的完整接口自测用例套件。

## 测试概述

本测试套件覆盖了所有 6 个 API 模块的 40+ 个接口：

- **Stock** - 股票管理（10 个接口）
- **Data** - 数据下载管理（5 个接口）
- **Predict** - 预测管理（3 个接口）
- **Position** - 持仓管理（7 个接口）
- **Agent** - 交易代理管理（11 个接口）
- **Log** - 日志管理（3 个接口）

## 目录结构

```
tests/
├── __init__.py                      # 测试包初始化
├── conftest.py                      # pytest 配置和共享 fixtures
├── test_stock.py                    # Stock 模块测试
├── test_data.py                     # Data 模块测试
├── test_predict.py                  # Predict 模块测试
├── test_position.py                 # Position 模块测试
├── test_agent.py                    # Agent 模块测试
├── test_log.py                      # Log 模块测试
├── fixtures/
│   ├── __init__.py
│   └── data_fixtures.py             # 测试数据 fixtures
└── utils/
    ├── __init__.py
    └── client.py                    # 测试客户端封装和断言辅助函数
```

## 安装依赖

```bash
cd /Users/samlty/code/qlib/examples/official/backend

# 安装所有依赖（包括测试依赖）
pip install -r requirements.txt

# 或者只安装测试依赖
pip install pytest==7.4.3
pip install pytest-asyncio==0.21.1
pip install pytest-cov==4.1.0
pip install pytest-mock==3.12.0
```

## 运行测试

### 运行所有测试

```bash
# 在项目根目录运行
pytest

# 或指定测试目录
pytest tests/
```

### 运行特定模块的测试

```bash
# 只运行 Stock 模块测试
pytest tests/test_stock.py -m stock

# 只运行 Data 模块测试
pytest tests/test_data.py -m data

# 只运行 Predict 模块测试
pytest tests/test_predict.py -m predict

# 只运行 Position 模块测试
pytest tests/test_position.py -m position

# 只运行 Agent 模块测试
pytest tests/test_agent.py -m agent

# 只运行 Log 模块测试
pytest tests/test_log.py -m log
```

### 运行特定测试函数

```bash
# 运行单个测试函数
pytest tests/test_stock.py::test_get_stocks_empty

# 运行特定文件中的所有测试
pytest tests/test_stock.py
```

### 显示详细输出

```bash
# 显示详细输出
pytest -v

# 显示打印输出
pytest -s

# 显示更详细的错误信息
pytest --tb=long
```

### 运行带覆盖率报告的测试

```bash
# 生成覆盖率报告
pytest --cov=. --cov-report=term-missing

# 生成 HTML 覆盖率报告
pytest --cov=. --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

### 运行慢速测试

```bash
# 运行所有测试（包括标记为 slow 的）
pytest -m "not slow"  # 跳过慢速测试
pytest -m slow         # 只运行慢速测试
```

### 并行运行测试

```bash
# 安装 pytest-xdist
pip install pytest-xdist

# 并行运行测试（使用 4 个进程）
pytest -n 4
```

## 测试配置

`pytest.ini` 文件配置了测试运行参数：

```ini
[pytest]
minversion = 7.0
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --tb=short
    --cov=.
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-report=xml
    --asyncio-mode=auto
```

## 测试标记

测试使用以下标记进行分类：

- `unit` - 单元测试
- `integration` - 集成测试
- `slow` - 慢速测试
- `stock` - Stock 模块测试
- `data` - Data 模块测试
- `predict` - Predict 模块测试
- `position` - Position 模块测试
- `agent` - Agent 模块测试
- `log` - Log 模块测试

## Fixtures

测试使用以下 fixtures：

### 自动 fixtures

- `client` - Async HTTP 测试客户端
- `setup_test_db` - 设置测试数据库（自动运行）
- `log_dir` - 临时日志目录

### 数据 fixtures

- `sample_stocks` - 示例股票数据
- `populated_stocks_db` - 填充股票数据的数据库
- `sample_positions` - 示例持仓数据
- `populated_positions_db` - 填充持仓数据的数据库
- `sample_agents` - 示例代理配置
- `populated_agents_db` - 填充代理配置的数据库
- `sample_predictions` - 示例预测数据
- `populated_predictions_db` - 填充预测数据的数据库

### 数据工厂

- `stock_factory` - 股票数据工厂
- `position_factory` - 持仓数据工厂
- `agent_factory` - 代理配置工厂
- `prediction_factory` - 预测数据工厂

## 测试数据管理

### 测试数据库隔离

每个测试函数使用独立的测试数据库：

- 数据库名称：`{original_db_name}_test`
- 每个测试前自动清理数据
- 确保测试之间互不干扰

### 测试数据

测试数据位于 `tests/fixtures/data_fixtures.py`：

- `TEST_STOCKS` - 测试股票数据
- `TEST_POSITIONS` - 测试持仓数据
- `TEST_AGENTS` - 测试代理配置
- `generate_test_predictions()` - 生成测试预测数据

## 断言辅助函数

`tests/utils/client.py` 提供了以下辅助函数：

### API 客户端封装

- `APITestClient` - 统一的 API 测试客户端封装
- `get()` - GET 请求
- `post()` - POST 请求
- `put()` - PUT 请求
- `delete()` - DELETE 请求
- `get_json()` - GET 请求并返回 JSON
- `post_json()` - POST 请求并返回 JSON

### 断言函数

- `assert_success_response()` - 断言响应成功
- `assert_error_response()` - 断言错误响应
- `assert_json_keys()` - 断言 JSON 响应包含指定键
- `assert_list_not_empty()` - 断言非空列表
- `assert_field_equals()` - 断言字段等于期望值
- `assert_field_type()` - 断言字段类型
- `assert_stock_structure()` - 断言股票数据结构
- `assert_position_structure()` - 断言持仓数据结构
- `assert_agent_structure()` - 断言代理配置结构

## 测试覆盖率

生成覆盖率报告：

```bash
# 终端报告
pytest --cov=. --cov-report=term-missing

# HTML 报告
pytest --cov=. --cov-report=html

# XML 报告（用于 CI/CD）
pytest --cov=. --cov-report=xml
```

覆盖率报告位置：

- 终端：直接显示在命令行
- HTML：`htmlcov/index.html`
- XML：`coverage.xml`

## 故障排查

### MongoDB 连接问题

确保 MongoDB 正在运行：

```bash
# 检查 MongoDB 状态
mongod --version

# 启动 MongoDB（如未运行）
mongod --dbpath /path/to/db
```

### 测试失败

如果测试失败，查看详细错误信息：

```bash
# 显示详细回溯
pytest --tb=long

# 显示更短的回溯
pytest --tb=short

# 只显示错误摘要
pytest --tb=line
```

### 依赖问题

重新安装依赖：

```bash
pip install --upgrade -r requirements.txt
```

## 持续集成

测试套件可以在 CI/CD 流水线中运行：

```yaml
# 示例 GitHub Actions 配置
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          file: ./coverage.xml
```

## 最佳实践

1. **运行测试前**：确保 MongoDB 正在运行
2. **隔离测试**：每个测试使用独立的测试数据库
3. **清理数据**：每个测试后自动清理数据
4. **使用 fixtures**：复用测试数据和配置
5. **标记测试**：使用 pytest 标记组织测试
6. **查看覆盖率**：定期检查测试覆盖率
7. **并行运行**：使用 pytest-xdist 加速测试

## 许可证

本测试套件遵循与主项目相同的许可证。
