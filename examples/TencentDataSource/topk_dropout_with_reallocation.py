# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
TopkDropoutStrategy with capital reallocation
=============================================

Enhanced version of TopkDropoutStrategy that reallocates unused capital
from rounding (100-share minimum) to maximize capital utilization.

Features:
- Equal capital allocation (same as TopkDropoutStrategy)
- Independent rounding (each stock rounded down to 100-share units)
- Capital reallocation (remaining capital redistributed to low-price stocks)
- High capital utilization (99%+ vs 94% in original)

IMPORTANT: When max_reallocation_rounds=0, this strategy behaves
EXACTLY the same as the original TopkDropoutStrategy.
"""

import copy
import numpy as np
import pandas as pd
from typing import Dict, List
from tencent_data_source import logger
from qlib.contrib.strategy.signal_strategy import TopkDropoutStrategy
from qlib.backtest.decision import Order, OrderDir, TradeDecisionWO
from qlib.backtest.position import Position


class TopkDropoutWithReallocation(TopkDropoutStrategy):
    """
    Enhanced TopkDropoutStrategy with capital reallocation

    This strategy extends TopkDropoutStrategy by reallocating unused capital
    caused by rounding to 100-share minimum units.

    When max_reallocation_rounds=0, it behaves EXACTLY the same as the original
    TopkDropoutStrategy. When max_reallocation_rounds>0, it redistributes
    remaining capital from rounding to maximize utilization.

    Algorithm:
    1. Use same stock selection logic as TopkDropoutStrategy
    2. Allocate equal cash to each stock in "buy" list (NEW stocks only)
    3. Round down to 100-share units
    4. If max_reallocation_rounds>0: redistribute remaining cash to buy stocks
    5. If max_reallocation_rounds=0: behave exactly like original

    Example (100万 capital, 52 stocks, avg price 19.15元):
        - Original: 94.56% utilization, 51,637元 remaining
        - With reallocation: 99.88% utilization, 1,122元 remaining

    Parameters
    ----------
    topk : int
        Number of stocks to hold in portfolio
    n_drop : int
        Number of stocks to replace each rebalance
    method_sell : str, default "bottom"
        Method to select stocks to sell: "bottom" or "random"
    method_buy : str, default "top"
        Method to select stocks to buy: "top" or "random"
    hold_thresh : int, default 1
        Minimum holding period (in days)
    only_tradable : bool, default False
        Only consider tradable stocks
    forbid_all_trade_at_limit : bool, default True
        Forbid all trades when stock hits limit up/down
    verbose : bool, default True
        Print capital utilization statistics
    max_reallocation_rounds : int, default 3
        Maximum number of reallocation rounds (0 = disable, behave like original)
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
            **kwargs,
        )

        self.verbose = verbose
        self.max_reallocation_rounds = max_reallocation_rounds
        self._trade_unit = 100  # Minimum trading unit for Chinese A-shares

    def _allocate_to_buy_stocks(
        self,
        buy_list: List[str],
        prices: Dict[str, float],
        cash: float,
        trade_start_time: pd.Timestamp,
        trade_end_time: pd.Timestamp,
    ) -> Dict[str, float]:
        """
        Allocate cash to buy stocks with optional reallocation

        Parameters
        ----------
        buy_list : List[str]
            List of stock IDs to buy (NEW stocks only)
        prices : Dict[str, float]
            Stock prices
        cash : float
            Available cash
        trade_start_time : pd.Timestamp
            Trade start time
        trade_end_time : pd.Timestamp
            Trade end time

        Returns
        -------
        Dict[str, float]
            {stock_id: amount}
        """
        if not buy_list:
            return {}

        # Equal allocation (same as original strategy)
        value = cash * self.risk_degree / len(buy_list)

        if self.verbose and self.max_reallocation_rounds > 0:
            logger.info(
                f"=== Capital Allocation (Date: {trade_start_time.strftime('%Y-%m-%d')}) ==="
            )
            logger.info(f"  Available cash: {cash:,.2f} 元")
            logger.info(
                f"  Cash for buying: {cash * self.risk_degree:,.2f} 元 (risk_degree={self.risk_degree})"
            )
            logger.info(f"  Number of buy stocks: {len(buy_list)}")
            logger.info(f"  Buy stocks: {', '.join(buy_list)}")
            logger.info(f"  Value per stock: {value:,.2f} 元")

        # First round: equal allocation with independent rounding
        actual_amounts = {}
        target_amounts = {}
        total_actual_value = 0.0
        prices_series = pd.Series(prices)

        for stock_id in buy_list:
            price = prices.get(stock_id, 0)
            # Handle None or invalid prices
            if price is None or price <= 0:
                continue

            # Calculate target amount
            target_amount = value / price
            target_amounts[stock_id] = target_amount

            # Round to trade unit (100 shares)
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

        # Calculate remaining cash after first round
        total_cash_for_buy = cash * self.risk_degree
        remaining_cash = total_cash_for_buy - total_actual_value

        if self.verbose and self.max_reallocation_rounds > 0:
            logger.info(f"First Round Allocation:")
            logger.info(f"  Total value: {total_actual_value:,.2f} 元")
            logger.info(f"  Remaining cash: {remaining_cash:,.2f} 元")
            
            # Print detailed buy information
            logger.info(f"  Stock Details:")
            logger.info(f"  {'Stock ID':<12} {'Price':<10} {'Target Amount':<15} {'Actual Amount':<15} {'Value':<15}")
            logger.info(f"  {'-' * 12} {'-' * 10} {'-' * 15} {'-' * 15} {'-' * 15}")
            for stock_id in sorted(actual_amounts.keys()):
                price = prices.get(stock_id, 0)
                target_amt = target_amounts.get(stock_id, 0)
                actual_amt = actual_amounts[stock_id]
                value = actual_amt * price
                logger.info(f"  {stock_id:<12} {price:<10.2f} {target_amt:<15.0f} {actual_amt:<15.0f} {value:<15,.2f}")

        # Reallocation rounds (only if max_reallocation_rounds > 0)
        if self.max_reallocation_rounds > 0 and remaining_cash > 100:
            # Sort stocks by price (ascending) to prioritize low-price stocks
            # Filter out invalid prices (None, 0, or negative)
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

                    # Calculate additional shares we can buy with remaining cash
                    additional_shares = int(remaining_cash / (price * self._trade_unit))
                    additional_shares = max(1, additional_shares)

                    # Update allocation
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
                            f"  Round {redistribution_round}: Allocated {used_cash:,.2f} to {stock_id} (price: {price:.2f})"
                        )

                if not redistributed_this_round:
                    break

        if self.verbose and self.max_reallocation_rounds > 0:
            logger.info(f"Final Allocation:")
            logger.info(f"  Total value: {total_actual_value:,.2f} 元")
            logger.info(f"  Remaining cash: {remaining_cash:,.2f} 元")
            logger.info(
                f"  Utilization: {(total_actual_value / total_cash_for_buy * 100):.2f}%"
            )

        return actual_amounts

    def _print_position_info(
        self,
        trade_start_time: pd.Timestamp,
        trade_end_time: pd.Timestamp,
    ):
        """
        Print detailed current position information

        Parameters
        ----------
        trade_start_time : pd.Timestamp
            Trade start time
        trade_end_time : pd.Timestamp
            Trade end time
        """
        # Get current stock list and cash
        stock_list = self.trade_position.get_stock_list()
        cash = self.trade_position.get_cash()

        if not stock_list:
            logger.info(f"=== Current Position (Date: {trade_start_time.strftime('%Y-%m-%d')}) ===")
            logger.info(f"  Cash: {cash:,.2f} 元")
            logger.info(f"  No stocks held")
            return

        # Calculate total position value
        total_stock_value = 0.0
        stock_details = []

        for stock_id in sorted(stock_list):
            # Get stock amount
            amount = self.trade_position.get_stock_amount(code=stock_id)

            # Get stock price
            try:
                price = self.trade_exchange.get_deal_price(
                    stock_id=stock_id,
                    start_time=trade_start_time,
                    end_time=trade_end_time,
                    direction=OrderDir.SELL,  # Use sell price for valuation
                )
                if price is None or price <= 0:
                    price = 0.0
            except:
                price = 0.0

            # Calculate stock value
            stock_value = amount * price
            total_stock_value += stock_value

            stock_details.append({
                'stock_id': stock_id,
                'amount': amount,
                'price': price,
                'value': stock_value,
            })

        # Calculate total portfolio value
        total_value = total_stock_value + cash

        # Print position information
        logger.info(f"=== Current Position (Date: {trade_start_time.strftime('%Y-%m-%d')}) ===")
        logger.info(f"  Total Portfolio Value: {total_value:,.2f} 元")
        logger.info(f"  Cash: {cash:,.2f} 元")
        logger.info(f"  Stock Value: {total_stock_value:,.2f} 元")
        logger.info(f"  Number of Stocks: {len(stock_list)}")
        logger.info(f"  Stock Details:")
        logger.info(f"  {'Stock ID':<12} {'Amount':<12} {'Price':<12} {'Value':<15} {'Pct':<10}")
        logger.info(f"  {'-' * 12} {'-' * 12} {'-' * 12} {'-' * 15} {'-' * 10}")

        for detail in stock_details:
            pct = (detail['value'] / total_stock_value * 100) if total_stock_value > 0 else 0.0
            logger.info(
                f"  {detail['stock_id']:<12} "
                f"{detail['amount']:<12.0f} "
                f"{detail['price']:<12.2f} "
                f"{detail['value']:<15,.2f} "
                f"{pct:<10.2f}%"
            )

        logger.info(f"  {'-' * 12} {'-' * 12} {'-' * 12} {'-' * 15} {'-' * 10}")
        logger.info(f"  {'Total':<12} {len(stock_list):<12} {'':<12} {total_stock_value:<15,.2f} 100.00%")

    def generate_trade_decision(self, execute_result=None):
        """
        Generate trade decisions with capital reallocation

        CRITICAL: When max_reallocation_rounds=0, this behaves EXACTLY
        the same as the original TopkDropoutStrategy.
        """
        # Get trade time information (same as original)
        trade_step = self.trade_calendar.get_trade_step()
        trade_start_time, trade_end_time = self.trade_calendar.get_step_time(trade_step)
        pred_start_time, pred_end_time = self.trade_calendar.get_step_time(
            trade_step, shift=1
        )
        pred_score = self.signal.get_signal(
            start_time=pred_start_time, end_time=pred_end_time
        )

        if isinstance(pred_score, pd.DataFrame):
            pred_score = pred_score.iloc[:, 0]

        if pred_score is None:
            return TradeDecisionWO([], self)

        # Copy current position for simulation (same as original)
        current_temp: Position = copy.deepcopy(self.trade_position)

        # Get current stock list and cash (same as original)
        current_stock_list = current_temp.get_stock_list()
        cash = current_temp.get_cash()
        logger.info(f"Initial cash (before sell orders): {cash:,.2f} 元")

        # Stock selection logic - IDENTICAL to original strategy
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

        # last position (sorted by score) - IDENTICAL to original
        last = pred_score.reindex(current_stock_list).sort_values(ascending=False).index

        # The new stocks today want to buy **at most** - IDENTICAL to original
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
            raise NotImplementedError(f"This type of input is not supported")

        # combine(new stocks + last stocks), we will drop stocks from this list - IDENTICAL
        comb = (
            pred_score.reindex(last.union(pd.Index(today)))
            .sort_values(ascending=False)
            .index
        )

        # Get stock list we really want to sell - IDENTICAL to original
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
            raise NotImplementedError(f"This type of input is not supported")

        # Get stock list we really want to buy - IDENTICAL to original (line 231)
        buy = today[: len(sell) + self.topk - len(last)]

        # Initialize order lists
        sell_order_list = []
        buy_order_list = []

        # Track total sell value for calculating new available cash
        total_sell_value_without_cost = 0.0
        total_sell_value_with_cost = 0.0

        # Generate sell orders - IDENTICAL to original (lines 232-262)
        for code in current_stock_list:
            if not self.trade_exchange.is_stock_tradable(
                stock_id=code,
                start_time=trade_start_time,
                end_time=trade_end_time,
                direction=None if self.forbid_all_trade_at_limit else OrderDir.SELL,
            ):
                continue
            if code in sell:
                # check hold limit
                time_per_step = self.trade_calendar.get_freq()
                if (
                    current_temp.get_stock_count(code, bar=time_per_step)
                    < self.hold_thresh
                ):
                    continue
                # sell order
                sell_amount = current_temp.get_stock_amount(code=code)
                sell_order = Order(
                    stock_id=code,
                    amount=sell_amount,
                    start_time=trade_start_time,
                    end_time=trade_end_time,
                    direction=Order.SELL,
                )
                # is order executable
                if self.trade_exchange.check_order(sell_order):
                    sell_order_list.append(sell_order)
                    trade_val, trade_cost, trade_price = self.trade_exchange.deal_order(
                        sell_order, position=current_temp
                    )
                    # update cash
                    cash += trade_val - trade_cost
                    # Track total sell value (excluding transaction cost)
                    total_sell_value_without_cost += trade_val
                    total_sell_value_with_cost += trade_val - trade_cost

        # Log cash after sell orders
        logger.info(f"Sell orders total value (without cost): {total_sell_value_without_cost:,.2f} 元")
        logger.info(f"Sell orders total value (with cost): {total_sell_value_with_cost:,.2f} 元")
        logger.info(f"Cash after sell orders (available for buying): {cash:,.2f} 元")

        # Allocate capital to buy stocks - NEW LOGIC with reallocation
        if self.max_reallocation_rounds == 0:
            # Behavior EXACTLY same as original strategy (lines 266-294)
            if len(buy) > 0:
                value = cash * self.risk_degree / len(buy)
                for code in buy:
                    # check is stock suspended
                    if not self.trade_exchange.is_stock_tradable(
                        stock_id=code,
                        start_time=trade_start_time,
                        end_time=trade_end_time,
                        direction=(
                            None if self.forbid_all_trade_at_limit else OrderDir.BUY
                        ),
                    ):
                        continue
                    # buy order
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
            # NEW: Apply reallocation logic
            # Get prices for buy stocks
            prices = {}
            for stock_id in buy:
                try:
                    price = self.trade_exchange.get_deal_price(
                        stock_id=stock_id,
                        start_time=trade_start_time,
                        end_time=trade_end_time,
                        direction=OrderDir.BUY,
                    )
                    # Ensure price is not None
                    if price is None:
                        prices[stock_id] = 0.0
                    else:
                        prices[stock_id] = price
                except:
                    prices[stock_id] = 0.0

            # Allocate with reallocation
            buy_amounts = self._allocate_to_buy_stocks(
                buy_list=buy,
                prices=prices,
                cash=cash,
                trade_start_time=trade_start_time,
                trade_end_time=trade_end_time,
            )

            # Generate buy orders based on allocated amounts
            for stock_id, target_amount in buy_amounts.items():
                # check is stock suspended
                if not self.trade_exchange.is_stock_tradable(
                    stock_id=stock_id,
                    start_time=trade_start_time,
                    end_time=trade_end_time,
                    direction=None if self.forbid_all_trade_at_limit else OrderDir.BUY,
                ):
                    continue
                # buy order
                buy_order = Order(
                    stock_id=stock_id,
                    amount=target_amount,
                    start_time=trade_start_time,
                    end_time=trade_end_time,
                    direction=OrderDir.BUY,
                )
                buy_order_list.append(buy_order)
        # Print detailed position information
        if self.verbose:
            logger.info("&"*80)
            logger.info(f"Trading Day {trade_start_time} - {trade_end_time}")
            self._print_position_info(trade_start_time, trade_end_time)
            logger.info("&"*80)

        logger.info("@" * 80)
        logger.info(f"Total buy orders: {len(buy_order_list)}")
        logger.info(f"buyer list is {buy_order_list}")
        logger.info(f"Total sell orders: {len(sell_order_list)}")
        
        # Print seller list with sell prices
        if self.verbose and sell_order_list:
            logger.info("Seller list details:")
            for order in sell_order_list:
                sell_price = self.trade_exchange.get_deal_price(
                    stock_id=order.stock_id,
                    start_time=trade_start_time,
                    end_time=trade_end_time,
                    direction=OrderDir.SELL,
                )
                if sell_price is None or sell_price <= 0:
                    sell_price = 0.0
                sell_value = order.amount * sell_price
                logger.info(
                    f"  {order.stock_id}: "
                    f"amount={order.amount:.0f}, "
                    f"price={sell_price:.2f}, "
                    f"value={sell_value:,.2f} 元"
                )
        else:
            logger.info(f"seller list is {sell_order_list}")

        # Calculate total buy value and transaction costs for new available cash calculation
        total_buy_value = 0.0
        total_buy_cost = 0.0
        for buy_order in buy_order_list:
            buy_price = self.trade_exchange.get_deal_price(
                stock_id=buy_order.stock_id,
                start_time=trade_start_time,
                end_time=trade_end_time,
                direction=OrderDir.BUY,
            )
            if buy_price is not None and buy_price > 0:
                trade_val = buy_order.amount * buy_price
                total_buy_value += trade_val
                # Calculate transaction cost using the same formula as exchange
                # cost_ratio = open_cost + impact_cost (simplified, ignoring volume impact)
                cost_ratio = self.trade_exchange.open_cost
                trade_cost = max(trade_val * cost_ratio, self.trade_exchange.min_cost)
                total_buy_cost += trade_cost

        # Calculate and log new available cash after trades (including transaction costs)
        new_available_cash = cash - total_buy_value - total_buy_cost
        logger.info("=" * 80)
        logger.info(f"Trade Summary:")
        logger.info(f"  Current Cash before buying trade: {cash:,.2f} 元")
        logger.info(f"  Total Buy Value: {total_buy_value:,.2f} 元")
        logger.info(f"  Total Buy Transaction Cost: {total_buy_cost:,.2f} 元")
        logger.info(f"  New Available Cash: {new_available_cash:,.2f} 元")
        logger.info("=" * 80)
        logger.info("@" * 80)
        return TradeDecisionWO(sell_order_list + buy_order_list, self)
