from __future__ import annotations

import numpy as np
import pandas as pd

from quant_bot.config import CostsConfig, TargetConfig
from quant_bot.data.validation import normalize_bar_frame, validate_bar_frame


class TargetConstructionError(ValueError):
    """Raised when exact target timestamps cannot be constructed safely."""


def _canonical_sessions(values: pd.Series | pd.Index | list[object]) -> pd.DatetimeIndex:
    sessions = pd.DatetimeIndex(pd.to_datetime(values, utc=True, errors="coerce"))
    if sessions.isna().any():
        raise TargetConstructionError("canonical sessions contain invalid timestamps")
    sessions = sessions.normalize().unique().sort_values()
    if len(sessions) < 2:
        raise TargetConstructionError("at least two canonical sessions are required")
    return sessions


def build_open_to_open_targets(
    frame: pd.DataFrame,
    canonical_sessions: pd.Series | pd.Index | list[object],
    target: TargetConfig,
    costs: CostsConfig,
) -> pd.DataFrame:
    """Attach exact future entry/exit opens without using per-symbol row shifts."""
    validate_bar_frame(frame, require_sorted=False)
    bars = normalize_bar_frame(frame).copy()
    bars["session"] = bars["timestamp"].dt.normalize()
    if bars.duplicated(["symbol", "session"]).any():
        raise TargetConstructionError("multiple bars exist for a symbol/session")

    sessions = _canonical_sessions(canonical_sessions)
    schedule_rows: list[dict[str, pd.Timestamp]] = []
    exit_offset = target.entry_session_offset + target.holding_sessions
    for index, feature_session in enumerate(sessions):
        entry_index = index + target.entry_session_offset
        exit_index = index + exit_offset
        if exit_index >= len(sessions):
            continue
        schedule_rows.append(
            {
                "session": feature_session,
                "entry_session": sessions[entry_index],
                "exit_session": sessions[exit_index],
            }
        )
    schedule = pd.DataFrame(schedule_rows)
    if schedule.empty:
        raise TargetConstructionError("session range is too short for the target horizon")

    result = bars.merge(schedule, on="session", how="left", validate="many_to_one")
    lookup = bars[["symbol", "session", "open"]]
    entries = lookup.rename(columns={"session": "entry_session", "open": "entry_open"})
    exits = lookup.rename(columns={"session": "exit_session", "open": "exit_open"})
    result = result.merge(
        entries,
        on=["symbol", "entry_session"],
        how="left",
        validate="many_to_one",
    )
    result = result.merge(
        exits,
        on=["symbol", "exit_session"],
        how="left",
        validate="many_to_one",
    )
    result["target_available"] = (
        result["entry_session"].notna()
        & result["exit_session"].notna()
        & result["entry_open"].notna()
        & result["exit_open"].notna()
    )
    result["gross_forward_return"] = result["exit_open"] / result["entry_open"] - 1.0

    entry_cash = result["entry_open"] * (1.0 + costs.slippage_per_side)
    entry_cash *= 1.0 + costs.commission_per_side
    exit_cash = result["exit_open"] * (1.0 - costs.slippage_per_side)
    exit_cash *= 1.0 - costs.commission_per_side
    result["net_forward_return"] = exit_cash / entry_cash - 1.0
    unavailable = ~result["target_available"]
    result.loc[unavailable, ["gross_forward_return", "net_forward_return"]] = np.nan
    return result.sort_values(["symbol", "timestamp"], kind="stable").reset_index(drop=True)

