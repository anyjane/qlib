# 量化投资管理系统

基于 FastAPI 的量化投资管理系统，使用 MongoDB 存储数据，并利用 Qlib 在线模式进行数据管理。

## 优化重点

1. **代码管理优化** - 支持股票代码的导入导出功能（CSV/Excel格式）
2. **交易代理管理优化** - 直接获取和显示代理的资产信息，包括账号ID、资产、持仓列表等
3. **主从代理机制** - 实现主用/从用代理切换，主用不可用时自动切换到从用，确保交易连续性

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

### 前端
- **框架**: Vue.js 3 + Element Plus
- **构建**: Vite
- **调试**: 支持前后端联调模式
- **Excel 导入导出**: xlsx 库

## 项目结构

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
│   │   └── agent_service.py      # 交易代理服务（优化主从机制）
│   ├── workers/
│   │   └── __init__.py
│   └── requirements.txt
├── frontend/                # 前端代码
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── router.js
│   │   ├── components/
│   │   │   ├── StockManager.vue      # 代码管理（优化导入导出）
│   │   │   ├── DataManager.vue        # 数据管理
│   │   │   ├── PredictResult.vue     # 预测结果
│   │   │   ├── PositionManager.vue   # 持仓管理（含交易操作）
│   │   │   ├── AgentManager.vue      # 交易代理管理（优化资产显示）
│   │   │   └── LogManager.vue         # 日志管理
│   │   ├── api/
│   │   │   ├── stock.js
│   │   │   └── agent.js
│   │   └── utils/
│   │       └── request.js    # Axios 封装
├── README.md
└── optimization-plan.md
```

## 快速开始

### 前置要求

- Python 3.8+
- MongoDB 4.0+
- Node.js 16+
- Qlib (可从 https://github.com/microsoft/qlib 安装)

### 后端安装

1. 创建虚拟环境
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量（可选）

创建 `.env` 文件：
```env
MONGODB_URL=mongodb://localhost:27017/
MONGODB_DB_NAME=quant_system_db
QLIB_PROVIDER_URI=~/.qlib/qlib_data/cn_data
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
```

4. 启动后端服务
```bash
python -m backend.main
```

后端将在 `http://localhost:8000` 运行。

### 前端安装

1. 安装依赖
```bash
cd frontend
npm install
```

2. 启动开发服务器
```bash
npm run dev
```

前端将在 `http://localhost:5173` 运行。

## 核心功能

### 1. 代码管理

- **导入功能**：支持 CSV 和 Excel 格式的批量导入
- **导出功能**：支持导出为 CSV 或 Excel
- **批量操作**：支持多选、全选、Shift+连续选择
- **数据验证**：导入时验证股票代码格式

### 2. 数据管理

- **腾讯 API 集成**：从腾讯财经 API 下载日线数据
- **Qlib 在线模式**：共享数据服务和缓存
- **增量下载**：支持初始下载和增量更新

### 3. 预测功能

- **Alpha158 因子**：使用 Qlib 的 Alpha158 特征
- **多进程加速**：支持多进程并行预测
- **历史查询**：支持历史数据查询和排序

### 4. 持仓管理

- **CRUD 操作**：添加、删除、修改持仓
- **导入导出**：支持持仓的导入导出
- **批量操作**：批量删除、批量更新
- **交易操作**：买入/卖出/同步

### 5. 交易代理管理

- **多代理支持**：支持配置多个交易代理
- **主从机制**：主用/从用代理配置
- **自动故障转移**：主用不可用时自动切换到从用
- **资产信息显示**：显示账号ID、总资产、可用资金、市值、持仓列表
- **心跳检测**：定时检测代理状态（30秒）

### 6. 日志管理

- **日志列表**：查看所有日志文件
- **单个下载**：下载单个日志文件
- **批量下载**：打包下载多个日志文件

## API 文档

启动后端后，访问 `http://localhost:8000/docs` 查看 Swagger API 文档。

## MongoDB 数据库设计

### Collections

1. **stocks** - 股票列表
2. **positions** - 持仓列表
3. **predictions** - 预测结果
4. **agent_configs** - 代理配置（支持多个代理）
5. **agent_positions** - 代理持仓记录
6. **local_positions** - 本地持仓（与代理持仓不同步）
7. **agent_logs** - 代理请求日志
8. **data_tasks** - 数据下载任务

## 开发指南

### 后端开发

```bash
# 进入后端目录
cd backend

# 激活虚拟环境
source venv/bin/activate

# 运行 FastAPI
python -m main

# 或使用 uvicorn
uvicorn main:app --reload --port 8000
```

### 前端开发

```bash
# 进入前端目录
cd frontend

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 测试

### 后端测试

```bash
cd backend
pytest
```

### 前端测试

```bash
cd frontend
npm run build
npm run preview
```

## 注意事项

1. **MongoDB 配置**: 需要安装 MongoDB 服务（localhost:27017）
2. **Qlib 初始化**: 首次运行需要初始化 Qlib 数据
3. **股票代码格式**: Qlib 使用 `sh600000`, `sz000001` 格式
4. **多进程限制**: 每个子进程需要独立初始化 Qlib
5. **主从代理机制**: 确保至少配置一个代理才能执行交易操作
6. **心跳检测**: 默认 30 秒检测一次代理状态

## 参考文档

- [Qlib 官方文档](https://qlib.readthedocs.io/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Element Plus 文档](https://element-plus.org/)
- [MongoDB 文档](https://docs.mongodb.com/)

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

- 项目地址: /Users/abc/workspace/qlib/examples/official
- 优化计划: optimization-plan.md
