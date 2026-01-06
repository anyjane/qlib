"""策略基类"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
import pandas as pd
from qlib.backtest.decision import Order, OrderDir, TradeDecisionWO
from qlib.backtest.position import Position


class BaseStrategy(ABC):
    """策略基类"""

    def __init__(
        self,
        *,
        topk: int,
        n_drop: int,
        method_sell: str = "bottom",
        method_buy: str = "top",
        hold_thresh: int = 1,
        only_tradable: bool = False,
        forbid_all_trade_at_limit: bool = True,
        verbose: bool = True,
        log_prediction_details: bool = False,
        **kwargs,
    ):
        """
        初始化策略

        Args:
            topk: 持仓数量
            n_drop: 每次调仓替换的股票数
            method_sell: 卖出方法（bottom/random）
            method_buy: 买入方法（top/random）
            hold_thresh: 持仓最小天数
            only_tradable: 是否只考虑可交易股票
            forbid_all_trade_at_limit: 涨跌停是否禁止交易
            verbose: 是否输出详细日志
            log_prediction_details: 是否输出预测详情
            **kwargs: 其他参数
        """
        self.topk = topk
        self.n_drop = n_drop
        self.method_sell = method_sell
        self.method_buy = method_buy
        self.hold_thresh = hold_thresh
        self.only_tradable = only_tradable
        self.forbid_all_trade_at_limit = forbid_all_trade_at_limit
        self.verbose = verbose
        self.log_prediction_details = log_prediction_details

        # 将由回测引擎设置
        self.trade_exchange = None
        self.trade_calendar = None
        self.trade_position = None
        self.signal = None

    def setup(self, exchange, calendar, position, signal):
        """
        设置策略依赖组件

        Args:
            exchange: 交易所对象
            calendar: 交易日历对象
            position: 持仓对象
            signal: 预测信号对象
        """
        self.trade_exchange = exchange
        self.trade_calendar = calendar
        self.trade_position = position
        self.signal = signal

    @abstractmethod
    def generate_trade_decision(self, execute_result=None) -> TradeDecisionWO:
        """
        生成交易决策

        Args:
            execute_result: 上次执行结果

        Returns:
            交易决策对象
        """
        pass

    def get_trade_step_info(self) -> Tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]:
        """
        获取交易步信息

        Returns:
            (trade_start_time, trade_end_time, pred_start_time, pred_end_time)
        """
        trade_step = self.trade_calendar.get_trade_step()
        trade_start_time, trade_end_time = self.trade_calendar.get_step_time(trade_step)
        pred_start_time, pred_end_time = self.trade_calendar.get_step_time(trade_step, shift=1)
        return trade_start_time, trade_end_time, pred_start_time, pred_end_time

    def get_prediction_signal(self, start_time: pd.Timestamp, end_time: pd.Timestamp):
        """
        获取预测信号

        Args:
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            预测信号
        """
        pred_score = self.signal.get_signal(start_time=start_time, end_time=end_time)
        if isinstance(pred_score, pd.DataFrame):
            pred_score = pred_score.iloc[:, 0]
        return pred_score

    def _filter_tradable_stocks(self, stocks: List[str], direction: Optional[str] = None) -> List[str]:
        """
        过滤可交易股票

        Args:
            stocks: 股票列表
            direction: 方向（buy/sell）

        Returns:
            可交易的股票列表
        """
        if not self.only_tradable:
            return stocks

        trade_start_time, trade_end_time, _, _ = self.get_trade_step_info()

        tradable = []
        for stock_id in stocks:
            direction_param = (
                None if self.forbid_all_trade_at_limit else
                OrderDir.BUY if direction == "buy" else
                OrderDir.SELL if direction == "sell" else
                None
            )

            if self.trade_exchange.is_stock_tradable(
                stock_id=stock_id,
                start_time=trade_start_time,
                end_time=trade_end_time,
                direction=direction_param,
            ):
                tradable.append(stock_id)

        return tradable

    def log_message(self, message: str):
        """
        记录日志消息

        Args:
            message: 消息内容
        """
        if self.verbose:
            from loguru import logger
            logger.info(message)
