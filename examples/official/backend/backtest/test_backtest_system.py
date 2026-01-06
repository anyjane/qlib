"""回测系统测试脚本"""
import sys
import asyncio
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backtest import BacktestConfig, StrategyType, MethodType, BacktestService
from types.backtest_types import BacktestConfig
from loguru import logger


def test_types():
    """测试类型定义"""
    logger.info("Testing type definitions...")

    # 测试 BacktestConfig
    config = BacktestConfig(
        initial_capital=100.0,
        market="csi300",
        train_start="2020-01-01",
        train_end="2024-12-31",
        test_start="2025-01-01",
        test_end="2025-12-30",
        strategy_type=StrategyType.TOPK_REALLOCATION,
        topk=50,
        n_drop=5,
        buy_rate=0.0005,
        sell_rate=0.0015,
        min_commission=5.0,
    )

    logger.info(f"Config created: {config.strategy_type}")
    logger.info("Type definitions test passed ✓")


def test_strategies():
    """测试策略创建"""
    logger.info("Testing strategy creation...")

    from backtest.strategies import create_strategy, StrategyType

    # 测试 TopkDropoutStrategy
    strategy1 = create_strategy(
        strategy_type=StrategyType.TOPK_DROPOUT,
        topk=50,
        n_drop=5,
        verbose=True,
    )
    logger.info(f"Created strategy: {strategy1.__class__.__name__}")

    # 测试 TopkReallocationStrategy
    strategy2 = create_strategy(
        strategy_type=StrategyType.TOPK_REALLOCATION,
        topk=50,
        n_drop=5,
        max_reallocation_rounds=3,
        verbose=True,
    )
    logger.info(f"Created strategy: {strategy2.__class__.__name__}")

    logger.info("Strategy creation test passed ✓")


def test_data_loader():
    """测试数据加载器"""
    logger.info("Testing data loader...")

    from backtest.data_loader import FeaturesDataLoader
    from config import settings

    loader = FeaturesDataLoader(settings.QLIB_PROVIDER_URI)

    # 测试加载交易日历
    calendar = loader.load_calendar()
    logger.info(f"Loaded {len(calendar)} trading days")

    # 测试加载股票池
    instruments = loader.load_instruments("csi300")
    logger.info(f"Loaded {len(instruments)} instruments")

    # 测试加载股票数据
    if instruments:
        stock_code = instruments[0]
        stock_data = loader.load_stock_data(stock_code)
        logger.info(f"Loaded data for {stock_code}: {list(stock_data.keys())}")

    logger.info("Data loader test passed ✓")


def test_trade_logger():
    """测试交易日志记录器"""
    logger.info("Testing trade logger...")

    from backtest.trade_logger import TradeLogger

    logger_obj = TradeLogger()

    # 测试记录交易
    logger_obj.start_day("2025-01-01")

    logger_obj.record_buy({
        "code": "sh600000",
        "name": "浦发银行",
        "score": 0.1234,
        "amount": 1000,
        "price": 10.5,
        "value": 10500.0,
        "commission": 5.25,
        "cash_before": 100000.0,
        "cash_after": 89494.75,
    })

    logger_obj.record_sell({
        "code": "sh600004",
        "name": "白云机场",
        "score": 0.0567,
        "amount": 500,
        "price": 15.2,
        "value": 7600.0,
        "commission": 11.4,
        "actual_received": 7588.6,
        "cash_before": 89494.75,
        "cash_after": 97083.35,
    })

    logger_obj.record_cash(100000.0, 97083.35, 200000.0)
    logger_obj.end_day()

    # 测试获取日志
    logs = logger_obj.get_trade_logs()
    logger.info(f"Recorded {len(logs)} daily logs")

    summary = logger_obj.get_summary()
    logger.info(f"Summary: {summary}")

    logger.info("Trade logger test passed ✓")


async def test_api_integration():
    """测试 API 集成"""
    logger.info("Testing API integration...")

    from config import settings

    # 测试数据库连接
    from database import MongoDB
    await MongoDB.connect_to_mongodb()

    # 测试插入测试数据
    test_result = {
        "task_id": "test_001",
        "experiment_name": "test_experiment",
        "config": {"initial_capital": 100.0},
        "metrics": {
            "annual_return_with_cost": 0.15,
            "sharpe_ratio_with_cost": 1.5,
            "max_drawdown_with_cost": 0.1,
            "total_trades": 100,
            "initial_capital": 1000000.0,
            "final_capital": 1150000.0,
            "total_return": 0.15,
        },
        "trade_logs": [],
        "equity_curve": [],
        "created_at": "2025-01-01T00:00:00",
    }

    await MongoDB.insert_backtest_result(test_result)
    logger.info("Inserted test backtest result")

    # 测试查询
    result = await MongoDB.get_backtest_result("test_001")
    logger.info(f"Retrieved backtest result: {result is not None}")

    # 清理测试数据
    await MongoDB.delete_backtest_result("test_001")
    logger.info("Deleted test backtest result")

    await MongoDB.close_mongodb()
    logger.info("API integration test passed ✓")


def main():
    """主测试函数"""
    logger.info("=" * 80)
    logger.info("STARTING BACKTEST SYSTEM TESTS")
    logger.info("=" * 80)

    try:
        # 测试类型定义
        test_types()

        # 测试策略创建
        test_strategies()

        # 测试数据加载器
        test_data_loader()

        # 测试交易日志记录器
        test_trade_logger()

        # 测试 API 集成
        asyncio.run(test_api_integration())

        logger.info("=" * 80)
        logger.info("ALL TESTS PASSED ✓")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
