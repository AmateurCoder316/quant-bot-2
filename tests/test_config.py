from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from quant_bot.config import AlpacaCredentials, ConfigurationError, load_experiment_config
from quant_bot.paths import REPOSITORY_ROOT


class ConfigurationTests(unittest.TestCase):
    def test_official_config_is_valid_and_costs_are_frozen(self) -> None:
        config = load_experiment_config(REPOSITORY_ROOT / "config" / "exp-001.yaml")
        self.assertEqual(config.experiment_id, "EXP-001")
        self.assertAlmostEqual(config.costs.approximate_round_trip, 0.003)
        self.assertEqual(config.portfolio.maximum_open_positions, 3)
        self.assertFalse(config.portfolio.allow_leverage)

    def test_credentials_load_from_ignored_local_file_and_repr_is_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env.local").write_text(
                "ALPACA_API_KEY=test-key\nALPACA_SECRET_KEY=test-secret\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                credentials = AlpacaCredentials.from_environment(root)
            self.assertEqual(credentials.api_key, "test-key")
            self.assertNotIn("test-key", repr(credentials))
            self.assertNotIn("test-secret", repr(credentials))

    def test_missing_credentials_fail_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(ConfigurationError):
                    AlpacaCredentials.from_environment(Path(directory))


if __name__ == "__main__":
    unittest.main()
