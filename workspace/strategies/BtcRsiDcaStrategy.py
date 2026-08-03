"""Backtest-only daily BTC RSI accumulation and reduction strategy."""

from datetime import datetime
from math import isfinite

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, Order, Trade

from rsi_dca_sizing import (
    account_equity,
    action_for_rsi,
    buy_stake,
    continuation_action,
    sell_stake,
)


class BtcRsiDcaStrategy(IStrategy):
    """Buy or reduce one BTC spot position once per daily RSI signal candle."""

    INTERFACE_VERSION = 3
    can_short = False
    timeframe = "1d"
    startup_candle_count = 15

    position_adjustment_enable = True
    max_entry_position_adjustment = -1

    # Freqtrade requires a stoploss value. This is only a near-total-loss safeguard;
    # the strategy has no normal stoploss, ROI, trailing, or exit-signal behaviour.
    minimal_roi = {"0": 10_000}
    stoploss = -0.999
    use_exit_signal = False
    trailing_stop = False

    order_types = {
        "entry": "market",
        "exit": "market",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["rsi"] < 30) & (dataframe["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "rsi_oversold_buy")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        return dataframe

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: float | None,
        max_stake: float,
        leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        """Use 0.5% of available initial equity instead of all unlimited stake."""
        initial_equity = account_equity(max_stake, 0.0, current_rate)
        return buy_stake(initial_equity, max_stake, min_stake) or 0.0

    def adjust_trade_position(
        self,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        min_stake: float | None,
        max_stake: float,
        current_entry_rate: float,
        current_exit_rate: float,
        current_entry_profit: float,
        current_exit_profit: float,
        **kwargs,
    ) -> float | None | tuple[float | None, str | None]:
        """Make at most one daily position adjustment using the latest completed RSI."""
        if trade.has_open_orders:
            return None

        dataframe, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
        if dataframe.empty:
            return None

        latest_candle = dataframe.iloc[-1]
        previous_candle = dataframe.iloc[-2] if len(dataframe.index) > 1 else None
        rsi = latest_candle["rsi"]
        if rsi is None or not isfinite(float(rsi)):
            return None

        candle_marker = latest_candle["date"].isoformat()
        if trade.get_custom_data("last_rsi_adjustment") == candle_marker:
            return None

        free_usdt = self.wallets.get_free(self.config["stake_currency"])
        position_value = trade.amount * current_rate
        equity = account_equity(free_usdt, trade.amount, current_rate)
        action = action_for_rsi(float(rsi))

        if action is None and previous_candle is not None:
            previous_rsi = previous_candle["rsi"]
            if previous_rsi is not None and isfinite(float(previous_rsi)):
                action = continuation_action(
                    float(rsi),
                    float(previous_rsi),
                    current_rate,
                    trade.get_custom_data("last_oversold_buy_price"),
                    trade.get_custom_data("last_overbought_sell_price"),
                )

        if action in {"buy", "buy_continuation"}:
            stake = buy_stake(equity, max_stake, min_stake)
            if stake is not None:
                trade.set_custom_data("last_rsi_adjustment", candle_marker)
                tag = "rsi_oversold_buy" if action == "buy" else "buy_continuation"
                return stake, tag

        if action in {"sell", "sell_continuation"}:
            stake = sell_stake(equity, position_value, trade.stake_amount, min_stake)
            if stake is not None:
                trade.set_custom_data("last_rsi_adjustment", candle_marker)
                tag = "rsi_overbought_sell" if action == "sell" else "sell_continuation"
                return stake, tag

        return None

    def order_filled(
        self,
        pair: str,
        trade: Trade,
        order: Order,
        current_time: datetime,
        **kwargs,
    ) -> None:
        """Capture only filled normal-RSI prices as continuation references."""
        price = float(order.average or order.price)
        if order.ft_order_tag == "rsi_oversold_buy" and order.ft_order_side == trade.entry_side:
            trade.set_custom_data("last_oversold_buy_price", price)
        elif order.ft_order_tag == "rsi_overbought_sell" and order.ft_order_side == trade.exit_side:
            trade.set_custom_data("last_overbought_sell_price", price)
