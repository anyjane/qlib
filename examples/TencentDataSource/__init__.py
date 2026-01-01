# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
TencentDataSource - Example for using Tencent stock data API as data source in Qlib

This example demonstrates how to:
1. Fetch stock data from Tencent's HTTP API
2. Handle pagination for large datasets (2000 records limit per request)
3. Integrate with Qlib's workflow system
4. Use Alpha158 features with CSI300 stocks
5. Train on 2020-2024 and backtest on 2025 data
"""

from .tencent_data_source import TencentCollector
from .workflow import run_tencent_workflow

__all__ = ["TencentCollector", "run_tencent_workflow"]
