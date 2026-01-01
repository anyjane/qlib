# TencentDataSource - Qlib Example with Tencent Stock API

This example demonstrates how to use Tencent's stock data API as a custom data source in Qlib, implement a complete workflow including data collection, feature engineering with Alpha158, model training, and backtesting.

## Features

- **Tencent HTTP API Integration**: Fetch stock K-line data from Tencent's public API
- **Automatic Pagination**: Handles API's 2000 records limit with smart pagination
- **CSI300 Stock Pool**: Uses CSI300 index constituents as stock universe
- **Alpha158 Features**: Implements 158 technical factors for feature engineering
- **Complete Workflow**: End-to-end pipeline from data collection to backtesting
- **Performance Metrics**: Automatically outputs annualized return and Sharpe ratio
- **Logging**: Comprehensive logging for debugging and monitoring

## Architecture

```
TencentDataSource/
├── __init__.py                        # Package initialization
├── config.py                          # Configuration parameters
├── tencent_data_source.py               # Data collector and normalizer (uses data_collector.base)
├── workflow.py                         # Training and backtesting workflow
├── run_example.py                      # Main entry point
├── workflow_config_tencent_alpha158.yaml  # YAML configuration
├── IMPORT_FIX_SUMMARY.md               # Import fix documentation
└── README.md                          # This file
```

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
