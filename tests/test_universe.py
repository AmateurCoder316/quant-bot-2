import unittest

import pandas as pd

from quant_bot.config import UniverseConfig
from quant_bot.data.universe import add_causal_universe_eligibility


class UniverseTests(unittest.TestCase):
    def test_eligibility_uses_only_current_and_past_rows(self) -> None:
        frame = pd.DataFrame(
            {
                "symbol": ["AAA", "AAA", "AAA"],
                "timestamp": pd.to_datetime(
                    ["2026-01-02", "2026-01-05", "2026-01-09"], utc=True
                ),
                "open": [10.0, 11.0, 12.0],
                "high": [11.0, 12.0, 13.0],
                "low": [9.0, 10.0, 11.0],
                "close": [10.0, 11.0, 12.0],
                "volume": [100.0, 100.0, 100.0],
            }
        )
        config = UniverseConfig(
            minimum_price=5.0,
            median_dollar_volume_window=2,
            minimum_median_dollar_volume=1_000.0,
            minimum_history_sessions=2,
            context_symbols=("SPY",),
        )
        with_future_gap = add_causal_universe_eligibility(frame, config)
        without_future_row = add_causal_universe_eligibility(frame.iloc[:2], config)
        self.assertTrue(bool(with_future_gap.loc[1, "eligible"]))
        self.assertEqual(
            bool(with_future_gap.loc[1, "eligible"]),
            bool(without_future_row.loc[1, "eligible"]),
        )


if __name__ == "__main__":
    unittest.main()

