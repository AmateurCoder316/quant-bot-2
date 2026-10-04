from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import time
from typing import Any, Iterable, Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from quant_bot.config import AlpacaCredentials


class AlpacaDataError(RuntimeError):
    """Raised for exhausted or malformed Alpaca data requests."""


@dataclass(frozen=True)
class DownloadResult:
    bars: pd.DataFrame
    raw_pages: tuple[Path, ...]


def _chunks(values: list[str], size: int) -> Iterator[list[str]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def normalize_bars_payload(payload: dict[str, Any]) -> pd.DataFrame:
    bars_by_symbol = payload.get("bars")
    if not isinstance(bars_by_symbol, dict):
        raise AlpacaDataError("response does not contain a symbol-keyed bars object")
    rows: list[dict[str, Any]] = []
    for symbol, records in bars_by_symbol.items():
        if not isinstance(records, list):
            raise AlpacaDataError(f"bars for {symbol} are not a list")
        for record in records:
            rows.append(
                {
                    "symbol": symbol,
                    "timestamp": record.get("t"),
                    "open": record.get("o"),
                    "high": record.get("h"),
                    "low": record.get("l"),
                    "close": record.get("c"),
                    "volume": record.get("v"),
                    "trade_count": record.get("n"),
                    "vwap": record.get("vw"),
                }
            )
    return pd.DataFrame(rows)


class AlpacaDataClient:
    def __init__(
        self,
        credentials: AlpacaCredentials,
        *,
        base_url: str = "https://data.alpaca.markets",
        timeout_seconds: float = 30.0,
        maximum_attempts: int = 5,
    ) -> None:
        self._credentials = credentials
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._maximum_attempts = maximum_attempts

    def _get_json(self, path: str, parameters: dict[str, str]) -> dict[str, Any]:
        url = f"{self._base_url}{path}?{urlencode(parameters)}"
        request = Request(
            url,
            headers={
                "APCA-API-KEY-ID": self._credentials.api_key,
                "APCA-API-SECRET-KEY": self._credentials.secret_key,
                "Accept": "application/json",
                "User-Agent": "quant-bot-2/0.1 research-only",
            },
        )
        for attempt in range(1, self._maximum_attempts + 1):
            try:
                with urlopen(request, timeout=self._timeout_seconds) as response:
                    payload = json.load(response)
                if not isinstance(payload, dict):
                    raise AlpacaDataError("Alpaca returned a non-object JSON response")
                return payload
            except HTTPError as exc:
                retryable = exc.code == 429 or 500 <= exc.code < 600
                if not retryable or attempt == self._maximum_attempts:
                    raise AlpacaDataError(f"Alpaca request failed with HTTP {exc.code}") from exc
            except URLError as exc:
                if attempt == self._maximum_attempts:
                    raise AlpacaDataError("Alpaca request failed after retries") from exc
            time.sleep(min(2 ** (attempt - 1), 16))
        raise AssertionError("retry loop exited unexpectedly")

    def download_daily_bars(
        self,
        symbols: Iterable[str],
        *,
        start: date,
        end: date,
        feed: str,
        adjustment: str,
        raw_directory: Path | None = None,
        symbol_chunk_size: int = 100,
    ) -> DownloadResult:
        unique_symbols = sorted({symbol.strip().upper() for symbol in symbols if symbol.strip()})
        if not unique_symbols:
            raise AlpacaDataError("no symbols were supplied")
        if start >= end:
            raise AlpacaDataError("download start must be before end")
        frames: list[pd.DataFrame] = []
        raw_pages: list[Path] = []
        if raw_directory is not None:
            raw_directory.mkdir(parents=True, exist_ok=True)

        for chunk_number, symbol_chunk in enumerate(
            _chunks(unique_symbols, symbol_chunk_size), start=1
        ):
            page_token: str | None = None
            page_number = 0
            while True:
                page_number += 1
                parameters = {
                    "symbols": ",".join(symbol_chunk),
                    "timeframe": "1Day",
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "adjustment": adjustment,
                    "feed": feed,
                    "sort": "asc",
                    "limit": "10000",
                }
                if page_token:
                    parameters["page_token"] = page_token
                payload = self._get_json("/v2/stocks/bars", parameters)
                frames.append(normalize_bars_payload(payload))
                if raw_directory is not None:
                    raw_path = raw_directory / (
                        f"bars_chunk_{chunk_number:03d}_page_{page_number:04d}.json"
                    )
                    temporary = raw_path.with_suffix(".json.tmp")
                    temporary.write_text(
                        json.dumps(payload, separators=(",", ":")), encoding="utf-8"
                    )
                    temporary.replace(raw_path)
                    raw_pages.append(raw_path)
                token_value = payload.get("next_page_token")
                page_token = str(token_value) if token_value else None
                if page_token is None:
                    break

        nonempty = [frame for frame in frames if not frame.empty]
        if not nonempty:
            raise AlpacaDataError("Alpaca returned no bars for the requested symbols and dates")
        bars = pd.concat(nonempty, ignore_index=True)
        bars = bars.sort_values(["symbol", "timestamp"], kind="stable").reset_index(drop=True)
        return DownloadResult(bars=bars, raw_pages=tuple(raw_pages))

