"""TopkDropout 策略实现"""
import copy
import numpy as np
import pandas as pd
from typing import List, Dict
from loguru import logger

from qlib.backtest.decision import Order, OrderDir, TradeDecisionWO
from qlib.backtest.position import Position
from .base_strategy import BaseStrategy


class TopkDropoutStrategy(BaseStrategy):
    """
    标准 TopkDropout 策略

    每次调仓替换评分最低的 n_drop 只股票
    """

    def generate_trade_decision(self, execute_result=None) -> TradeDecisionWO:
        """
        生成交易决策
        """
        # 获取交易时间信息
        trade_start_time, trade_end_time, pred_start_time, pred_end_time = self.get_trade_step_info()

        # 获取预测信号
        pred_score = self.get_prediction_signal(pred_start_time, pred_end_time)

        if pred_score is None:
            return TradeDecisionWO([], self)

        # 复制当前持仓用于模拟
        current_temp: Position = copy.deepcopy(self.trade_position)

        # 获取当前持仓列表和现金
        current_stock_list = current_temp.get_stock_list()
        cash = current_temp.get_cash()

        self.log_message(f"Initial cash (before sell orders): {cash:,.2f} 元")

        # 股票选择逻辑
        if self.only_tradable:
            def get_first_n(li, n, reverse=False):
                cur_n = 0
                res = []
                for si in reversed(li) if reverse else li:
                    if self.trade_exchange.is_stock_tradable(
                        stock_id=si,
                        start_time=trade_start_time,
                        end_time=trade_end_time,
                    ):
                        res.append(si)
                        cur_n += 1
                        if cur_n >= n:
                            break
                return res[::-1] if reverse else res

            def get_last_n(li, n):
                return get_first_n(li, n, reverse=True)

            def filter_stock(li):
                return [
                    si
                    for si in li
                    if self.trade_exchange.is_stock_tradable(
                        stock_id=si,
                        start_time=trade_start_time,
                        end_time=trade_end_time,
                    )
                ]
        else:
            def get_first_n(li, n):
                return list(li)[:n]

            def get_last_n(li, n):
                return list(li)[-n:]

            def filter_stock(li):
                return li

        # 当前持仓（按评分排序）
        last = pred_score.reindex(current_stock_list).sort_values(ascending=False).index

        # 今天的买入候选股票
        if self.method_buy == "top":
            today = get_first_n(
                pred_score[~pred_score.index.isin(last)]
                .sort_values(ascending=False)
                .index,
                self.n_drop + self.topk - len(last),
            )
        elif self.method_buy == "random":
            topk_candi = get_first_n(
                pred_score.sort_values(ascending=False).index, self.topk
            )
            candi = list(filter(lambda x: x not in last, topk_candi))
            n = self.n_drop + self.topk - len(last)
            try:
                today = np.random.choice(candi, n, replace=False)
            except ValueError:
                today = candi
        else:
            raise NotImplementedError(f"Method buy not supported: {self.method_buy}")

        # 合并新股票和持仓股票，然后从中选择卖出股票
        comb = (
            pred_score.reindex(last.union(pd.Index(today)))
            .sort_values(ascending=False)
            .index
        )

        # 选择卖出的股票
        if self.method_sell == "bottom":
            sell = last[last.isin(get_last_n(comb, self.n_drop))]
        elif self.method_sell == "random":
            candi = filter_stock(last)
            try:
                sell = pd.Index(
                    np.random.choice(candi, self.n_drop, replace=False)
                    if len(last)
                    else []
                )
            except ValueError:
                sell = candi
        else:
            raise NotImplementedError(f"Method sell not supported: {self.method_sell}")

        # 选择买入的股票
        buy = today[: len(sell) + self.topk - len(last)]

        # 生成卖出订单
        sell_order_list = []
        buy_order_list = []

        total_sell_value = 0.0
        total_sell_cost = 0.0

        for code in current_stock_list:
            # 检查是否可交易
            if not self.trade_exchange.is_stock_tradable(
                stock_id=code,
                start_time=trade_start_time,
                end_time=trade_end_time,
                direction=None if self.forbid_all_trade_at_limit else OrderDir.SELL,
            ):
                continue

            if code in sell:
                # 检查持有期限
                time_per_step = self.trade_calendar.get_freq()
                if (
                    current_temp.get_stock_count(code, bar=time_per_step)
                    < self.hold_thresh
                ):
                    continue

                # 创建卖出订单
                sell_amount = current_temp.get_stock_amount(code=code)
                sell_order = Order(
                    stock_id=code,
                    amount=sell_amount,
                    start_time=trade_start_time,
                    end_time=trade_end_time,
                    direction=Order.SELL,
                )

                # 检查订单是否可执行
                if self.trade_exchange.check_order(sell_order):
                    sell_order_list.append(sell_order)
                    trade_val, trade_cost, trade_price = self.trade_exchange.deal_order(
                        sell_order, position=current_temp
                    )
                    cash += trade_val - trade_cost
                    total_sell_value += trade_val
                    total_sell_cost += trade_cost

        self.log_message(f"Sell orders total value: {total_sell_value:,.2f} 元")
        self.log_message(f"Sell orders total cost: {total_sell_cost:,.2f} 元")
        self.log_message(f"Cash after sell orders: {cash:,.2f} 元")

        # 生成买入订单（等权分配）
        if len(buy) > 0:
            value = cash * 0.95 / len(buy)  # 95% 仓位
            for code in buy:
                # 检查是否可交易
                if not self.trade_exchange.is_stock_tradable(
                    stock_id=code,
                    start_time=trade_start_time,
                    end_time=trade_end_time,
                    direction=None if self.forbid_all_trade_at_limit else OrderDir.BUY,
                ):
                    continue

                # 获取买入价格
                buy_price = self.trade_exchange.get_deal_price(
                    stock_id=code,
                    start_time=trade_start_time,
                    end_time=trade_end_time,
                    direction=OrderDir.BUY,
                )

                # 计算买入数量
                buy_amount = value / buy_price

                # 获取复权因子并舍入到交易单位
                factor = self.trade_exchange.get_factor(
                    stock_id=code,
                    start_time=trade_start_time,
                    end_time=trade_end_time,
                )
                buy_amount = self.trade_exchange.round_amount_by_trade_unit(
                    buy_amount, factor
                )

                # 创建买入订单
                buy_order = Order(
                    stock_id=code,
                    amount=buy_amount,
                    start_time=trade_start_time,
                    end_time=trade_end_time,
                    direction=Order.BUY,
                )
                buy_order_list.append(buy_order)

        self.log_message(f"Total buy orders: {len(buy_order_list)}")
        self.log_message(f"Total sell orders: {len(sell_order_list)}")

        return TradeDecisionWO(sell_order_list + buy_order_list, self)
