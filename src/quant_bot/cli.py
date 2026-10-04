from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

from quant_bot.config import AlpacaCredentials, load_experiment_config
from quant_bot.data.alpaca import AlpacaDataClient
from quant_bot.data.manifest import write_manifest
from quant_bot.data.validation import validate_bar_frame
from quant_bot.paths import REPOSITORY_ROOT, initialize_data_directories


DEFAULT_CONFIG = REPOSITORY_ROOT / "config" / "exp-001.yaml"
DEFAULT_SYMBOLS = REPOSITORY_ROOT / "config" / "universe-exp-001.txt"


def _read_symbols(path: Path) -> list[str]:
    return [
        line.strip().upper()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _read_bars(path: Path) -> pd.DataFrame:
    suffixes = path.suffixes
    if suffixes[-2:] == [".csv", ".gz"] or path.suffix == ".csv":
        return pd.read_csv(path)
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    raise ValueError("bar input must be .csv, .csv.gz, or .parquet")


def _command_validate_config(args: argparse.Namespace) -> int:
    config = load_experiment_config(args.config)
    print(f"valid: {config.experiment_id}")
    print(f"data: {config.data.start} through {config.data.end} ({config.data.feed})")
    print(f"approximate round-trip friction: {config.costs.approximate_round_trip:.2%}")
    print(
        "portfolio: "
        f"${config.portfolio.starting_capital:,.0f}, "
        f"{config.portfolio.maximum_open_positions} positions, "
        f"{config.portfolio.maximum_allocation_per_position:.0%} each"
    )
    return 0


def _command_init_dirs(args: argparse.Namespace) -> int:
    for path in initialize_data_directories(args.root):
        print(path)
    return 0


def _command_validate_bars(args: argparse.Namespace) -> int:
    report = validate_bar_frame(_read_bars(args.path))
    print(f"rows: {report.rows:,}")
    print(f"symbols: {report.symbols:,}")
    print(f"range: {report.first_timestamp} through {report.last_timestamp}")
    return 0


def _command_download_bars(args: argparse.Namespace) -> int:
    config = load_experiment_config(args.config)
    credentials = AlpacaCredentials.from_environment(REPOSITORY_ROOT)
    symbols = _read_symbols(args.symbols)
    symbols.extend(config.universe.context_symbols)
    raw_directory = REPOSITORY_ROOT / "data" / "raw" / "alpaca" / config.experiment_id.lower()
    client = AlpacaDataClient(
        credentials,
        base_url=config.data.market_data_base_url,
    )
    result = client.download_daily_bars(
        symbols,
        start=config.data.start,
        end=config.data.end,
        feed=config.data.feed,
        adjustment=config.data.adjustment,
        raw_directory=raw_directory,
    )
    report = validate_bar_frame(result.bars)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.bars.to_csv(args.output, index=False, compression="gzip")
    manifest_path = args.output.with_suffix(args.output.suffix + ".manifest.json")
    write_manifest(
        manifest_path,
        [*result.raw_pages, args.output],
        metadata={
            "experiment_id": config.experiment_id,
            "feed": config.data.feed,
            "timeframe": config.data.timeframe,
            "adjustment": config.data.adjustment,
            "start": config.data.start.isoformat(),
            "end": config.data.end.isoformat(),
            "symbols_requested": len(set(symbols)),
            "rows": report.rows,
            "symbols_received": report.symbols,
        },
    )
    print(f"wrote {report.rows:,} rows for {report.symbols} symbols to {args.output}")
    print(f"manifest: {manifest_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quant-bot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_config = subparsers.add_parser("validate-config")
    validate_config.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    validate_config.set_defaults(handler=_command_validate_config)

    init_dirs = subparsers.add_parser("init-dirs")
    init_dirs.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    init_dirs.set_defaults(handler=_command_init_dirs)

    validate_bars = subparsers.add_parser("validate-bars")
    validate_bars.add_argument("path", type=Path)
    validate_bars.set_defaults(handler=_command_validate_bars)

    download_bars = subparsers.add_parser("download-bars")
    download_bars.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    download_bars.add_argument("--symbols", type=Path, default=DEFAULT_SYMBOLS)
    download_bars.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "data" / "raw" / "exp-001-daily-bars.csv.gz",
    )
    download_bars.set_defaults(handler=_command_download_bars)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

