# TencentDataSource - Qlib Example with Tencent Stock API

This example demonstrates how to use Tencent's stock data API as a custom data source in Qlib, implement a complete workflow including data collection, feature engineering with Alpha158, model training, and backtesting.

## Features

- **Tencent HTTP API Integration**: Fetch stock K-line data from Tencent's public API
- **Automatic Pagination**: Handles API's 2000 records limit with smart pagination
- **CSI300 Stock Pool**: Uses CSI300 index constituents as the stock universe
- **Alpha158 Features**: Implements 158 technical factors for feature engineering
- **Complete Workflow**: End-to-end pipeline from data collection to backtesting
- **Performance Metrics**: Automatically outputs annualized return and Sharpe ratio
- **Logging**: Comprehensive logging for debugging and monitoring

## Architecture

```
TencentDataSource/
├── __init__.py              # Package initialization
├── config.py                # Configuration parameters
├── tencent_data_source.py   # Data collector and normalizer
├── workflow.py              # Training and backtesting workflow
└── README.md                # This file
```

## Quick Start

### Prerequisites

1. Install Qlib and dependencies:
```bash
pip install qlib pandas numpy requests loguru fire
```

2. Ensure you have Qlib's default data for CSI300 (for stock list):
```bash
python scripts/get_data.py qlib_data --target_dir ~/.qlib/qlib_data/cn_data --region cn
```

### Step 1: Collect Data from Tencent API

```bash
cd examples/TencentDataSource

# Download data for CSI300 stocks from 2020-01-01 to 2025-12-31
python -m tencent_data_source download_data \
    --source_dir ~/.qlib/tencent_data/source \
    --start 2020-01-01 \
    --end 2025-12-31 \
    --interval day \
    --max_workers 1
```

### Step 2: Normalize and Convert to Qlib Format

```bash
# Normalize the collected data
python -m tencent_data_source normalize_data \
    --source_dir ~/.qlib/tencent_data/source \
    --normalize_dir ~/.qlib/tencent_data/normalize \
    --interval day
```

### Step 3: Dump to Qlib Binary Format

```bash
# Convert normalized data to Qlib format
cd ../../scripts
python dump_bin.py \
    --csv_path ~/.qlib/tencent_data/normalize \
    --qlib_dir ~/.qlib/tencent_data/qlib_data \
    --freq day \
    --include_fields open,close,high,low,volume,amount,change
```

### Step 4: Run Training and Backtesting

```bash
cd examples/TencentDataSource

# Run the complete workflow
python -m workflow run \
    --provider_uri ~/.qlib/tencent_data/qlib_data \
    --experiment_name tencent_alpha158_2025 \
    --mode code \
    --market csi300
```

## Configuration

All parameters are configured in `config.py`:

### Data Collection Settings

```python
COLLECTION_CONFIG = {
    "interval": "day",           # Data frequency: "day" or "1min"
    "max_workers": 1,            # Concurrent workers (recommend 1)
    "max_collector_count": 2,     # Retry attempts for failed requests
    "delay": 0,                 # Delay between requests (seconds)
    "check_data_length": None,    # Minimum data length required
}
```

### Time Periods

```python
TIME_CONFIG = {
    "train_start": "2020-01-01",
    "train_end": "2024-12-31",
    "test_start": "2025-01-01",
    "test_end": "2025-12-31",
}
```

### Model Configuration (LightGBM)

```python
MODEL_CONFIG = {
    "class": "LGBModel",
    "kwargs": {
        "loss": "mse",
        "learning_rate": 0.2,
        "max_depth": 8,
        "num_leaves": 210,
        # ... more parameters
    },
}
```

### Portfolio Strategy

```python
PORT_ANALYSIS_CONFIG = {
    "strategy": {
        "class": "TopkDropoutStrategy",
        "kwargs": {
            "signal": "<PRED>",
            "topk": 50,           # Top 50 stocks
            "n_drop": 5,          # Dropout 5 stocks
        },
    },
    "backtest": {
        "account": 100000000,      # 100 million initial capital
        "open_cost": 0.0005,      # 0.05% buy cost
        "close_cost": 0.0015,     # 0.15% sell cost
    },
}
```

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

## Workflow Components

### 1. Data Collection (`TencentCollector`)

- Fetches K-line data from Tencent API
- Handles pagination for large datasets
- Implements retry logic for failed requests
- Supports concurrent data collection

**Usage**:
```python
from tencent_data_source import TencentCollector

collector = TencentCollector(
    save_dir="~/.qlib/tencent_data/source",
    start="2020-01-01",
    end="2025-12-31",
    interval="day",
    max_workers=1,
)
collector.collector_data()
```

### 2. Data Normalization (`TencentNormalize`)

- Converts Tencent data to Qlib format
- Handles missing values and outliers
- Aligns to trading calendar
- Calculates daily returns

**Usage**:
```python
from tencent_data_source import TencentNormalize

normalizer = TencentNormalize(date_field_name="date", symbol_field_name="symbol")
normalized_data = normalizer.normalize(raw_data)
```

### 3. Workflow Execution (`run_tencent_workflow`)

- Initializes Qlib with custom data
- Creates model and dataset
- Trains LightGBM model on 2020-2024 data
- Backtests on 2025 data
- Outputs performance metrics

**Usage**:
```python
from workflow import run_tencent_workflow

results = run_tencent_workflow(
    provider_uri="~/.qlib/tencent_data/qlib_data",
    experiment_name="my_experiment",
    mode="code",
    market="csi300",
)

print(f"Annual Return: {results['annual_return_no_cost']}")
print(f"Sharpe Ratio: {results['sharpe_ratio_no_cost']}")
```

## Output Metrics

The workflow automatically outputs the following performance metrics:

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

## Logging

Comprehensive logging is implemented throughout the workflow:

- **INFO**: Progress updates and key events
- **DEBUG**: Detailed debugging information
- **WARNING**: Non-critical issues (e.g., failed requests)
- **ERROR**: Critical errors

**Enable Debug Logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Troubleshooting

### Issue: "No data returned from API"

**Solution**: Check if the stock code is correct and trading. Some stocks may be delisted.

### Issue: "Request timeout"

**Solution**: Increase `REQUEST_TIMEOUT` in `tencent_data_source.py` or use a VPN if outside China.

### Issue: "Missing instruments from Qlib"

**Solution**: Download default Qlib data first:
```bash
python scripts/get_data.py qlib_data --target_dir ~/.qlib/qlib_data/cn_data --region cn
```

### Issue: "Data not found for 2025"

**Solution**: Verify that the end date is within the available date range. Use a recent date as the end date.

### Issue: "Memory error during data collection"

**Solution**: Reduce `max_workers` to 1 and collect data in smaller batches by adjusting the date range.

## Advanced Usage

### Custom Stock Pool

To use a custom stock pool instead of CSI300:

```python
# Modify get_instrument_list() in tencent_data_source.py
def get_instrument_list(self) -> List[str]:
    # Return your custom stock symbols
    return ["sh600000", "sh600519", "sh601318", ...]
```

### Custom Alpha Features

To modify Alpha158 configuration:

```python
# Edit ALPHA158_CONFIG in config.py
ALPHA158_CONFIG = {
    "handler": "Alpha360",  # Use Alpha360 instead
    # or create custom handler
}
```

### Custom Model

To use a different model:

```python
# Edit MODEL_CONFIG in config.py
MODEL_CONFIG = {
    "class": "MLPModel",  # Use MLP instead of LGBM
    "module_path": "qlib.contrib.model.pytorch_nn",
    "kwargs": { ... },
}
```

## Performance Tips

1. **Data Collection**: Use `max_workers=1` to avoid rate limiting
2. **Pagination**: The collector automatically handles pagination for large date ranges
3. **Caching**: Once collected, data can be reused without re-downloading
4. **Parallel Processing**: Qlib's workflow automatically uses multi-threading for data processing

## References

- [Qlib Documentation](https://qlib.readthedocs.io/)
- [Tencent Stock API](https://web.ifzq.gtimg.cn/)
- [Alpha158 Features](https://github.com/microsoft/qlib/blob/main/qlib/contrib/data/loader.py)
- [LightGBM Documentation](https://lightgbm.readthedocs.io/)

## License

Copyright (c) Microsoft Corporation. Licensed under the MIT License.

## Support

For issues and questions:
- Check the [Qlib GitHub Issues](https://github.com/microsoft/qlib/issues)
- Review the logs for detailed error messages
- Verify API availability and data range
