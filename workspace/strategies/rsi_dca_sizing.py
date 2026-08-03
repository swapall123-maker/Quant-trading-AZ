"""Pure sizing rules for the BTC daily RSI DCA strategy."""

EQUITY_FRACTION = 0.005


def account_equity(free_usdt: float, btc_amount: float, btc_price: float) -> float:
    """Return current cash plus the marked-to-market BTC position value."""
    return free_usdt + (btc_amount * btc_price)


def action_for_rsi(rsi: float) -> str | None:
    """Return the single allowed daily action for a completed RSI value."""
    if rsi < 30:
        return "buy"
    if rsi > 70:
        return "sell"
    return None


def continuation_action(
    rsi: float,
    previous_rsi: float,
    price: float,
    last_oversold_buy_price: float | None,
    last_overbought_sell_price: float | None,
) -> str | None:
    """Select one reference-price continuation action outside RSI extremes."""
    if not 30 < rsi < 70:
        return None

    buy_continuation = last_oversold_buy_price is not None and (
        price < last_oversold_buy_price
        or (price == last_oversold_buy_price and previous_rsi <= 30)
    )
    sell_continuation = last_overbought_sell_price is not None and (
        price > last_overbought_sell_price
        or (price == last_overbought_sell_price and previous_rsi >= 70)
    )

    if buy_continuation == sell_continuation:
        return None
    return "buy_continuation" if buy_continuation else "sell_continuation"


def buy_stake(equity: float, max_stake: float, min_stake: float | None) -> float | None:
    """Return a cash-capped buy target, or None when it would be exchange dust."""
    stake = min(equity * EQUITY_FRACTION, max_stake)
    if min_stake is not None and stake < min_stake:
        return None
    return stake


def sell_stake(
    equity: float,
    position_value: float,
    trade_stake: float,
    min_stake: float | None,
) -> float | None:
    """Return Freqtrade's negative stake adjustment for the desired BTC sale."""
    target_value = min(equity * EQUITY_FRACTION, position_value)
    if min_stake is not None and target_value < min_stake:
        return None
    if target_value == position_value:
        return -trade_stake
    return -(target_value * trade_stake / position_value)
