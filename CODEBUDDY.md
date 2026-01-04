# CODEBUDDY.md - Qlib Architecture Guide

## 1. Overall Purpose

Qlib is an open-source, AI-oriented quantitative investment platform developed by Microsoft Research. It aims to realize the potential, empower research, and create value using AI technologies in quantitative investment, from exploring ideas to implementing productions.

Key capabilities:
- **Complete ML Pipeline**: Data processing, model training, and back-testing
- **Full Quant Chain**: Alpha seeking, risk modeling, portfolio optimization, and order execution
- **Multiple Paradigms**: Supervised learning, market dynamics modeling, and reinforcement learning
- **Production Ready**: Online serving and automatic model rolling support

Reference: ["Qlib: An AI-oriented Quantitative Investment Platform"](https://arxiv.org/abs/2009.11189)

## 2. Main Directories and Their Purposes

### Core Package Structure (`/qlib`)
```
qlib/
├── backtest/          # Backtesting engine (Exchange, Executor, Account, Position, etc.)
├── cli/               # Command-line interface (qrun command)
├── contrib/            # Contributed models, strategies, and tools
│   ├── model/          # Ready-to-use models (LightGBM, XGBoost, MLR, etc.)
│   ├── strategy/       # Trading strategies (TopkDropout, TWAP, etc.)
│   ├── data/          # Data handlers (Alpha158, Alpha360, etc.)
│   ├── eva/           # Evaluation tools
│   ├── report/         # Reporting and analysis tools
│   └── workflow/       # Workflow utilities
├── data/              # Data providers and operations
│   ├── _libs/         # Cython-optimized rolling/expanding operations
│   ├── dataset/        # Dataset classes (DatasetH, DatasetL)
│   ├── storage/        # Data storage implementations
│   ├── ops.py          # Expression operators
│   ├── cache.py        # Caching mechanisms (Redis, Disk, Memory)
│   └── data.py        # Main data provider (D class)
├── model/             # Model base classes and trainers
│   ├── base.py         # BaseModel, Model, ModelFT (fine-tunable)
│   ├── trainer.py       # Training utilities
│   ├── ens/            # Ensemble methods
│   ├── interpret/       # Model interpretation
│   ├── meta/           # Meta-learning models
│   └── riskmodel/      # Risk models
├── rl/                # Reinforcement Learning framework
│   ├── order_execution/ # RL for order execution (PPO, OPDS, etc.)
│   ├── trainer/         # RL training utilities
│   ├── strategy/        # RL-based strategies
│   └── utils/          # RL utilities
├── strategy/           # Base strategy classes
├── workflow/           # Experiment management (MLflow-based)
│   ├── exp.py          # Experiment class
│   ├── expm.py         # Experiment manager
│   ├── recorder.py      # Recorder for logging metrics
│   └── record_temp.py  # Recording templates
├── utils/             # Utility functions
│   ├── time.py         # Time handling
│   ├── paral.py        # Parallel processing
│   ├── serial.py       # Serialization
│   └── data.py         # Data utilities
├── config.py          # Configuration management (C object)
├── log.py             # Logging infrastructure
└── __init__.py        # Package initialization
```

### Other Key Directories
- **`/examples`**: Complete examples including:
  - `benchmarks/`: Model implementations (LightGBM, XGBoost, LSTM, Transformer, etc.)
  - `benchmarks_dynamic/`: Dynamic market adaptation methods
  - `rl_order_execution/`: RL order execution examples
  - `highfreq/`: High-frequency trading examples
  - `tutorial/`: Tutorial notebooks
  - `data_demo/`: Data preparation demos
  - `portfolio/`: Portfolio optimization examples
  
- **`/tests`**: Test suite organized by component
  - `backtest/`: Backtesting tests
  - `data_mid_layer_tests/`: Data provider tests
  - `dataset_tests/`: Dataset tests
  - `rl/`: Reinforcement learning tests
  - `ops/`: Operator tests
  - `storage_tests/`: Storage tests
  
- **`/scripts`**: Utility scripts
  - `get_data.py`: Data downloading
  - `dump_bin.py`: Convert data to Qlib format
  - `check_data_health.py`: Data validation
  - `data_collector/`: Data collection scripts
  
- **`/docs`**: Sphinx documentation
  - `component/`: Component documentation
  - `developer/`: Developer guide
  - `advanced/`: Advanced topics

## 3. Programming Languages

**Primary Language**: Python (3.8, 3.9, 3.10, 3.11, 3.12)

**Cython for Performance**:
- `qlib/data/_libs/rolling.pyx`: Rolling operations compiled to C++
- `qlib/data/_libs/expanding.pyx`: Expanding operations compiled to C++
- These provide optimized calculations for time series operations

## 4. Build System and Package Management

**Build System**: 
- `setuptools` with `setuptools-scm` for version management
- `cython` for compiling performance-critical modules

**Package Management**:
- **pip** for distribution (package name: `pyqlib`)
- **pyproject.toml** defines dependencies and build configuration
- `setup.py` handles Cython extensions

**Key Dependencies**:
```
- pandas>=1.1          # Data manipulation
- numpy                  # Numerical computing
- mlflow                 # Experiment tracking
- redis                  # Caching
- lightgbm               # Gradient boosting
- pyyaml/ruamel.yaml     # Configuration
- gym                    # RL environments
- cvxpy                  # Portfolio optimization
- matplotlib              # Visualization
- pyarrow                # Data storage
```

**Installation Methods**:
1. **From PyPI**: `pip install pyqlib`
2. **From Source**: `pip install -e .` (editable mode)
3. **Docker**: Official images available (`pyqlib/qlib_image_stable`)

## 5. Testing Framework

**Primary Framework**: `pytest`

**Test Configuration** (`tests/pytest.ini`):
```ini
[pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
filterwarnings =
    ignore:.*rng.randint:DeprecationWarning
    ignore:.*Casting input x to numpy array:UserWarning
```

**Test Organization**:
- Tests run with: `python -m pytest tests/ -m "not slow"`
- CI runs on multiple OS: Windows, Ubuntu (22.04, 24.04), macOS (14, 15)
- Multiple Python versions: 3.8, 3.9, 3.10, 3.11, 3.12
- Retry logic in CI (3 attempts) for flaky tests

## 6. Linting/Formatting Tools

**Linting Pipeline** (defined in `Makefile`):

1. **Black** (Code Formatting):
   - Line length: 120 characters
   - Command: `make black`
   - Config: `.pre-commit-config.yaml`

2. **Pylint** (Code Quality):
   - Command: `make pylint`
   - Config: `.pylintrc`
   - Many warnings disabled for flexibility (C0103, W0212, E1102, etc.)

3. **Flake8** (Style Checks):
   - Command: `make flake8`
   - Ignores: E501 (line too long), E203 (whitespace), E731 (lambda), etc.
   - Per-file ignores for `__init__.py` (F401, F403)

4. **MyPy** (Type Checking):
   - Command: `make mypy`
   - Config: `.mypy.ini`
   - Version locked: `<1.5.0`

5. **nbqa** (Notebook Quality):
   - Applies black and pylint to Jupyter notebooks
   - Command: `make nbqa`

6. **nbconvert** (Notebook Testing):
   - Executes notebooks to ensure they work
   - Command: `make nbconvert`

**Pre-commit Hooks**: 
- Configured in `.pre-commit-config.yaml`
- Automatically runs black and flake8 on commit

## 7. High-Level Architecture and Key Components

### Core Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                  Application Layer                         │
│  (Examples: benchmarks, user workflows)                 │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                 Workflow Layer                            │
│  • Experiment Management (MLflow)                        │
│  • Recorder (logging, artifacts)                        │
│  • Task orchestration                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                  Learning Framework                        │
│  • Supervised Learning (Model, Trainer)                 │
│  • Reinforcement Learning (Policy, Env, Trainer)          │
│  • Meta-Learning                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                Business Logic Layer                        │
│  • Strategy (BaseStrategy, RLStrategy)                 │
│  • Trading (Decision, Order)                           │
│  • Portfolio (Position, Account)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                  Data Layer                             │
│  • Provider (Data, Calendar, Instrument, Feature)         │
│  • Operations (Expression engine with rolling/expanding)    │
│  • Storage (Local, Arctic, MongoDB)                    │
│  • Caching (Redis, Disk, Memory)                      │
└───────────────────────────────────────────────────────────────┘
```

### Key Components

#### Data Layer (`qlib.data`)
- **Provider System**: 
  - `D` - Main data interface for users
  - Providers: LocalProvider, ClientProvider, ArcticProvider
  - Supports multiple frequencies (day, 1min, etc.)
  
- **Expression Engine**:
  - Domain-specific language for feature engineering
  - Operators: Ref, Mean, Std, Corr, etc.
  - Optimized with Cython for performance
  
- **Caching Strategy**:
  - ExpressionCache: Cache feature expressions
  - DatasetCache: Cache prepared datasets
  - Redis-based distributed caching support
  
- **Point-in-Time (PIT) Database**:
  - Historical data integrity
  - Backfill adjustment support

#### Model Layer (`qlib.model`)
- **BaseModel**: Abstract interface for prediction
- **Model**: Learnable models with `fit()` and `predict()`
- **ModelFT**: Fine-tunable models
- **Trainer**: Training utilities (task_train)
- **Contrib Models**: Pre-implemented SOTA models

#### Workflow Layer (`qlib.workflow`)
- **R**: Global experiment manager
- **Recorder**: Log metrics, save artifacts, track experiments
- **MLflow Integration**: Backend for experiment tracking
- **Config-driven**: YAML-based workflow definitions

#### Backtesting Engine (`qlib.backtest`)
- **Exchange**: Simulates market (orders, fills, slippage)
- **Executor**: Executes decisions at different frequencies
- **Account**: Portfolio accounting
- **Position**: Position management
- **Strategy**: Base class for trading logic
- **Nested Execution**: Multi-level strategy optimization (e.g., day + minute)

#### Reinforcement Learning (`qlib.rl`)
- **Environment**: Gym-compatible trading environments
- **Policy**: RL policies (PPO, etc.)
- **Interpreter**: State/Action translation
- **Order Execution**: RL for optimal execution (TWAP, PPO, OPDS)

### Configuration System (`qlib.config`)

**Global Config Object `C`**:
- Hierarchical configuration
- Modes: `client` (default) and `server`
- Regions: CN, US, TW (different market rules)
- Environment variables: `QLIB_*` prefix
- Dynamic updating during runtime

**Key Settings**:
```python
C.provider_uri        # Data location (str or dict per frequency)
C.region              # Market region (REG_CN, REG_US, REG_TW)
C.expression_cache    # Caching strategy
C.kernels            # Number of CPUs for parallel processing
C.logging_level       # Logging verbosity
```

## 8. Existing Documentation Files

**No existing files found**:
- No `AGENTS.md`
- No `CLAUDE.md`
- No `.cursor/rules`
- No `.cursorrules`
- No `.github/copilot-instructions.md`

**Official Documentation**:
- Located in `/docs/` directory
- Built with Sphinx
- Available online: https://qlib.readthedocs.io/
- Key sections:
  - `component/`: Detailed component docs (Data, Model, Strategy, etc.)
  - `developer/`: Development guide and code standards
  - `start/`: Getting started tutorials
  - `advanced/`: Advanced topics

## 9. Common Commands

### Development Setup
```bash
# Install with dev dependencies
make dev

# Or install specific dependency sets
make develop    # Install base dependencies
make lint       # Install linting tools
make docs       # Install documentation tools
make rl         # Install RL dependencies
```

### Building and Testing
```bash
# Build Cython extensions (rolling, expanding)
make prerequisite

# Clean build artifacts
make clean

# Run all linting checks
make lint

# Run tests
cd tests
python -m pytest . -m "not slow"

# Run specific test file
python -m pytest tests/data_mid_layer_tests/test_ops.py
```

### Code Quality
```bash
# Format code with Black
make black
black qlib -l 120

# Check with Pylint
make pylint

# Check with Flake8
make flake8

# Type check with MyPy
make mypy

# Check notebooks
make nbqa
```

### Documentation
```bash
# Generate documentation
make docs-gen

# Or manually:
cd docs/
make html
```

### Data Preparation
```bash
# Download China market data
python -m qlib.cli.data qlib_data --target_dir ~/.qlib/qlib_data/cn_data --region cn

# Download 1-minute data
python -m qlib.cli.data qlib_data --target_dir ~/.qlib/qlib_data/cn_data_1min --region cn --interval 1min

# Convert CSV to Qlib format
python scripts/dump_bin.py --csv_path <path> --qlib_dir <qlib_data_dir>

# Check data health
python scripts/check_data_health.py check_data --qlib_dir ~/.qlib/qlib_data/cn_data
```

### Running Workflows
```bash
# Run workflow with qrun (CLI)
cd examples
qrun benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml

# Or run with Python
python qlib/cli/run.py examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml

# Run workflow by code
python examples/workflow_by_code.py
```

### Package Management
```bash
# Build wheel
make build
python -m build --wheel

# Upload to PyPI
make upload
python -m twine upload dist/*

# Install from source in editable mode
pip install -e .
```

## 10. Key Architectural Patterns and Design Decisions

### 1. Provider Pattern (Data Layer)
**Purpose**: Abstract different data sources and enable client-server mode

**Implementation**:
- `LocalProvider`: Local file system access
- `ClientProvider`: Remote server access (via API)
- `Provider` classes: CalendarProvider, InstrumentProvider, FeatureProvider

**Benefit**: Same API for local and distributed data access

### 2. Expression Engine Pattern
**Purpose**: Declarative feature engineering with lazy evaluation

**Implementation**:
```python
# Define expressions declaratively
fields = ['$close', 'Ref($close, 1)', 'Mean($close, 3)', '$high-$low']

# Operators are composable and lazy-evaluated
# Compiled to efficient operations
```

**Benefits**:
- User-friendly domain-specific language
- Optimized execution plan
- Cached intermediate results

### 3. Strategy-Executor Pattern
**Purpose**: Separate trading logic from execution mechanics

**Components**:
- **Strategy**: Generates trade decisions (what to do)
- **Executor**: Executes decisions at specific times (when and how)
- **Exchange**: Simulates market reality

**Nested Execution**:
```python
# Optimize portfolio at daily level AND execution at minute level
Executor[day](Strategy) + Executor[1min](Strategy)
```

### 4. Recorder Pattern (Experiment Management)
**Purpose**: Better abstraction over MLflow for experiment tracking

**Design**:
```python
with R.start(experiment_name='test'):
    model.fit(dataset)
    R.log_metrics({'ic': ic_value})
    R.save_objects(model=model)
```

**Advantages over raw MLflow**:
- Context manager for automatic start/end
- Rich methods (log_object, load_object)
- Code diff logging
- URI separation per experiment

### 5. Configuration Hierarchy
**Purpose**: Flexible configuration with sensible defaults

**Priority**:
1. Runtime arguments (`qlib.init(**kwargs)`)
2. YAML configuration
3. Default configuration (`C`)
4. Environment variables (`QLIB_*`)

**Modes**:
- `client`: Local mode (default for researchers)
- `server`: Server mode with shared caching

### 6. Data-Driven Architecture
**Purpose**: Decouple business logic from data access

**Implementation**:
- All data access through `D` object
- Operations are pure functions (no side effects)
- Caching transparent to users

### 7. Component-Based Design
**Purpose**: Loose coupling, standalone usage

**Example**:
```python
# Use just the data layer
from qlib.data import D
df = D.features(instruments, fields, start_time, end_time)

# Use just the backtesting engine
from qlib.backtest import backtest, get_exchange
exchange = get_exchange(...)
portfolio_metrics = backtest(...)
```

### 8. Performance Optimization Patterns

**Cython Optimization**:
- Rolling/expanding operations compiled to C++
- 10-100x faster than pure Python

**Parallel Processing**:
- `kernels` parameter for multi-CPU
- Joblib backend: multiprocessing/loky

**Caching Strategy**:
- ExpressionCache: Avoid recomputing features
- DatasetCache: Avoid reloading data
- Redis: Distributed caching for teams

**Binary Format**:
- Custom binary format for efficient storage
- Direct array loading (no CSV parsing)

### 9. Multi-Paradigm Support

**Supervised Learning**:
- Traditional ML pipeline: dataset → model → prediction
- Many SOTA models: LightGBM, XGBoost, Transformer, etc.

**Reinforcement Learning**:
- Gym-compatible environments
- RL for order execution (optimal execution strategies)
- Continuous decision modeling

**Market Dynamics**:
- Rolling retraining (adapt to concept drift)
- DDG-DA (domain adaptation)
- Meta-learning for quick adaptation

### 10. Region-Specific Design
**Purpose**: Different markets have different rules

**Regions**:
- **CN** (China): Trade unit 100, limit 9.5%
- **US** (United States): Trade unit 1, no limit
- **TW** (Taiwan): Trade unit 1000, limit 10%

**Configuration**:
```python
qlib.init(provider_uri="...", region=REG_CN)
```

### Design Philosophy

1. **User-Friendly**: High-level APIs (`qrun`, `R`, `D`)
2. **Flexible**: Configuration-driven, customizable components
3. **Performant**: Cython optimization, caching, parallelization
4. **Production-Ready**: Online serving, monitoring, reliability
5. **Extensible**: Plugin architecture, easy to add models/strategies
6. **Reproducible**: Experiment tracking, configuration management

---

## Quick Reference

### Initialization
```python
import qlib
from qlib.data import D

qlib.init(
    provider_uri="~/.qlib/qlib_data/cn_data",
    region="cn"
)
```

### Basic Workflow
```python
# 1. Get data
instruments = D.instruments('csi300')
df = D.features(instruments, ['$close', '$volume'], ...)

# 2. Train model
model.fit(dataset)

# 3. Backtest
from qlib.backtest import backtest
port_metrics, indicator_metrics = backtest(...)
```

### CLI Workflow
```bash
qrun workflow_config.yaml
```

### Key Classes
- `C`: Configuration object
- `D`: Data provider interface
- `R`: Experiment recorder
- `BaseModel`: Base class for models
- `BaseStrategy`: Base class for strategies
- `Exchange`: Market simulator
