"""Export filled Freqtrade backtest orders as a compact CSV history."""

import csv
import json
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path


FIELDNAMES = ["date", "pair", "side", "tag", "price", "amount", "cost"]


def order_rows(trades: list[dict]) -> list[dict[str, object]]:
    """Return one CSV-ready row per filled buy or sell order."""
    rows: list[dict[str, object]] = []
    seen_orders: set[tuple[object, ...]] = set()
    for trade in trades:
        for order in trade.get("orders", []):
            timestamp = order.get("order_filled_timestamp")
            side = order.get("ft_order_side")
            amount = order.get("amount", 0)
            if timestamp is None or side not in {"buy", "sell"} or amount <= 0:
                continue
            identity = (
                trade.get("pair", ""),
                timestamp,
                side,
                order.get("ft_order_tag", ""),
                order.get("safe_price", ""),
                amount,
                order.get("cost", ""),
            )
            if identity in seen_orders:
                continue
            seen_orders.add(identity)
            rows.append(
                {
                    "date": datetime.fromtimestamp(timestamp / 1000, UTC).isoformat(),
                    "pair": trade.get("pair", ""),
                    "side": side,
                    "tag": order.get("ft_order_tag", ""),
                    "price": order.get("safe_price", ""),
                    "amount": amount,
                    "cost": order.get("cost", ""),
                }
            )
    return rows


def newest_backtest_zip(results_dir: Path) -> Path:
    """Find the most recently produced Freqtrade result archive."""
    archives = list(results_dir.glob("backtest-result-*.zip"))
    if not archives:
        raise FileNotFoundError(f"No Freqtrade backtest zip found in {results_dir}")
    return max(archives, key=lambda path: path.stat().st_mtime)


def load_trades(results_dir: Path) -> list[dict]:
    """Load all strategy trade lists from the newest Freqtrade result archive."""
    archive = newest_backtest_zip(results_dir)
    with zipfile.ZipFile(archive) as zip_file:
        members = [
            name
            for name in zip_file.namelist()
            if name.startswith("backtest-result-")
            and name.endswith(".json")
            and not name.endswith("_config.json")
            and not name.endswith(".meta.json")
        ]
        if not members:
            raise FileNotFoundError(f"No backtest JSON member found in {archive}")
        result = json.loads(zip_file.read(members[0]))

    trades: list[dict] = []
    for strategy in result.get("strategy", {}).values():
        trades.extend(strategy.get("trades", []))
    return trades


def write_csv(rows: list[dict[str, object]], output_path: Path) -> None:
    """Write stable CSV columns for spreadsheet inspection."""
    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main(arguments: list[str]) -> int:
    if len(arguments) != 2:
        print("Usage: export_trade_history.py <backtest-results-dir> <output-csv>")
        return 2

    results_dir = Path(arguments[0])
    output_path = Path(arguments[1])
    write_csv(order_rows(load_trades(results_dir)), output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
