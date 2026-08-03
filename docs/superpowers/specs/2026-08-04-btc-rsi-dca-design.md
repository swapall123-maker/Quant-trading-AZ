# BTC RSI DCA Strategy — Design

## Goal

Create a Freqtrade backtest-only BTC/USDT spot strategy that accumulates BTC while daily RSI is below 30 and scales out while daily RSI is above 70.

## Fixed rules

- Market: Binance spot BTC/USDT only; no short, margin, leverage or API credentials.
- Timeframe: 1 day.
- Backtest timerange: 2020-01-01 through 2026-08-04.
- Starting wallet: 100,000 USDT.
- RSI uses the standard 14-candle period.
- Signal is evaluated from a completed daily candle and executed by Freqtrade on the next candle, avoiding look-ahead bias.
- Daily buy: when RSI is strictly below 30, add up to 0.5% of total account equity, capped by free USDT.
- Daily sell: when RSI is strictly above 70, reduce up to 0.5% of total account equity, capped by the BTC position. Sell all remaining BTC if its value is below that amount.
- Buy accumulation stops at RSI greater than or equal to 30. Selling stops at RSI less than or equal to 70.
- No automatic ROI exit, stop-loss, trailing stop, short entry or full exit signal is enabled.
- Binance spot fee assumptions are retained in the backtest.

## Strategy structure

`workspace/strategies/BtcRsiDcaStrategy.py` owns the indicator and position-adjustment rules. It uses the standard Freqtrade `adjust_trade_position` callback so repeated daily actions modify one BTC position instead of creating unrelated orders.

The tracked configuration file `workspace/config.rsi-dca.json` owns the 100,000 USDT wallet, the single BTC/USDT pair, 1d timeframe, spot mode and position-adjustment limits. Historical candles and result artefacts stay in ignored `data/` and `workspace/backtest_results/` directories.

## Data and execution flow

1. Download BTC/USDT daily spot OHLCV for the fixed timerange.
2. Calculate RSI(14) from each completed candle.
3. Open an initial 0.5%-equity long position only while RSI is below 30.
4. On each subsequent daily candle, add or reduce the current position according to the RSI threshold and account-equity cap.
5. Report final balance, BTC exposure, total adjustments, fees, drawdown and comparison baseline data.

## Error handling and verification

- If the requested 2026 end date contains unavailable candles, use the latest timestamp returned by Binance and record the actual final date in the report.
- If position size is below the exchange minimum, do not force an invalid order; record the remaining dust value.
- Verify no host port is published before and after the backtest.
- Test both thresholds with deterministic synthetic RSI unit tests, then run an integration backtest with downloaded Binance data.
- The report must state that results are historical simulation only, not a trading recommendation.
