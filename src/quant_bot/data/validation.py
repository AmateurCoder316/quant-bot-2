from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


REQUIRED_BAR_COLUMNS = (
    "symbol",
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
)


class DataValidationError(ValueError):
    """Raised when market data violates a required invariant."""


@dataclass(frozen=True)
class BarValidationReport:
    rows: int
    symbols: int
    first_timestamp: pd.Timestamp
    last_timestamp: pd.Timestamp


def normalize_bar_frame(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in REQUIRED_BAR_COLUMNS if column not in frame.columns]
    if missing:
        raise DataValidationError(f"missing bar columns: {', '.join(missing)}")

    result = frame.copy()
    result["symbol"] = result["symbol"].astype("string").str.strip().str.upper()
    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
    for column in ("open", "high", "low", "close", "volume"):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    return result


def validate_bar_frame(
    frame: pd.DataFrame,
    *,
    require_sorted: bool = True,
) -> BarValidationReport:
    bars = normalize_bar_frame(frame)
    if bars.empty:
        raise DataValidationError("bar frame is empty")
    if bars["symbol"].isna().any() or (bars["symbol"].str.len() == 0).any():
        raise DataValidationError("symbol contains missing or blank values")
    if bars["timestamp"].isna().any():
        raise DataValidationError("timestamp contains invalid values")

    numeric = bars[["open", "high", "low", "close", "volume"]].to_numpy(dtype=float)
    if not np.isfinite(numeric).all():
        raise DataValidationError("bar frame contains NaN or infinite numeric values")
    if (bars[["open", "high", "low", "close"]] <= 0).any(axis=None):
        raise DataValidationError("OHLC prices must be positive")
    if (bars["volume"] < 0).any():
        raise DataValidationError("volume must be non-negative")
    if bars.duplicated(["symbol", "timestamp"]).any():
        raise DataValidationError("duplicate symbol/timestamp rows detected")

    max_body = bars[["open", "close", "low"]].max(axis=1)
    min_body = bars[["open", "close", "high"]].min(axis=1)
    if (bars["high"] < max_body).any():
        raise DataValidationError("high is below open, close, or low")
    if (bars["low"] > min_body).any():
        raise DataValidationError("low is above open, close, or high")

    if require_sorted:
        unsorted = [
            str(symbol)
            for symbol, group in bars.groupby("symbol", sort=False)
            if not group["timestamp"].is_monotonic_increasing
        ]
        if unsorted:
            preview = ", ".join(unsorted[:5])
            raise DataValidationError(f"timestamps are not increasing for: {preview}")

    return BarValidationReport(
        rows=len(bars),
        symbols=int(bars["symbol"].nunique()),
        first_timestamp=bars["timestamp"].min(),
        last_timestamp=bars["timestamp"].max(),
    )

