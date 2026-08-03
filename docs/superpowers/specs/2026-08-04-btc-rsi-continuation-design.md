# BTC RSI Continuation DCA — Design

## Goal

Replace the current pure RSI DCA rules with a BTC/USDT spot, daily backtest strategy that can continue buying after RSI leaves oversold territory and continue selling after RSI leaves overbought territory, using the most recent qualifying RSI order as the reference price.

## Fixed environment

- Binance spot `BTC/USDT` only; 1d candles; starting balance `100,000 USDT`.
- RSI period 14 is calculated from closed candles. Signals act at Freqtrade's next candle, preventing look-ahead bias.
- Backtest timerange is `20200101-20260804`; report the actual final Binance candle when it is unavailable.
- Use Binance's configured spot fee. Never enable shorting, margin, leverage, credentials or live trading.
- Each submitted buy or sell targets at most `0.5%` (`0.005`) of current marked-to-market account equity and must respect available USDT, held BTC and exchange minimums.
- No ROI, trailing or strategy exit signal. Freqtrade's mandatory technical stoploss remains a near-total-loss safeguard only, not a normal strategy rule.

## Buy rules

1. On each closed daily candle where RSI is strictly below 30, buy 0.5% of current equity and record that filled order's execution price as `last_oversold_buy_price`.
2. When RSI is strictly above 30, continue buying 0.5% each day while the price is at or below `last_oversold_buy_price`.
3. The continuation-buy phase ends when price recovers to or above that saved reference price. Its reference is not replaced by continuation purchases; only a later RSI-below-30 purchase creates a new reference.
4. RSI exactly 30 does not activate a normal RSI buy or a continuation-buy phase.

## Sell rules

1. On each closed daily candle where RSI is strictly above 70, sell 0.5% of current equity and record that filled order's execution price as `last_overbought_sell_price`.
2. When RSI is strictly below 70, continue selling 0.5% each day while the price is at or above `last_overbought_sell_price`.
3. The continuation-sell phase ends when price falls to or below that saved reference price. Its reference is not replaced by continuation sales; only a later RSI-above-70 sale creates a new reference.
4. RSI exactly 70 does not activate a normal RSI sale or a continuation-sell phase.

## Boundary and execution decisions

- To make the user's inclusive trigger and stop wording deterministic, equality is an eligible continuation order only on the first daily evaluation after the RSI regime changes. Thereafter equality is the recovery point and stops further continuation orders. Price beyond the reference keeps the phase stopped.
- A normal RSI-below-30 buy always has priority over buy-continuation logic and refreshes the saved buy reference. A normal RSI-above-70 sell always has priority over sell-continuation logic and refreshes the saved sell reference.
- One position adjustment maximum is allowed for a candle. If an impossible simultaneous buy/sell condition occurs, no adjustment is made; regular RSI zones cannot overlap.
- A sell target larger than the remaining BTC position closes the position. A target below exchange minimum is skipped and recorded as dust in the report.

## Strategy state and report

`BtcRsiDcaStrategy` persists the two reference prices and phase state using Freqtrade trade custom data, which also prevents duplicate actions in a daily candle. The export records every order with tags: `rsi_oversold_buy`, `buy_continuation`, `rsi_overbought_sell`, or `sell_continuation`.

The runbook records actual downloaded range, final balance, return, drawdown, fees, order counts by tag and an execution table containing date, side, tag, RSI, price, value and reference price. Results remain historical simulation, not a trading recommendation.
