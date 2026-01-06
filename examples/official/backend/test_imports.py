#!/usr/bin/env python3
"""测试所有导入是否正常工作"""
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print("Testing imports...")

try:
    # 测试类型导入
    from backtest.type_defs import (
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
        BacktestRequest,
        BacktestResponse,
        StrategyInfo,
    )
    print("✓ Type definitions imported successfully")
    
    # 测试组件导入
    from backtest import (
        BacktestService,
        FeaturesDataLoader,
        TradeLogger,
        BaseStrategy,
        TopkDropoutStrategy,
        TopkReallocationStrategy,
        create_strategy,
        get_available_strategies,
    )
    print("✓ Components imported successfully")
    
    # 测试策略创建
    strategy = create_strategy(
        strategy_type=StrategyType.TOPK_DROPOUT,
        topk=50,
        n_drop=5,
    )
    print(f"✓ Strategy created: {strategy.__class__.__name__}")
    
    # 测试配置创建
    config = BacktestConfig(
        initial_capital=100.0,
        market="csi300",
        train_start="2020-01-01",
        train_end="2024-12-31",
        test_start="2025-01-01",
        test_end="2025-12-30",
        strategy_type=StrategyType.TOPK_REALLOCATION,
    )
    print(f"✓ Config created: {config.strategy_type}")
    
    # 测试 API 导入
    from api.backtest_enhanced import router
    print("✓ API router imported successfully")
    
    print("\n✅ All imports and basic functionality working!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
