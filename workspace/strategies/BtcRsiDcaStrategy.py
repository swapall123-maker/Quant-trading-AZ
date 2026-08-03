"""Backtest-only daily BTC RSI accumulation and reduction strategy."""

from datetime import datetime

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, Trade

from rsi_dca_sizing import account_equity, action_for_rsi, buy_stake, sell_stake


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
        ] = (1, "rsi_dca_buy")
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
        rsi = latest_candle["rsi"]
        if rsi is None:
            return None

        candle_marker = latest_candle["date"].isoformat()
        if trade.get_custom_data("last_rsi_adjustment") == candle_marker:
            return None

        free_usdt = self.wallets.get_free(self.config["stake_currency"])
        position_value = trade.amount * current_rate
        equity = account_equity(free_usdt, trade.amount, current_rate)
        action = action_for_rsi(float(rsi))

        if action == "buy":
            stake = buy_stake(equity, max_stake, min_stake)
            if stake is not None:
                trade.set_custom_data("last_rsi_adjustment", candle_marker)
                return stake, "rsi_dca_buy"

        if action == "sell":
            stake = sell_stake(equity, position_value, trade.stake_amount, min_stake)
            if stake is not None:
                trade.set_custom_data("last_rsi_adjustment", candle_marker)
                return stake, "rsi_dca_sell"

        return None
