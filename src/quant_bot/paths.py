from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def initialize_data_directories(root: Path = REPOSITORY_ROOT) -> list[Path]:
    """Create ignored runtime directories and return them in deterministic order."""
    paths = [
        root / "data" / "raw",
        root / "data" / "interim",
        root / "data" / "processed",
        root / "artifacts",
        root / "reports" / "generated",
    ]
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
    return paths

