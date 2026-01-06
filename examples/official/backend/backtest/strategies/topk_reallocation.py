"""TopkReallocation 策略实现（带资金再分配）"""
import copy
import numpy as np
import pandas as pd
from typing import Dict, List
from loguru import logger

from qlib.backtest.decision import Order, OrderDir, TradeDecisionWO
from qlib.backtest.position import Position
from .topk_dropout import TopkDropoutStrategy


class TopkReallocationStrategy(TopkDropoutStrategy):
    """
    带资金再分配的 TopkDropout 策略

    在原始 TopkDropout 策略基础上，支持将剩余资金（因舍入产生的）
    重新分配给低价股，提高资金利用率。

    当 max_reallocation_rounds=0 时，行为与原始 TopkDropoutStrategy 完全一致。
    """

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
        max_reallocation_rounds: int = 3,
        log_prediction_details: bool = False,
        **kwargs,
    ):
        super().__init__(
            topk=topk,
            n_drop=n_drop,
            method_sell=method_sell,
            method_buy=method_buy,
            hold_thresh=hold_thresh,
            only_tradable=only_tradable,
            forbid_all_trade_at_limit=forbid_all_trade_at_limit,
            verbose=verbose,
            log_prediction_details=log_prediction_details,
            **kwargs,
        )
        self.max_reallocation_rounds = max_reallocation_rounds
        self._trade_unit = 100  # A股最小交易单位

    def generate_trade_decision(self, execute_result=None) -> TradeDecisionWO:
        """
        生成交易决策（带资金再分配）
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

        # 记录详细预测信息
        if self.log_prediction_details:
            self._log_prediction_details(trade_start_time, pred_score, current_stock_list)

        # 股票选择逻辑（与父类相同）
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

        # 生成买入订单
        if self.max_reallocation_rounds == 0:
            # 原始策略：等权分配
            if len(buy) > 0:
                value = cash * 0.95 / len(buy)
                for code in buy:
                    if not self.trade_exchange.is_stock_tradable(
                        stock_id=code,
                        start_time=trade_start_time,
                        end_time=trade_end_time,
                        direction=None if self.forbid_all_trade_at_limit else OrderDir.BUY,
                    ):
                        continue

                    buy_price = self.trade_exchange.get_deal_price(
                        stock_id=code,
                        start_time=trade_start_time,
                        end_time=trade_end_time,
                        direction=OrderDir.BUY,
                    )
                    buy_amount = value / buy_price
                    factor = self.trade_exchange.get_factor(
                        stock_id=code,
                        start_time=trade_start_time,
                        end_time=trade_end_time,
                    )
                    buy_amount = self.trade_exchange.round_amount_by_trade_unit(
                        buy_amount, factor
                    )
                    buy_order = Order(
                        stock_id=code,
                        amount=buy_amount,
                        start_time=trade_start_time,
                        end_time=trade_end_time,
                        direction=Order.BUY,
                    )
                    buy_order_list.append(buy_order)
        else:
            # 新策略：资金再分配
            # 获取买入股票价格
            prices = {}
            for stock_id in buy:
                try:
                    price = self.trade_exchange.get_deal_price(
                        stock_id=stock_id,
                        start_time=trade_start_time,
                        end_time=trade_end_time,
                        direction=OrderDir.BUY,
                    )
                    prices[stock_id] = price if price is not None else 0.0
                except:
                    prices[stock_id] = 0.0

            # 分配资金（带再分配）
            buy_amounts = self._allocate_to_buy_stocks(
                buy_list=buy,
                prices=prices,
                cash=cash,
                trade_start_time=trade_start_time,
                trade_end_time=trade_end_time,
            )

            # 生成买入订单
            for stock_id, target_amount in buy_amounts.items():
                if not self.trade_exchange.is_stock_tradable(
                    stock_id=stock_id,
                    start_time=trade_start_time,
                    end_time=trade_end_time,
                    direction=None if self.forbid_all_trade_at_limit else OrderDir.BUY,
                ):
                    continue

                buy_order = Order(
                    stock_id=stock_id,
                    amount=target_amount,
                    start_time=trade_start_time,
                    end_time=trade_end_time,
                    direction=Order.BUY,
                )
                buy_order_list.append(buy_order)

        self.log_message(f"Total buy orders: {len(buy_order_list)}")
        self.log_message(f"Total sell orders: {len(sell_order_list)}")

        return TradeDecisionWO(sell_order_list + buy_order_list, self)

    def _allocate_to_buy_stocks(
        self,
        buy_list: List[str],
        prices: Dict[str, float],
        cash: float,
        trade_start_time: pd.Timestamp,
        trade_end_time: pd.Timestamp,
    ) -> Dict[str, float]:
        """
        分配资金给买入股票（支持再分配）

        Args:
            buy_list: 买入股票列表
            prices: 股票价格字典
            cash: 可用现金
            trade_start_time: 交易开始时间
            trade_end_time: 交易结束时间

        Returns:
            {stock_id: amount} 分配数量字典
        """
        if not buy_list:
            return {}

        # 等权分配
        value = cash * 0.95 / len(buy_list)

        if self.verbose and self.max_reallocation_rounds > 0:
            logger.info(f"=== Capital Allocation (Date: {trade_start_time.strftime('%Y-%m-%d')}) ===")
            logger.info(f"  Available cash: {cash:,.2f} 元")
            logger.info(f"  Cash for buying: {cash * 0.95:,.2f} 元 (95% position)")
            logger.info(f"  Number of buy stocks: {len(buy_list)}")
            logger.info(f"  Value per stock: {value:,.2f} 元")

        # 第一轮：独立舍入
        actual_amounts = {}
        target_amounts = {}
        total_actual_value = 0.0

        for stock_id in buy_list:
            price = prices.get(stock_id, 0)
            if price is None or price <= 0:
                continue

            # 计算目标数量
            target_amount = value / price
            target_amounts[stock_id] = target_amount

            # 舍入到交易单位
            factor = self.trade_exchange.get_factor(
                stock_id=stock_id,
                start_time=trade_start_time,
                end_time=trade_end_time,
            )
            actual_amount = self.trade_exchange.round_amount_by_trade_unit(
                target_amount, factor
            )

            actual_amounts[stock_id] = actual_amount
            total_actual_value += actual_amount * price

        # 计算剩余现金
        total_cash_for_buy = cash * 0.95
        remaining_cash = total_cash_for_buy - total_actual_value

        if self.verbose and self.max_reallocation_rounds > 0:
            logger.info(f"First Round Allocation:")
            logger.info(f"  Total value: {total_actual_value:,.2f} 元")
            logger.info(f"  Remaining cash: {remaining_cash:,.2f} 元")

        # 资金再分配轮次
        if self.max_reallocation_rounds > 0 and remaining_cash > 100:
            # 按价格升序排序（优先低价股）
            stock_prices = [
                (stock_id, prices.get(stock_id, float("inf")))
                for stock_id in buy_list
                if stock_id in prices
                and prices.get(stock_id) is not None
                and prices.get(stock_id, 0) > 0
            ]
            stock_prices.sort(key=lambda x: x[1])

            redistribution_round = 0
            while (
                remaining_cash > 0
                and redistribution_round < self.max_reallocation_rounds
            ):
                redistribution_round += 1
                redistributed_this_round = False

                for stock_id, price in stock_prices:
                    if remaining_cash < price * self._trade_unit:
                        continue

                    # 计算可买入的手数
                    additional_shares = int(remaining_cash / (price * self._trade_unit))
                    additional_shares = max(1, additional_shares)

                    # 更新分配
                    current_amount = actual_amounts.get(stock_id, 0)
                    additional_amount = additional_shares * self._trade_unit
                    new_amount = current_amount + additional_amount
                    actual_amounts[stock_id] = new_amount
                    used_cash = additional_amount * price
                    remaining_cash -= used_cash
                    total_actual_value += used_cash
                    redistributed_this_round = True

                    if self.verbose:
                        logger.info(
                            f"  Round {redistribution_round}: "
                            f"Allocated {used_cash:,.2f} to {stock_id} (price: {price:.2f})"
                        )

                if not redistributed_this_round:
                    break

        if self.verbose and self.max_reallocation_rounds > 0:
            logger.info(f"Final Allocation:")
            logger.info(f"  Total value: {total_actual_value:,.2f} 元")
            logger.info(f"  Remaining cash: {remaining_cash:,.2f} 元")
            logger.info(f"  Utilization: {(total_actual_value / total_cash_for_buy * 100):.2f}%")

        return actual_amounts

    def _log_prediction_details(
        self,
        trade_start_time: pd.Timestamp,
        pred_score: pd.Series,
        current_stock_list: List[str],
    ):
        """
        记录详细预测信息

        Args:
            trade_start_time: 交易开始时间
            pred_score: 预测得分
            current_stock_list: 当前持仓列表
        """
        logger.info("=" * 80)
        logger.info(f"Prediction Details for {trade_start_time.date()}:")
        logger.info("=" * 80)

        # 预测统计
        logger.info("Prediction Statistics:")
        logger.info(f"  Total Predictions: {len(pred_score)}")
        logger.info(f"  Max Score: {pred_score.max():.4f}")
        logger.info(f"  Min Score: {pred_score.min():.4f}")
        logger.info(f"  Mean Score: {pred_score.mean():.4f}")
        logger.info(f"  Median Score: {pred_score.median():.4f}")
        logger.info(f"  Std Dev: {pred_score.std():.4f}")

        # TopK 股票
        topk_stocks = pred_score.sort_values(ascending=False).head(self.topk)
        logger.info(f"\nTop {self.topk} Stocks by Prediction Score:")
        for rank, (stock_id, score) in enumerate(topk_stocks.items(), 1):
            logger.info(f"  [{rank:2d}] {stock_id}: {score:.4f}")

        # 当前持仓
        logger.info(f"\nCurrent Holdings ({len(current_stock_list)} stocks):")
        if current_stock_list:
            held_scores = pred_score.reindex(current_stock_list).sort_values(ascending=False)
            for stock_id, score in held_scores.items():
                if pd.notna(score):
                    rank = (pred_score > score).sum() + 1
                    logger.info(f"  {stock_id}: {score:.4f} (Rank: {int(rank)})")
        else:
            logger.info("  No holdings")

        logger.info("=" * 80)
