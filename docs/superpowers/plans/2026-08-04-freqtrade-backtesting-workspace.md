# Freqtrade Backtesting Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clone Freqtrade and create a safe, repeatable Docker-based crypto backtesting workspace for BTC/USDT and ETH/USDT, without exchange credentials or live trading.

**Architecture:** The parent Git repository stores only documentation and safe metadata. The upstream Freqtrade source is cloned as a separate ignored repository at `vendor/freqtrade`; its generated user data, market data and reports never enter the parent Git history. Docker Compose runs disposable Freqtrade containers with `user_data` mounted locally.

**Tech Stack:** Git; Freqtrade stable branch; Docker Desktop and Docker Compose; Binance public OHLCV data; Freqtrade SampleStrategy.

## Global Constraints

- Work only on the local `develop` branch; do not merge or push to `main` in this implementation cycle.
- Clone `https://github.com/freqtrade/freqtrade.git` at the upstream `stable` branch.
- Do not configure exchange API keys, API secrets, withdrawals, leverage, futures, live trading, or a `freqtrade trade` process.
- Restrict the first backtest to Binance spot historical data for `BTC/USDT` and `ETH/USDT`, 1h timeframe.
- Preserve generated data, database files, logs, reports and any config containing secrets outside tracked files.
- Use Docker Compose; do not install Python packages globally.

---

## File Structure

- Create: `.gitignore` — excludes the upstream clone and all Freqtrade-generated assets.
- Create: `docs/runbooks/freqtrade-backtesting.md` — Vietnamese commands and expected outcomes for the first safe backtest.
- Create: `vendor/freqtrade/` — ignored upstream Freqtrade clone, checked out at `stable`.
- Generated (ignored): `vendor/freqtrade/user_data/` — configuration, strategies, data, logs and reports.

### Task 1: Establish safe repository boundaries

**Files:**
- Create: `.gitignore`
- Create: `docs/runbooks/freqtrade-backtesting.md`
- Test: `git check-ignore -v vendor/freqtrade/user_data/config.json`

**Interfaces:**
- Consumes: Parent repository on branch `develop`.
- Produces: A tracked runbook and ignore rules that protect upstream/generated Freqtrade files.

- [ ] **Step 1: Add the ignore rules**

Create `.gitignore` with exactly:

```gitignore
# Upstream framework and all machine-specific Freqtrade state
/vendor/freqtrade/

# Prevent accidental secrets or backtest artifacts elsewhere in this project
*.sqlite
*.sqlite-journal
*.json
*.log
/backtest-results/
```

- [ ] **Step 2: Verify protection before cloning**

Run: `git check-ignore -v vendor/freqtrade/user_data/config.json`

Expected: output identifies `.gitignore` and `/vendor/freqtrade/` as the matching rule.

- [ ] **Step 3: Write the initial runbook**

Create `docs/runbooks/freqtrade-backtesting.md` with:

```markdown
# Freqtrade Backtesting Runbook

## Safety boundary

- Backtesting only; never run `freqtrade trade`.
- Do not add exchange API keys or secrets.
- Use Binance public spot data, `BTC/USDT` and `ETH/USDT`, timeframe `1h`.
- Treat `SampleStrategy` as a technical smoke test, not an investable strategy.

## Commands

Run all Freqtrade commands from `vendor/freqtrade`.

1. `docker compose pull`
2. `docker compose run --rm freqtrade create-userdir --userdir user_data`
3. `docker compose run --rm freqtrade download-data --exchange binance --pairs BTC/USDT ETH/USDT --timeframes 1h --timerange 20250101-20251231`
4. `docker compose run --rm freqtrade backtesting --config user_data/config.json --strategy SampleStrategy --timerange 20250101-20251231 -i 1h`

If a command fails, save the complete terminal output before changing configuration or strategy code.
```

- [ ] **Step 4: Inspect the staged diff**

Run: `git diff -- .gitignore docs/runbooks/freqtrade-backtesting.md`

Expected: no API key, secret, generated data or upstream code appears.

- [ ] **Step 5: Commit the boundary and runbook**

```bash
git add .gitignore docs/runbooks/freqtrade-backtesting.md
git commit -m "docs: add safe freqtrade backtesting runbook"
```

### Task 2: Clone and validate upstream Freqtrade

**Files:**
- Create: `vendor/freqtrade/` (ignored upstream Git repository)
- Test: `git -C vendor/freqtrade branch --show-current`; `docker compose -f vendor/freqtrade/docker-compose.yml config --quiet`

**Interfaces:**
- Consumes: Ignore rule from Task 1 and official upstream remote URL.
- Produces: An isolated Freqtrade stable checkout runnable by Docker Compose.

- [ ] **Step 1: Confirm Docker prerequisites**

Run:

```bash
docker --version
docker compose version
```

Expected: both commands exit 0. If either is unavailable, stop; install and start Docker Desktop before continuing.

- [ ] **Step 2: Clone the stable upstream branch**

Run:

```bash
mkdir -p vendor
git clone --branch stable --single-branch https://github.com/freqtrade/freqtrade.git vendor/freqtrade
```

Expected: `vendor/freqtrade/.git` exists and the clone has no local modifications.

- [ ] **Step 3: Verify upstream revision and branch**

Run:

```bash
git -C vendor/freqtrade branch --show-current
git -C vendor/freqtrade status --short
git -C vendor/freqtrade log -1 --oneline
```

Expected: branch output is `stable`, status output is empty, and the final command prints one upstream commit.

- [ ] **Step 4: Validate Compose without starting a bot**

Run: `docker compose -f vendor/freqtrade/docker-compose.yml config --quiet`

Expected: exit 0; no container is started and no exchange credential is created.

### Task 3: Initialize the safe backtest assets

**Files:**
- Create: `vendor/freqtrade/user_data/` (ignored generated directory)
- Modify: `docs/runbooks/freqtrade-backtesting.md` only if a verified stable Compose command differs.
- Test: `docker compose run --rm freqtrade create-userdir --userdir user_data`; `docker compose run --rm freqtrade list-strategies --userdir user_data`

**Interfaces:**
- Consumes: Valid Docker Compose definition from Task 2.
- Produces: A local sample-strategy directory without an exchange account or trade process.

- [ ] **Step 1: Pull the official container image**

Run from `vendor/freqtrade`:

```bash
docker compose pull
```

Expected: the `freqtrade` image is downloaded; no bot is running afterward.

- [ ] **Step 2: Create the user-data directory and sample strategy**

Run from `vendor/freqtrade`:

```bash
docker compose run --rm freqtrade create-userdir --userdir user_data
docker compose run --rm freqtrade list-strategies --userdir user_data
```

Expected: `user_data/strategies/` exists and strategy listing includes a sample strategy. Do not pass `--reset`, because it overwrites generated files.

- [ ] **Step 3: Verify parent repository hygiene**

Run from the parent repository: `git status --short`

Expected: only intentional tracked documentation changes from Task 1 can appear; neither `vendor/freqtrade/` nor `user_data/` appears.

### Task 4: Run the first reproducible SampleStrategy backtest

**Files:**
- Modify: `vendor/freqtrade/user_data/config.json` (ignored; generated interactively without credentials)
- Create: `vendor/freqtrade/user_data/data/` (ignored historical data)
- Create: `vendor/freqtrade/user_data/backtest_results/` (ignored report artifacts)
- Modify: `docs/runbooks/freqtrade-backtesting.md` with actual command, date and upstream commit.
- Test: one successful data-download command and one successful SampleStrategy backtest command.

**Interfaces:**
- Consumes: `user_data` from Task 3 and public Binance spot data.
- Produces: A reproducible backtest command and report for inspection, with no live-trading process.

- [ ] **Step 1: Generate configuration without credentials**

Run from `vendor/freqtrade`:

```bash
docker compose run --rm freqtrade new-config --config user_data/config.json
```

Choose Binance exchange, spot market, `dry_run` enabled, and no API key or API secret. Do not start the trade command.

- [ ] **Step 2: Download fixed public historical data**

Run from `vendor/freqtrade`:

```bash
docker compose run --rm freqtrade download-data --config user_data/config.json --exchange binance --pairs BTC/USDT ETH/USDT --timeframes 1h --timerange 20250101-20251231
```

Expected: historical candles are stored below `user_data/data/`; the command reports both requested pairs.

- [ ] **Step 3: Run the smoke-test backtest**

Run from `vendor/freqtrade`:

```bash
docker compose run --rm freqtrade backtesting --config user_data/config.json --strategy SampleStrategy --timerange 20250101-20251231 -i 1h
```

Expected: Freqtrade prints trade count, profit and max drawdown, or warns explicitly that there were no trades. Either outcome is a valid smoke test; it is not an investment result.

- [ ] **Step 4: Record only reproducibility metadata**

Append to the runbook: execution date, Freqtrade commit from `git -C vendor/freqtrade rev-parse HEAD`, data timerange, pairs, timeframe and full command. Do not commit `config.json`, reports, raw data or logs.

- [ ] **Step 5: Verify safety and commit the runbook update**

Run:

```bash
git status --short
git diff --check
git check-ignore -v vendor/freqtrade/user_data/config.json
```

Expected: generated Freqtrade files are ignored, no whitespace errors occur, and no credential appears in the tracked diff.

Then commit only documentation:

```bash
git add docs/runbooks/freqtrade-backtesting.md
git commit -m "docs: record initial freqtrade backtest"
```

## Spec Coverage Review

- Backtest-only, no credentials, no live trading: Tasks 1 and 4.
- BTC/USDT and ETH/USDT, 1h historical data: Task 4.
- Clone a suitable repo at a stable release: Task 2.
- Docker rather than global Python installation: Tasks 2 and 3.
- Reproducible commands and retained troubleshooting evidence: Tasks 1 and 4.
- No initial ML, RL, futures, leverage, optimization or community strategy: Global Constraints and Tasks 1–4.

