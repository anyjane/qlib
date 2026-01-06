"""交易日志记录器"""
from typing import Dict, List
from datetime import datetime
from loguru import logger

from .type_defs import (
    DailyTradeLog,
    BuyDetail,
    SellDetail,
    PositionDetail,
    TopStock,
    EquityPoint,
)


class TradeLogger:
    """
    交易日志记录器

    记录回测过程中的每笔交易详细信息
    """

    def __init__(self):
        """初始化交易日志记录器"""
        self.trade_logs: List[DailyTradeLog] = []
        self.equity_curve: List[EquityPoint] = []
        self.current_date = None
        self.current_log = None

    def start_day(self, date: str):
        """
        开始新的一天

        Args:
            date: 交易日期
        """
        self.current_date = date
        self.current_log = DailyTradeLog(
            trade_date=date,
            top_stocks=[],
            current_positions=[],
            buys=[],
            sells=[],
            cash_before=0.0,
            cash_after=0.0,
            total_value=0.0,
        )
        logger.info(f"=== Start trading day: {date} ===")

    def record_top_stocks(self, top_stocks: List[Dict]):
        """
        记录预测得分最高的股票

        Args:
            top_stocks: 股票信息列表 [{"code": "sh600000", "score": 0.1234, "rank": 1}, ...]
        """
        self.current_log.top_stocks = [
            TopStock(
                code=stock["code"],
                name=stock.get("name"),
                prediction_score=stock["score"],
                rank=stock["rank"],
            )
            for stock in top_stocks
        ]
        logger.info(f"Recorded {len(top_stocks)} top stocks")

    def record_positions(self, positions: List[Dict]):
        """
        记录当前持仓

        Args:
            positions: 持仓信息列表 [{"code": "sh600000", "amount": 1000, "cost_price": 10.5, "current_price": 11.2, "value": 11200.0, "score": 0.1234, "rank": 10}, ...]
        """
        self.current_log.current_positions = [
            PositionDetail(
                code=pos["code"],
                name=pos.get("name"),
                prediction_score=pos.get("score", 0.0),
                rank=pos.get("rank", 0),
                amount=pos["amount"],
                cost_price=pos["cost_price"],
                current_price=pos["current_price"],
                value=pos["value"],
            )
            for pos in positions
        ]
        logger.info(f"Recorded {len(positions)} current positions")

    def record_buy(self, buy: Dict):
        """
        记录买入操作

        Args:
            buy: 买入信息 {
                "code": "sh600000",
                "name": "浦发银行",
                "score": 0.1234,
                "amount": 1000,
                "price": 11.2,
                "value": 11200.0,
                "commission": 5.6,
                "cash_before": 50000.0,
                "cash_after": 38794.4,
            }
        """
        buy_detail = BuyDetail(
            code=buy["code"],
            name=buy.get("name"),
            prediction_score=buy.get("score", 0.0),
            amount=buy["amount"],
            price=buy["price"],
            value=buy["value"],
            commission=buy["commission"],
            cash_before=buy["cash_before"],
            cash_after=buy["cash_after"],
        )
        self.current_log.buys.append(buy_detail)
        logger.info(
            f"Recorded BUY: {buy['code']} {buy['amount']} shares @ {buy['price']:.2f}, "
            f"value={buy['value']:.2f}, commission={buy['commission']:.2f}"
        )

    def record_sell(self, sell: Dict):
        """
        记录卖出操作

        Args:
            sell: 卖出信息 {
                "code": "sh600000",
                "name": "浦发银行",
                "score": 0.0567,
                "amount": 1000,
                "price": 11.5,
                "value": 11500.0,
                "commission": 17.25,
                "actual_received": 11482.75,
                "cash_before": 38794.4,
                "cash_after": 50277.15,
            }
        """
        sell_detail = SellDetail(
            code=sell["code"],
            name=sell.get("name"),
            prediction_score=sell.get("score", 0.0),
            amount=sell["amount"],
            price=sell["price"],
            value=sell["value"],
            commission=sell["commission"],
            actual_received=sell["actual_received"],
            cash_before=sell["cash_before"],
            cash_after=sell["cash_after"],
        )
        self.current_log.sells.append(sell_detail)
        logger.info(
            f"Recorded SELL: {sell['code']} {sell['amount']} shares @ {sell['price']:.2f}, "
            f"value={sell['value']:.2f}, commission={sell['commission']:.2f}, "
            f"received={sell['actual_received']:.2f}"
        )

    def record_cash(self, cash_before: float, cash_after: float, total_value: float):
        """
        记录资金信息

        Args:
            cash_before: 交易前现金
            cash_after: 交易后现金
            total_value: 总资产
        """
        self.current_log.cash_before = cash_before
        self.current_log.cash_after = cash_after
        self.current_log.total_value = total_value
        logger.info(
            f"Recorded cash: before={cash_before:.2f}, after={cash_after:.2f}, total={total_value:.2f}"
        )

    def end_day(self):
        """结束当天交易"""
        if self.current_log:
            self.trade_logs.append(self.current_log)
            logger.info(f"=== End trading day: {self.current_date} ===")

        self.current_date = None
        self.current_log = None

    def add_equity_point(self, date: str, cash: float, stock_value: float, total_value: float):
        """
        添加资金曲线点

        Args:
            date: 日期
            cash: 现金
            stock_value: 股票市值
            total_value: 总资产
        """
        equity_point = EquityPoint(
            date=date,
            cash=cash,
            stock_value=stock_value,
            total_value=total_value,
        )
        self.equity_curve.append(equity_point)

    def get_trade_logs(self) -> List[DailyTradeLog]:
        """
        获取所有交易日志

        Returns:
            交易日志列表
        """
        return self.trade_logs

    def get_equity_curve(self) -> List[EquityPoint]:
        """
        获取资金曲线

        Returns:
            资金曲线点列表
        """
        return self.equity_curve

    def get_summary(self) -> Dict:
        """
        获取交易摘要

        Returns:
            交易摘要字典
        """
        if not self.trade_logs:
            return {
                "total_days": 0,
                "total_buys": 0,
                "total_sells": 0,
                "total_trades": 0,
            }

        total_buys = sum(len(log.buys) for log in self.trade_logs)
        total_sells = sum(len(log.sells) for log in self.trade_logs)

        return {
            "total_days": len(self.trade_logs),
            "total_buys": total_buys,
            "total_sells": total_sells,
            "total_trades": total_buys + total_sells,
        }

    def clear(self):
        """清空所有日志"""
        self.trade_logs = []
        self.equity_curve = []
        self.current_date = None
        self.current_log = None
        logger.info("Trade logger cleared")
