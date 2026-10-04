import unittest

from quant_bot.data.alpaca import AlpacaDataError, normalize_bars_payload


class AlpacaPayloadTests(unittest.TestCase):
    def test_symbol_keyed_payload_is_normalized(self) -> None:
        payload = {
            "bars": {
                "AAA": [
                    {
                        "t": "2026-01-02T05:00:00Z",
                        "o": 10.0,
                        "h": 11.0,
                        "l": 9.0,
                        "c": 10.5,
                        "v": 1000,
                        "n": 25,
                        "vw": 10.2,
                    }
                ]
            },
            "next_page_token": None,
        }
        frame = normalize_bars_payload(payload)
        self.assertEqual(frame.loc[0, "symbol"], "AAA")
        self.assertEqual(frame.loc[0, "trade_count"], 25)
        self.assertEqual(frame.loc[0, "vwap"], 10.2)

    def test_malformed_payload_fails_loudly(self) -> None:
        with self.assertRaises(AlpacaDataError):
            normalize_bars_payload({"bars": []})


if __name__ == "__main__":
    unittest.main()
