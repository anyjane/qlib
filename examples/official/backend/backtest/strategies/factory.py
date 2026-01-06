"""策略工厂"""
from typing import Dict, Any
from .base_strategy import BaseStrategy
from .topk_dropout import TopkDropoutStrategy
from .topk_reallocation import TopkReallocationStrategy
from ..type_defs import StrategyType


# 策略注册表
_STRATEGY_REGISTRY: Dict[StrategyType, type] = {
    StrategyType.TOPK_DROPOUT: TopkDropoutStrategy,
    StrategyType.TOPK_REALLOCATION: TopkReallocationStrategy,
}


def create_strategy(
    strategy_type: StrategyType,
    **kwargs,
) -> BaseStrategy:
    """
    创建策略实例

    Args:
        strategy_type: 策略类型
        **kwargs: 策略参数

    Returns:
        策略实例

    Raises:
        ValueError: 未知的策略类型
    """
    strategy_class = _STRATEGY_REGISTRY.get(strategy_type)

    if strategy_class is None:
        raise ValueError(f"Unknown strategy type: {strategy_type}")

    return strategy_class(**kwargs)


def get_available_strategies() -> Dict[StrategyType, Dict[str, Any]]:
    """
    获取可用的策略列表

    Returns:
        策略信息字典
    """
    from ..type_defs import StrategyInfo

    strategies = {
        StrategyType.TOPK_DROPOUT: StrategyInfo(
            type=StrategyType.TOPK_DROPOUT,
            name="TopkDropout",
            description="标准TopkDropout策略，每次调仓替换评分最低的股票",
            params={
                "topk": {"type": "int", "default": 50, "description": "持仓数量"},
                "n_drop": {"type": "int", "default": 5, "description": "每次调仓替换数"},
                "method_sell": {"type": "str", "default": "bottom", "description": "卖出方法（top/bottom/random）"},
                "method_buy": {"type": "str", "default": "top", "description": "买入方法（top/bottom/random）"},
                "hold_thresh": {"type": "int", "default": 1, "description": "持仓最小天数"},
                "only_tradable": {"type": "bool", "default": False, "description": "只考虑可交易股票"},
                "forbid_all_trade_at_limit": {"type": "bool", "default": True, "description": "涨跌停禁止交易"},
            },
        ),
        StrategyType.TOPK_REALLOCATION: StrategyInfo(
            type=StrategyType.TOPK_REALLOCATION,
            name="TopkDropoutWithReallocation",
            description="增强的TopkDropout策略，支持资金再分配以提高利用率",
            params={
                "topk": {"type": "int", "default": 50, "description": "持仓数量"},
                "n_drop": {"type": "int", "default": 5, "description": "每次调仓替换数"},
                "method_sell": {"type": "str", "default": "bottom", "description": "卖出方法（top/bottom/random）"},
                "method_buy": {"type": "str", "default": "top", "description": "买入方法（top/bottom/random）"},
                "hold_thresh": {"type": "int", "default": 1, "description": "持仓最小天数"},
                "only_tradable": {"type": "bool", "default": False, "description": "只考虑可交易股票"},
                "forbid_all_trade_at_limit": {"type": "bool", "default": True, "description": "涨跌停禁止交易"},
                "max_reallocation_rounds": {"type": "int", "default": 3, "description": "最大再分配轮数"},
            },
        ),
    }

    return strategies
