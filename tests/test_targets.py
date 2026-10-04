import unittest

import pandas as pd

from quant_bot.config import CostsConfig, TargetConfig
from quant_bot.data.targets import build_open_to_open_targets


def make_bars(missing_session: str | None = None) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    sessions = pd.bdate_range("2026-01-02", periods=9, tz="UTC")
    rows = []
    for index, session in enumerate(sessions):
        if missing_session and session.date().isoformat() == missing_session:
            continue
        price = 100.0 + index
        rows.append(
            {
                "symbol": "AAA",
                "timestamp": session,
                "open": price,
                "high": price + 1,
                "low": price - 1,
                "close": price + 0.5,
                "volume": 1_000_000,
            }
        )
    return pd.DataFrame(rows), sessions


class TargetConstructionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.target = TargetConfig(entry_session_offset=1, holding_sessions=5)
        self.costs = CostsConfig(commission_per_side=0.001, slippage_per_side=0.0005)

    def test_exact_entry_and_exit_sessions_are_used(self) -> None:
        bars, sessions = make_bars()
        targets = build_open_to_open_targets(bars, sessions, self.target, self.costs)
        first = targets.iloc[0]
        self.assertEqual(first["entry_session"], sessions[1])
        self.assertEqual(first["exit_session"], sessions[6])
        self.assertAlmostEqual(first["gross_forward_return"], 106.0 / 101.0 - 1.0)
        self.assertLess(first["net_forward_return"], first["gross_forward_return"])

    def test_missing_future_exit_marks_target_unavailable_instead_of_shifting(self) -> None:
        bars, sessions = make_bars(missing_session="2026-01-12")
        targets = build_open_to_open_targets(bars, sessions, self.target, self.costs)
        first = targets.iloc[0]
        self.assertEqual(first["exit_session"].date().isoformat(), "2026-01-12")
        self.assertFalse(bool(first["target_available"]))
        self.assertTrue(pd.isna(first["gross_forward_return"]))


if __name__ == "__main__":
    unittest.main()

