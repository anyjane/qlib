# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Data Collector Module for Qlib

This module provides base classes and utilities for collecting financial data
from various sources and normalizing it for use with Qlib.

The main classes are:
- BaseCollector: Base class for data collectors
- BaseNormalize: Base class for data normalizers
- BaseRun: Base class for running data collection workflows
"""

from .base import BaseCollector, BaseNormalize, BaseRun, Normalize

__all__ = [
    "BaseCollector",
    "BaseNormalize",
    "BaseRun",
    "Normalize",
]
