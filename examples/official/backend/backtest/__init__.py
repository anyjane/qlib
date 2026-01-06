"""回测模块"""
from .strategies import (
    BaseStrategy,
    TopkDropoutStrategy,
    TopkReallocationStrategy,
    create_strategy,
)
from .data_loader import FeaturesDataLoader
from .trade_logger import TradeLogger
from .service import BacktestService
from .types import (
    BacktestConfig,
    BacktestResult,
    BacktestMetrics,
    DailyTradeLog,
    BuyDetail,
    SellDetail,
    PositionDetail,
    TopStock,
    EquityPoint,
    StrategyType,
    MethodType,
)

__all__ = [
    # Strategies
    "BaseStrategy",
    "TopkDropoutStrategy",
    "TopkReallocationStrategy",
    "create_strategy",
    # Components
    "FeaturesDataLoader",
    "TradeLogger",
    "BacktestService",
    # Types
    "BacktestConfig",
    "BacktestResult",
    "BacktestMetrics",
    "DailyTradeLog",
    "BuyDetail",
    "SellDetail",
    "PositionDetail",
    "TopStock",
    "EquityPoint",
    "StrategyType",
    "MethodType",
]
