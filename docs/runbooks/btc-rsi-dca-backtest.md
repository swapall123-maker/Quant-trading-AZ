# BTC RSI DCA backtest

This runbook executes only a historical Binance spot simulation. It contains no API credentials, has no live-trading mode, and never publishes a host port.

## Fixed scenario

- Pair and market: Binance spot `BTC/USDT` only.
- Candles: `1d`; requested range `20200101-20260804`.
- Starting wallet: `100,000 USDT`; Binance's configured spot fee is applied by Freqtrade.
- Indicator: RSI(14) from completed candles.
- Rules: RSI strictly below 30 buys 0.5% of marked-to-market account equity each day; RSI strictly above 70 sells 0.5% each day. RSI 30 through 70 does nothing. A BTC position smaller than the next sell target is fully reduced, subject to exchange minimums.
- Timing: Freqtrade evaluates the completed candle and simulates a market order on the following candle. This avoids look-ahead bias.
- Exit controls: no signal exit, ROI or trailing exit. Freqtrade requires a technical emergency stoploss field; the strategy sets it to `-99.9%`, so it is not part of the normal RSI rule.

## Check Docker ports

```bash
docker ps --format '{{.Names}} {{.Ports}}'
```

No container called `quant-freqtrade-*` should remain before or after the commands. The Compose file deliberately has no `ports:` entry and each command uses `run --rm`.

## Download daily candles

```bash
docker compose --project-name quant-freqtrade -f workspace/docker-compose.yml run --rm freqtrade \
  download-data --config /freqtrade/user_data/config.rsi-dca.json \
  --pairs BTC/USDT --timeframes 1d --timerange 20200101-20260804
```

If Binance has no candle for the requested final day, Freqtrade keeps the latest available candle. Verify the actual downloaded range:

```bash
docker compose --project-name quant-freqtrade -f workspace/docker-compose.yml run --rm freqtrade \
  list-data --config /freqtrade/user_data/config.rsi-dca.json --show-timerange
```

## Run the backtest

```bash
docker compose --project-name quant-freqtrade -f workspace/docker-compose.yml run --rm freqtrade \
  backtesting --config /freqtrade/user_data/config.rsi-dca.json \
  --strategy BtcRsiDcaStrategy --strategy-path /freqtrade/user_data/strategies \
  --timerange 20200101-20260804 --export trades \
  --backtest-directory /freqtrade/user_data/backtest_results
```

`rsi_dca_buy` and `rsi_dca_sell` are the position-adjustment tags in the exported trades. Data and JSON results stay under ignored local directories.

## Run record

Run date: 2026-08-03 (container clock), Freqtrade 2026.7.

- Downloaded data: 2020-01-01 00:00:00 through 2026-08-02 00:00:00 UTC (2,406 daily candles). The requested 2026-08-04 endpoint was unavailable.
- Backtest range after the 15-candle RSI warm-up: 2020-01-16 00:00:00 through 2026-08-02 00:00:00 UTC.
- Starting / final balance: 100,000 / 105,025.731 USDT; absolute result +5,025.731 USDT (+5.03%).
- Wallet-based maximum drawdown: 5,989.299 USDT (5.71%). Freqtrade's closed-trade drawdown was 1,420.701 USDT (1.33%).
- Freqtrade reports 7 trade lifecycles: 6 RSI sell closures and 1 final forced valuation exit. The exported orders contain 92 `rsi_dca_buy` orders and 85 `rsi_dca_sell` orders, confirming repeated daily position adjustments.
- Docker port checks before and after the run listed only the pre-existing PostgreSQL mappings `5432` and `5433`; no `quant-freqtrade-*` container remained and no Freqtrade host port was published.

Historical performance is a simulation, not a trading recommendation or a guarantee of future results.
