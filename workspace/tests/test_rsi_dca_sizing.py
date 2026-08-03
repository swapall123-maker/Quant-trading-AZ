import unittest

from rsi_dca_sizing import (
    account_equity,
    action_for_rsi,
    buy_stake,
    continuation_action,
    sell_stake,
)


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

    def test_buy_continuation_below_reference_after_rsi_leaves_oversold(self):
        self.assertEqual(
            continuation_action(45, 29, 99, 100, None),
            "buy_continuation",
        )

    def test_equal_price_is_allowed_only_on_the_crossing_candle(self):
        self.assertEqual(
            continuation_action(45, 30, 100, 100, None),
            "buy_continuation",
        )
        self.assertIsNone(continuation_action(45, 40, 100, 100, None))

    def test_sell_continuation_above_reference_after_rsi_leaves_overbought(self):
        self.assertEqual(
            continuation_action(55, 71, 101, None, 100),
            "sell_continuation",
        )

    def test_continuations_do_not_run_in_normal_or_boundary_rsi_zones(self):
        self.assertIsNone(continuation_action(30, 29, 99, 100, None))
        self.assertIsNone(continuation_action(70, 71, 101, None, 100))

    def test_conflicting_continuations_skip_the_candle(self):
        self.assertIsNone(continuation_action(50, 40, 100, 101, 99))
