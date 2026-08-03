# Freqtrade Backtesting Runbook

## Safety boundary

- This workspace is for backtesting only. Do not run `freqtrade trade`.
- The Docker Compose service publishes no host port.
- Do not add exchange API keys or secrets to `config.backtest.json`.
- Raw market data and reports remain in ignored local directories.

## Verified environment

- Docker Compose project: `quant-freqtrade`
- Container image: `freqtradeorg/freqtrade:stable`
- Freqtrade version: `2026.7`
- Upstream reference: Freqtrade stable commit `52bc96f4480b1a0da6a9b455bd00b17fbb6786a5`
- Exchange/data: Binance spot public OHLCV
- Pairs: `BTC/USDT`, `ETH/USDT`
- Timeframe: `1h`
- Timerange: `20250101-20251231`

## Commands

Run from the project root.

Download data:

```bash
docker compose -p quant-freqtrade -f workspace/docker-compose.yml run --rm freqtrade download-data --config /freqtrade/user_data/config.backtest.json --exchange binance --pairs BTC/USDT ETH/USDT --timeframes 1h --timerange 20250101-20251231
```

Run the smoke-test backtest:

```bash
docker compose -p quant-freqtrade -f workspace/docker-compose.yml run --rm freqtrade backtesting --config /freqtrade/user_data/config.backtest.json --strategy SampleStrategy --timerange 20250101-20251231 -i 1h
```

## First smoke-test result

The SampleStrategy run completed technically. It reported 93 trades, a final balance of 1067.124 USDT from a 1000 USDT dry-run wallet, and 16.55% maximum drawdown. This is a framework verification result only; it is not a trading recommendation or evidence of future profitability.
