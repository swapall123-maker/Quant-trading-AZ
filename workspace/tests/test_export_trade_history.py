import unittest

from export_trade_history import order_rows


class ExportTradeHistoryTest(unittest.TestCase):
    def test_order_rows_keeps_only_filled_buy_and_sell_orders(self):
        trades = [
            {
                "pair": "BTC/USDT",
                "orders": [
                    {
                        "order_filled_timestamp": 1_577_836_800_000,
                        "ft_order_side": "buy",
                        "ft_order_tag": "rsi_oversold_buy",
                        "safe_price": 7_000,
                        "amount": 0.1,
                        "cost": 700,
                    },
                    {
                        "order_filled_timestamp": 1_577_923_200_000,
                        "ft_order_side": "sell",
                        "ft_order_tag": "rsi_overbought_sell",
                        "safe_price": 7_100,
                        "amount": 0.1,
                        "cost": 710,
                    },
                    {
                        "ft_order_side": "buy",
                        "ft_order_tag": "unfilled",
                        "safe_price": 7_200,
                        "amount": 0.1,
                        "cost": 720,
                    },
                ],
            }
        ]

        rows = order_rows(trades)

        self.assertEqual(
            [row["tag"] for row in rows],
            ["rsi_oversold_buy", "rsi_overbought_sell"],
        )
        self.assertEqual(rows[0]["date"], "2020-01-01T00:00:00+00:00")
        self.assertEqual(rows[1]["side"], "sell")
