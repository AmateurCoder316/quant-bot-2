from __future__ import annotations

import pandas as pd

from quant_bot.config import UniverseConfig
from quant_bot.data.validation import normalize_bar_frame, validate_bar_frame


def add_causal_universe_eligibility(
    frame: pd.DataFrame,
    config: UniverseConfig,
) -> pd.DataFrame:
    """Add eligibility using only values available through each row's timestamp."""
    validate_bar_frame(frame, require_sorted=False)
    bars = normalize_bar_frame(frame).sort_values(
        ["symbol", "timestamp"], kind="stable"
    )
    bars["dollar_volume"] = bars["close"] * bars["volume"]
    grouped = bars.groupby("symbol", sort=False, group_keys=False)
    bars["history_sessions"] = grouped.cumcount() + 1
    bars["median_dollar_volume"] = grouped["dollar_volume"].transform(
        lambda values: values.rolling(
            config.median_dollar_volume_window,
            min_periods=config.median_dollar_volume_window,
        ).median()
    )
    is_context = bars["symbol"].isin(config.context_symbols)
    bars["eligible"] = (
        ~is_context
        & (bars["close"] >= config.minimum_price)
        & (bars["history_sessions"] >= config.minimum_history_sessions)
        & (bars["median_dollar_volume"] >= config.minimum_median_dollar_volume)
    )
    return bars.reset_index(drop=True)

