import unittest

import pandas as pd

from quant_bot.data.validation import DataValidationError, validate_bar_frame


def valid_bars() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "symbol": ["AAA", "AAA", "BBB"],
            "timestamp": [
                "2026-01-02T05:00:00Z",
                "2026-01-05T05:00:00Z",
                "2026-01-02T05:00:00Z",
            ],
            "open": [10.0, 10.5, 20.0],
            "high": [11.0, 11.0, 21.0],
            "low": [9.5, 10.0, 19.0],
            "close": [10.5, 10.8, 20.5],
            "volume": [1000, 1200, 900],
        }
    )


class BarValidationTests(unittest.TestCase):
    def test_valid_frame_reports_shape(self) -> None:
        report = validate_bar_frame(valid_bars())
        self.assertEqual(report.rows, 3)
        self.assertEqual(report.symbols, 2)

    def test_duplicate_symbol_timestamp_is_rejected(self) -> None:
        frame = pd.concat([valid_bars(), valid_bars().iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(DataValidationError, "duplicate"):
            validate_bar_frame(frame)

    def test_impossible_high_is_rejected(self) -> None:
        frame = valid_bars()
        frame.loc[0, "high"] = 9.0
        with self.assertRaisesRegex(DataValidationError, "high"):
            validate_bar_frame(frame)

    def test_unsorted_symbol_history_is_rejected(self) -> None:
        frame = valid_bars().iloc[[1, 0, 2]].reset_index(drop=True)
        with self.assertRaisesRegex(DataValidationError, "not increasing"):
            validate_bar_frame(frame)


if __name__ == "__main__":
    unittest.main()

