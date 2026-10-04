from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import os
from pathlib import Path
from typing import Any

import yaml

from quant_bot.paths import REPOSITORY_ROOT


class ConfigurationError(ValueError):
    """Raised when experiment configuration is incomplete or inconsistent."""


def _date(value: Any, field_name: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ConfigurationError(f"{field_name} must be an ISO date") from exc


@dataclass(frozen=True)
class DataConfig:
    feed: str
    timeframe: str
    adjustment: str
    start: date
    end: date
    market_data_base_url: str


@dataclass(frozen=True)
class UniverseConfig:
    minimum_price: float
    median_dollar_volume_window: int
    minimum_median_dollar_volume: float
    minimum_history_sessions: int
    context_symbols: tuple[str, ...]


@dataclass(frozen=True)
class TargetConfig:
    entry_session_offset: int
    holding_sessions: int


@dataclass(frozen=True)
class CostsConfig:
    commission_per_side: float
    slippage_per_side: float

    @property
    def approximate_round_trip(self) -> float:
        return 2.0 * (self.commission_per_side + self.slippage_per_side)


@dataclass(frozen=True)
class PortfolioConfig:
    starting_capital: float
    maximum_open_positions: int
    maximum_allocation_per_position: float
    allow_leverage: bool
    allow_shorting: bool


@dataclass(frozen=True)
class ValidationConfig:
    initial_training_end: date
    walk_forward_years: tuple[int, ...]
    execution_tuning_start: date
    execution_tuning_end: date
    frozen_test_start: date
    frozen_test_end: date
    embargo_sessions: int


@dataclass(frozen=True)
class ExperimentConfig:
    experiment_id: str
    random_seed: int
    data: DataConfig
    universe: UniverseConfig
    target: TargetConfig
    costs: CostsConfig
    portfolio: PortfolioConfig
    validation: ValidationConfig

    def validate(self) -> None:
        if not self.experiment_id.startswith("EXP-"):
            raise ConfigurationError("experiment_id must start with EXP-")
        if self.data.start >= self.data.end:
            raise ConfigurationError("data.start must be before data.end")
        if self.data.feed != "iex":
            raise ConfigurationError("EXP-001 is frozen to the Alpaca IEX feed")
        if self.target.entry_session_offset < 1:
            raise ConfigurationError("entry must occur after the feature session")
        if self.target.holding_sessions < 1:
            raise ConfigurationError("holding_sessions must be positive")
        if self.validation.embargo_sessions < self.target.holding_sessions:
            raise ConfigurationError("embargo must cover the complete label horizon")
        if not 0.0 <= self.costs.commission_per_side < 0.05:
            raise ConfigurationError("commission_per_side is outside a plausible range")
        if not 0.0 <= self.costs.slippage_per_side < 0.05:
            raise ConfigurationError("slippage_per_side is outside a plausible range")
        if abs(self.costs.approximate_round_trip - 0.003) > 1e-12:
            raise ConfigurationError("EXP-001 round-trip friction must remain 0.30%")
        if self.portfolio.starting_capital <= 0:
            raise ConfigurationError("starting_capital must be positive")
        if self.portfolio.maximum_open_positions != 3:
            raise ConfigurationError("EXP-001 is frozen to three open positions")
        if abs(self.portfolio.maximum_allocation_per_position - 0.20) > 1e-12:
            raise ConfigurationError("EXP-001 allocation must remain 20% per position")
        if self.portfolio.allow_leverage or self.portfolio.allow_shorting:
            raise ConfigurationError("EXP-001 is long-only and unleveraged")
        if self.validation.execution_tuning_end >= self.validation.frozen_test_start:
            raise ConfigurationError("execution tuning must end before the frozen test")
        if self.validation.frozen_test_end > self.data.end:
            raise ConfigurationError("frozen test cannot extend past the data range")


def load_experiment_config(path: Path | str) -> ExperimentConfig:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ConfigurationError("configuration root must be a mapping")

    try:
        data_raw = raw["data"]
        universe_raw = raw["universe"]
        target_raw = raw["target"]
        costs_raw = raw["costs"]
        portfolio_raw = raw["portfolio"]
        validation_raw = raw["validation"]
        config = ExperimentConfig(
            experiment_id=str(raw["experiment_id"]),
            random_seed=int(raw["random_seed"]),
            data=DataConfig(
                feed=str(data_raw["feed"]),
                timeframe=str(data_raw["timeframe"]),
                adjustment=str(data_raw["adjustment"]),
                start=_date(data_raw["start"], "data.start"),
                end=_date(data_raw["end"], "data.end"),
                market_data_base_url=str(data_raw["market_data_base_url"]).rstrip("/"),
            ),
            universe=UniverseConfig(
                minimum_price=float(universe_raw["minimum_price"]),
                median_dollar_volume_window=int(
                    universe_raw["median_dollar_volume_window"]
                ),
                minimum_median_dollar_volume=float(
                    universe_raw["minimum_median_dollar_volume"]
                ),
                minimum_history_sessions=int(universe_raw["minimum_history_sessions"]),
                context_symbols=tuple(str(item) for item in universe_raw["context_symbols"]),
            ),
            target=TargetConfig(
                entry_session_offset=int(target_raw["entry_session_offset"]),
                holding_sessions=int(target_raw["holding_sessions"]),
            ),
            costs=CostsConfig(
                commission_per_side=float(costs_raw["commission_per_side"]),
                slippage_per_side=float(costs_raw["slippage_per_side"]),
            ),
            portfolio=PortfolioConfig(
                starting_capital=float(portfolio_raw["starting_capital"]),
                maximum_open_positions=int(portfolio_raw["maximum_open_positions"]),
                maximum_allocation_per_position=float(
                    portfolio_raw["maximum_allocation_per_position"]
                ),
                allow_leverage=bool(portfolio_raw["allow_leverage"]),
                allow_shorting=bool(portfolio_raw["allow_shorting"]),
            ),
            validation=ValidationConfig(
                initial_training_end=_date(
                    validation_raw["initial_training_end"],
                    "validation.initial_training_end",
                ),
                walk_forward_years=tuple(
                    int(item) for item in validation_raw["walk_forward_years"]
                ),
                execution_tuning_start=_date(
                    validation_raw["execution_tuning_start"],
                    "validation.execution_tuning_start",
                ),
                execution_tuning_end=_date(
                    validation_raw["execution_tuning_end"],
                    "validation.execution_tuning_end",
                ),
                frozen_test_start=_date(
                    validation_raw["frozen_test_start"],
                    "validation.frozen_test_start",
                ),
                frozen_test_end=_date(
                    validation_raw["frozen_test_end"],
                    "validation.frozen_test_end",
                ),
                embargo_sessions=int(validation_raw["embargo_sessions"]),
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigurationError(f"invalid or missing configuration value: {exc}") from exc

    config.validate()
    return config


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            raise ConfigurationError(f"invalid environment line {line_number} in {path}")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


@dataclass(frozen=True, repr=False)
class AlpacaCredentials:
    api_key: str
    secret_key: str

    @classmethod
    def from_environment(cls, root: Path = REPOSITORY_ROOT) -> "AlpacaCredentials":
        file_values: dict[str, str] = {}
        for filename in (".env", ".env.local"):
            file_values.update(_read_env_file(root / filename))
        api_key = os.environ.get("ALPACA_API_KEY") or file_values.get("ALPACA_API_KEY", "")
        secret_key = os.environ.get("ALPACA_SECRET_KEY") or file_values.get(
            "ALPACA_SECRET_KEY", ""
        )
        if not api_key or not secret_key:
            raise ConfigurationError(
                "Alpaca credentials are missing; set environment variables or .env.local"
            )
        return cls(api_key=api_key, secret_key=secret_key)

    def __repr__(self) -> str:
        return "AlpacaCredentials(api_key=<redacted>, secret_key=<redacted>)"

