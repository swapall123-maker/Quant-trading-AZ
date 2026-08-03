# BTC RSI Continuation DCA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the daily BTC/USDT RSI DCA backtest with price-reference continuation buys and sells, plus an exportable history of every simulated order.

**Architecture:** Keep every threshold and reference-price decision in `rsi_dca_sizing.py`, so deterministic unit tests cover it without Freqtrade. The strategy assigns distinct order tags and captures actual filled prices in Freqtrade trade custom data. A small standard-library reporting script converts Freqtrade's exported order history into a readable CSV.

**Tech Stack:** Python 3.14, Freqtrade 2026.7 Docker image, TA-Lib, Python `unittest`, Binance public OHLCV.

## Global Constraints

- Work directly on the user-approved `develop` branch; do not create a worktree or modify `main`.
- Binance spot BTC/USDT, 1d, RSI(14), 100000 USDT and requested timerange `20200101-20260804` only.
- Signals use completed candles and Freqtrade simulates orders on the next candle; each action is at most 0.005 of marked-to-market equity.
- Buy continuation: only 30 < RSI < 70, current price below the latest filled RSI<30 buy price, or equal on the first candle crossing above 30.
- Sell continuation: only 30 < RSI < 70, current price above the latest filled RSI>70 sell price, or equal on the first candle crossing below 70.
- Normal RSI<30 buy and RSI>70 sell take priority and refresh their matching reference. A possible conflicting continuation pair emits no order.
- Preserve spot-only, no credentials, no short/margin/leverage/ROI/trailing/normal stop-loss behavior, no Docker host ports, and Binance fee configuration.

## File Structure

- `workspace/strategies/rsi_dca_sizing.py`: add deterministic continuation-action selection.
- `workspace/tests/test_rsi_dca_sizing.py`: test all crossings, equality and conflict boundaries.
- `workspace/strategies/BtcRsiDcaStrategy.py`: tag normal/continuation orders and persist filled reference prices.
- `workspace/scripts/export_trade_history.py`: turn exported Freqtrade orders into a CSV row per buy/sell.
- `workspace/tests/test_export_trade_history.py`: test CSV row extraction with a small in-memory trade fixture.
- `docs/runbooks/btc-rsi-dca-backtest.md`: update commands, tags, result record and report path.

### Task 1: Test and add continuation-rule selection

**Files:**
- Modify: `workspace/strategies/rsi_dca_sizing.py`
- Modify: `workspace/tests/test_rsi_dca_sizing.py`

**Interfaces:**
- Produces `continuation_action(rsi: float, previous_rsi: float, price: float, last_oversold_buy_price: float | None, last_overbought_sell_price: float | None) -> str | None`.
- Returns only `"buy_continuation"`, `"sell_continuation"` or `None`.

- [ ] **Step 1: Write failing continuation tests**

```python
def test_buy_continuation_below_reference_after_rsi_leaves_oversold(self):
    self.assertEqual(continuation_action(45, 29, 99, 100, None), "buy_continuation")

def test_equal_price_is_allowed_only_on_the_crossing_candle(self):
    self.assertEqual(continuation_action(45, 30, 100, 100, None), "buy_continuation")
    self.assertIsNone(continuation_action(45, 40, 100, 100, None))

def test_sell_continuation_above_reference_after_rsi_leaves_overbought(self):
    self.assertEqual(continuation_action(55, 71, 101, None, 100), "sell_continuation")

def test_continuations_do_not_run_in_normal_or_boundary_rsi_zones(self):
    self.assertIsNone(continuation_action(30, 29, 99, 100, None))
    self.assertIsNone(continuation_action(70, 71, 101, None, 100))

def test_conflicting_continuations_skip_the_candle(self):
    self.assertIsNone(continuation_action(50, 40, 100, 101, 99))
```

- [ ] **Step 2: Verify RED**

Run: `cd workspace && PYTHONPATH=strategies python3 -m unittest tests/test_rsi_dca_sizing.py -v`

Expected: import failure for `continuation_action`.

- [ ] **Step 3: Add the minimal pure selector**

```python
def continuation_action(rsi, previous_rsi, price, last_oversold_buy_price,
                        last_overbought_sell_price):
    if not 30 < rsi < 70:
        return None
    buy = last_oversold_buy_price is not None and (
        price < last_oversold_buy_price
        or (price == last_oversold_buy_price and previous_rsi <= 30)
    )
    sell = last_overbought_sell_price is not None and (
        price > last_overbought_sell_price
        or (price == last_overbought_sell_price and previous_rsi >= 70)
    )
    if buy == sell:
        return None
    return "buy_continuation" if buy else "sell_continuation"
```

- [ ] **Step 4: Verify GREEN and commit**

Run: `cd workspace && PYTHONPATH=strategies python3 -m unittest tests/test_rsi_dca_sizing.py -v`

Expected: all sizing and continuation tests pass.

Run: `git add workspace/strategies/rsi_dca_sizing.py workspace/tests/test_rsi_dca_sizing.py && git commit -m "feat: add RSI continuation rules"`

### Task 2: Wire Freqtrade orders and filled-price state

**Files:**
- Modify: `workspace/strategies/BtcRsiDcaStrategy.py`

**Interfaces:**
- Consumes `action_for_rsi`, `continuation_action`, `buy_stake`, and `sell_stake`.
- Persists `last_oversold_buy_price`, `last_overbought_sell_price`, and `last_rsi_adjustment` via `Trade.set_custom_data`.
- Emits tags `rsi_oversold_buy`, `buy_continuation`, `rsi_overbought_sell`, and `sell_continuation`.

- [ ] **Step 1: Add failing strategy-discovery expectation**

Run: `docker compose --project-name quant-freqtrade -f workspace/docker-compose.yml run --rm freqtrade list-strategies --strategy-path /freqtrade/user_data/strategies`

Expected: current strategy loads but has no continuation tags; this establishes the pre-change Docker import baseline.

- [ ] **Step 2: Implement strategy state and order tags**

In `populate_entry_trend`, rename the normal tag to `rsi_oversold_buy`. In `adjust_trade_position`, get the latest and previous RSI candles, select normal action first, otherwise call `continuation_action`. Use `buy_stake` for `rsi_oversold_buy`/`buy_continuation`, and `sell_stake` for `rsi_overbought_sell`/`sell_continuation`. Do not set reference prices at signal time.

Add:

```python
def order_filled(self, pair, trade, order, current_time, **kwargs):
    price = float(order.average or order.price)
    if order.ft_order_tag == "rsi_oversold_buy" and order.ft_order_side == trade.entry_side:
        trade.set_custom_data("last_oversold_buy_price", price)
    elif order.ft_order_tag == "rsi_overbought_sell" and order.ft_order_side == trade.exit_side:
        trade.set_custom_data("last_overbought_sell_price", price)
```

Use the existing daily marker to prevent duplicate callback orders. If data is missing, RSI is NaN, reference price is absent, action stakes are dust, or both continuation directions match, return `None`.

- [ ] **Step 3: Verify strategy discovery and unit regressions**

Run: `docker compose --project-name quant-freqtrade -f workspace/docker-compose.yml run --rm freqtrade list-strategies --strategy-path /freqtrade/user_data/strategies && cd workspace && PYTHONPATH=strategies python3 -m unittest tests/test_rsi_dca_sizing.py -v`

Expected: strategy imports and all tests pass.

- [ ] **Step 4: Commit**

Run: `git add workspace/strategies/BtcRsiDcaStrategy.py && git commit -m "feat: continue RSI positions by reference price"`

### Task 3: Test and add order-history CSV exporter

**Files:**
- Create: `workspace/scripts/export_trade_history.py`
- Create: `workspace/tests/test_export_trade_history.py`

**Interfaces:**
- Produces `order_rows(trades: list[dict]) -> list[dict[str, object]]`.
- Produces CLI: `python3 workspace/scripts/export_trade_history.py <backtest-results-dir> <output-csv>`.
- CSV columns: `date`, `pair`, `side`, `tag`, `price`, `amount`, `cost`.

- [ ] **Step 1: Write failing extraction test**

```python
def test_order_rows_keeps_only_filled_buy_and_sell_orders(self):
    trades = [{"pair": "BTC/USDT", "orders": [
        {"order_date": "2020-01-01T00:00:00Z", "ft_order_side": "buy", "ft_order_tag": "rsi_oversold_buy", "average": 7000, "filled": 0.1, "cost": 700},
        {"order_date": "2020-01-02T00:00:00Z", "ft_order_side": "sell", "ft_order_tag": "rsi_overbought_sell", "average": 7100, "filled": 0.1, "cost": 710},
    ]}]
    self.assertEqual([row["tag"] for row in order_rows(trades)], ["rsi_oversold_buy", "rsi_overbought_sell"])
```

- [ ] **Step 2: Verify RED**

Run: `cd workspace && PYTHONPATH=scripts python3 -m unittest tests/test_export_trade_history.py -v`

Expected: import failure for `export_trade_history`.

- [ ] **Step 3: Implement stdlib-only CSV export**

Read the JSON member of the newest Freqtrade zip in the supplied results directory with `zipfile.ZipFile`, use `csv.DictWriter`, and keep only orders with `filled > 0` and side `buy` or `sell`. Map the Freqtrade fields used by the test. Tags preserve whether an order was normal RSI or a continuation order.

- [ ] **Step 4: Verify GREEN and commit**

Run: `cd workspace && PYTHONPATH=scripts python3 -m unittest tests/test_export_trade_history.py -v`

Expected: exporter test passes.

Run: `git add workspace/scripts/export_trade_history.py workspace/tests/test_export_trade_history.py && git commit -m "feat: export BTC RSI trade history"`

### Task 4: Run integration backtest and update evidence

**Files:**
- Modify: `docs/runbooks/btc-rsi-dca-backtest.md`

- [ ] **Step 1: Confirm no Freqtrade host port, then refresh daily BTC data**

Run: `docker ps --format '{{.Names}} {{.Ports}}'`

Run: `docker compose --project-name quant-freqtrade -f workspace/docker-compose.yml run --rm freqtrade download-data --config /freqtrade/user_data/config.rsi-dca.json --pairs BTC/USDT --timeframes 1d --timerange 20200101-20260804`

Expected: no Freqtrade port; only ignored local data changes.

- [ ] **Step 2: Run the continuation backtest and export history**

Run: `docker compose --project-name quant-freqtrade -f workspace/docker-compose.yml run --rm freqtrade backtesting --config /freqtrade/user_data/config.rsi-dca.json --strategy BtcRsiDcaStrategy --strategy-path /freqtrade/user_data/strategies --timerange 20200101-20260804 --export trades --backtest-directory /freqtrade/user_data/backtest_results`

Run: `python3 workspace/scripts/export_trade_history.py workspace/backtest_results workspace/backtest_results/btc-rsi-continuation-history.csv`

Expected: Freqtrade completes in spot dry-run mode and a local ignored CSV lists every filled order.

- [ ] **Step 3: Update runbook and verify final state**

Record actual data range, Freqtrade version, final balance, return, drawdown, order counts by four tags, CSV path and post-run port check. State results are historical only.

Run: `cd workspace && PYTHONPATH=strategies:scripts python3 -m unittest discover -s tests -v && docker ps --format '{{.Names}} {{.Ports}}' && git diff --check`

Expected: all tests pass, no Freqtrade container or host port remains, and diff check is clean.

- [ ] **Step 4: Commit the run evidence**

Run: `git add docs/runbooks/btc-rsi-dca-backtest.md && git commit -m "docs: record RSI continuation backtest"`
