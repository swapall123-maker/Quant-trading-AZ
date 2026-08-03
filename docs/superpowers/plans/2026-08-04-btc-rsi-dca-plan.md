# BTC RSI DCA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a backtest-only Freqtrade strategy for Binance spot BTC/USDT on 1d candles. RSI(14) below 30 buys, and RSI(14) above 70 sells; each action targets 0.5% of marked-to-market account equity.

**Architecture:** Sizing arithmetic stays in a dependency-free module with deterministic tests. `BtcRsiDcaStrategy` calculates RSI and uses Freqtrade callbacks to convert the tested targets into an initial order or an adjustment of one open BTC position. A separate fixed config and runbook make the 100,000-USDT historical run reproducible.

**Tech Stack:** Python 3, Freqtrade 2026.7 Docker image, TA-Lib, Python `unittest`, Binance public OHLCV.

## Global Constraints

- Binance spot BTC/USDT only; no credentials, margin, leverage, shorting, live trading or host ports.
- Use RSI period 14, `1d`, `20200101-20260804`, `100000` USDT and `0.005` of current equity per action.
- Completed-candle signal, next-candle Freqtrade execution; strict `< 30` buy and `> 70` sell only.
- No ROI, stop-loss, trailing-stop or conventional exit signal. Respect exchange minimums and cash/position caps.
- Persist historical data and results only in ignored directories; record actual downloaded end date and historical-only disclaimer.

## File Structure

- `workspace/strategies/rsi_dca_sizing.py`: Pure marked-to-market equity and Freqtrade stake conversion.
- `workspace/tests/test_rsi_dca_sizing.py`: Deterministic sizing regression tests.
- `workspace/strategies/BtcRsiDcaStrategy.py`: RSI/entry/position-adjustment strategy.
- `workspace/config.rsi-dca.json`: Single-pair 100,000-USDT spot backtest config.
- `docs/runbooks/btc-rsi-dca-backtest.md`: Exact no-port download/backtest commands and recorded output.

### Task 1: Add tested sizing rules

**Files:**
- Create: `workspace/tests/test_rsi_dca_sizing.py`
- Create: `workspace/strategies/rsi_dca_sizing.py`

**Interfaces:**
- `account_equity(free_usdt: float, btc_amount: float, btc_price: float) -> float`
- `action_for_rsi(rsi: float) -> str | None`
- `buy_stake(equity: float, max_stake: float, min_stake: float | None) -> float | None`
- `sell_stake(equity: float, position_value: float, trade_stake: float, min_stake: float | None) -> float | None`

- [x] **Step 1: Write the failing tests**

```python
class RsiDcaSizingTest(unittest.TestCase):
    def test_buy_uses_half_percent_of_marked_to_market_equity(self):
        equity = account_equity(90_000, 0.2, 50_000)
        self.assertEqual(equity, 100_000)
        self.assertEqual(buy_stake(equity, 90_000, 10), 500)

    def test_buy_is_capped_by_free_cash(self):
        self.assertEqual(buy_stake(100_000, 250, 10), 250)

    def test_thresholds_are_strict(self):
        self.assertEqual(action_for_rsi(29.9), "buy")
        self.assertIsNone(action_for_rsi(30.0))
        self.assertIsNone(action_for_rsi(70.0))
        self.assertEqual(action_for_rsi(70.1), "sell")

    def test_sell_converts_current_quote_target_to_trade_stake(self):
        self.assertEqual(sell_stake(100_000, 20_000, 10_000, 10), -250)

    def test_sell_closes_when_position_is_smaller_than_target(self):
        self.assertEqual(sell_stake(100_000, 400, 300, 10), -300)

    def test_rejects_dust_orders(self):
        self.assertIsNone(buy_stake(1_000, 1_000, 10))
        self.assertIsNone(sell_stake(1_000, 100, 80, 10))
```

- [x] **Step 2: Verify RED**

Run: `cd workspace && PYTHONPATH=strategies python3 -m unittest tests/test_rsi_dca_sizing.py -v`

Expected: fail because `rsi_dca_sizing` is absent.

- [x] **Step 3: Implement minimal helper**

```python
EQUITY_FRACTION = 0.005
def account_equity(free_usdt, btc_amount, btc_price): return free_usdt + btc_amount * btc_price
def action_for_rsi(rsi):
    if rsi < 30: return "buy"
    if rsi > 70: return "sell"
    return None
def buy_stake(equity, max_stake, min_stake):
    value = min(equity * EQUITY_FRACTION, max_stake)
    return value if min_stake is None or value >= min_stake else None
def sell_stake(equity, position_value, trade_stake, min_stake):
    value = min(equity * EQUITY_FRACTION, position_value)
    if min_stake is not None and value < min_stake: return None
    return -trade_stake if value == position_value else -(value * trade_stake / position_value)
```

- [x] **Step 4: Verify GREEN**

Run: `cd workspace && PYTHONPATH=strategies python3 -m unittest tests/test_rsi_dca_sizing.py -v`

Expected: six tests pass.

- [x] **Step 5: Commit**

Run: `git add workspace/tests/test_rsi_dca_sizing.py workspace/strategies/rsi_dca_sizing.py && git commit -m "feat: add RSI DCA position sizing"`

### Task 2: Add RSI strategy

**Files:**
- Create: `workspace/strategies/BtcRsiDcaStrategy.py`

**Interfaces:**
- Consumes the Task 1 helpers.
- Exposes `BtcRsiDcaStrategy(IStrategy)` using `custom_stake_amount` and `adjust_trade_position`.

- [x] **Step 1: Implement only from Task 1's passing sizing interface**

Set: `INTERFACE_VERSION = 3`, `can_short = False`, `timeframe = "1d"`, `startup_candle_count = 15`, `position_adjustment_enable = True`, `max_entry_position_adjustment = -1`, `minimal_roi = {"0": 10000}`, `stoploss = -0.99`, `use_exit_signal = False`, `trailing_stop = False`; use market entry/exit/stoploss orders. Add RSI via `ta.RSI(dataframe, timeperiod=14)`. Entry signal is `rsi < 30` and `volume > 0`. The strategy never sets an exit signal.

`custom_stake_amount` creates the initial 0.5%-equity buy from available max stake. `adjust_trade_position` must return `None` for open orders, find the latest analyzed RSI, calculate `free_usdt + trade.amount * current_rate`, then use the already-tested `action_for_rsi` result to call `buy_stake` or `sell_stake`. Return `(amount, "rsi_dca_buy")` or `(amount, "rsi_dca_sell")`; return `None` otherwise.

- [x] **Step 2: Verify Freqtrade discovers it**

Run: `docker compose --project-name quant-freqtrade -f workspace/docker-compose.yml run --rm freqtrade list-strategies --strategy-path /freqtrade/user_data/strategies`

Expected: `BtcRsiDcaStrategy` appears with no import error.

- [x] **Step 3: Verify sizing tests remain green and commit**

Run: `cd workspace && PYTHONPATH=strategies python3 -m unittest tests/test_rsi_dca_sizing.py -v && git add workspace/strategies/BtcRsiDcaStrategy.py && git commit -m "feat: add BTC RSI DCA strategy"`

### Task 3: Configure and document the fixed historical run

**Files:**
- Create: `workspace/config.rsi-dca.json`
- Create: `docs/runbooks/btc-rsi-dca-backtest.md`

- [x] **Step 1: Add safe config**

Use dry-run Binance spot, `stake_currency: USDT`, `stake_amount: unlimited`, `max_open_trades: 1`, `timeframe: 1d`, `dry_run_wallet: 100000`, `tradable_balance_ratio: 1.0`, one static pair `BTC/USDT`, blank key/secret and position adjustment enabled. Set market order types and disabled order-book pricing. Do not add `ports`, a container name, API credentials or live-trading settings.

- [x] **Step 2: Add runbook command path**

```bash
docker compose --project-name quant-freqtrade -f workspace/docker-compose.yml run --rm freqtrade download-data --config /freqtrade/user_data/config.rsi-dca.json --pairs BTC/USDT --timeframes 1d --timerange 20200101-20260804
docker compose --project-name quant-freqtrade -f workspace/docker-compose.yml run --rm freqtrade backtesting --config /freqtrade/user_data/config.rsi-dca.json --strategy BtcRsiDcaStrategy --strategy-path /freqtrade/user_data/strategies --timerange 20200101-20260804 --export trades --export-filename /freqtrade/user_data/backtest_results/btc-rsi-dca.json
```

Document next-candle execution, strict thresholds, fee sensitivity, actual data end date, tags, historical-only warning and `docker ps --format '{{.Names}} {{.Ports}}'` pre/post port check.

- [x] **Step 3: Validate config and commit**

Run: `docker compose --project-name quant-freqtrade -f workspace/docker-compose.yml run --rm freqtrade show-config --config /freqtrade/user_data/config.rsi-dca.json`

Expected: dry-run spot BTC/USDT, `1d`, 100000-USDT wallet and no API key.

Run: `git add workspace/config.rsi-dca.json docs/runbooks/btc-rsi-dca-backtest.md && git commit -m "docs: add BTC RSI DCA backtest runbook"`

### Task 4: Integrate, record and verify

**Files:**
- Modify: `docs/runbooks/btc-rsi-dca-backtest.md`

- [x] **Step 1: Confirm no Freqtrade host port**

Run: `docker ps --format '{{.Names}} {{.Ports}}'`

Expected: no `quant-freqtrade-*` container or published Freqtrade port.

- [x] **Step 2: Download and inspect 1d data**

Run the download command from Task 3, then `docker compose --project-name quant-freqtrade -f workspace/docker-compose.yml run --rm freqtrade list-data --config /freqtrade/user_data/config.rsi-dca.json --show-timerange`.

Expected: BTC/USDT starts no later than 2020-01-01 and prints its actual final date.

- [x] **Step 3: Run backtest and append evidence**

Run the backtesting command from Task 3. Add the Freqtrade version, actual data range, total profit, final balance, drawdown, entries/exits and historical-only note to the runbook.

- [x] **Step 4: Confirm teardown and commit**

Run: `docker ps --format '{{.Names}} {{.Ports}}'`

Expected: no Freqtrade container remains after `run --rm`.

Run: `git add docs/runbooks/btc-rsi-dca-backtest.md && git commit -m "docs: record BTC RSI DCA backtest"`
