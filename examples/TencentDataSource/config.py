# Tencent Data Source Configuration
import os
from pathlib import Path

# Base URL for Tencent stock data API
TENCENT_BASE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"

# Maximum records per request (Tencent API limitation)
MAX_RECORDS_PER_REQUEST = 2000

# Default data directory
DEFAULT_DATA_DIR = os.path.expanduser("~/.qlib/tencent_data")

# Stock pool configuration
MARKET_CONFIG = {
    "csi300": {
        "name": "CSI300",
        "benchmark": "SH000300",
        "stocks_file": "csi300.txt",
    }
}

# Time range configuration
TIME_CONFIG = {
    "train_start": "2020-01-01",
    "train_end": "2024-12-31",
    "test_start": "2025-01-01",
    "test_end": "2025-12-31",
    "data_start": "2020-01-01",
    "data_end": "2025-12-31",
}

# Data collection configuration
COLLECTION_CONFIG = {
    "interval": "day",  # day or 1min
    "max_workers": 8,  # Number of concurrent workers (recommend 8 for parallel download)
    "max_collector_count": 2,  # Max retry attempts for failed requests
    "delay": 0,  # Delay between requests in seconds
    "check_data_length": None,  # Minimum required data length
}

# Alpha158 configuration
ALPHA158_CONFIG = {
    "handler": "Alpha158",
    "handler_module": "qlib.contrib.data.handler",
}

# Model configuration (LightGBM)
MODEL_CONFIG = {
    "class": "LGBModel",
    "module_path": "qlib.contrib.model.gbdt",
    "kwargs": {
        "loss": "mse",
        "colsample_bytree": 0.8879,
        "learning_rate": 0.2,
        "subsample": 0.8789,
        "lambda_l1": 205.6999,
        "lambda_l2": 580.9768,
        "max_depth": 8,
        "num_leaves": 210,
        "num_threads": 20,
    },
}

# Portfolio analysis configuration
PORT_ANALYSIS_CONFIG = {
    "strategy": {
        # "class": "TopkDropoutStrategy",
        # "module_path": "qlib.contrib.strategy",
        "class": "TopkDropoutWithReallocation",
        "module_path": "examples.TencentDataSource.topk_dropout_with_reallocation",
        "kwargs": {
            "signal": "<PRED>",
            "topk": 20,
            "n_drop": 2,
            "verbose": True,
            "max_reallocation_rounds": 3,
        },
    },
    "backtest": {
        "start_time": "2025-01-01",
        "end_time": "2025-12-30",
        "account": 1000000,
        "benchmark": "SH000300",
        "exchange_kwargs": {
            "limit_threshold": 0.095,
            "deal_price": "close",
            "open_cost": 0.0005,
            "close_cost": 0.0015,
            "min_cost": 5,
        },
    },
}

# Logging configuration
LOGGING_CONFIG = {
    "level": "INFO",  # DEBUG, INFO, WARNING, ERROR
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
}
