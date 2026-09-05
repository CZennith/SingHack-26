"""Single entry point for loading the deterministic CSV data set."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_all(data_dir: Path) -> dict[str, pd.DataFrame]:
    """Read every CSV in ``data_dir`` once, keyed by its filename stem."""
    return {
        csv_path.stem: pd.read_csv(csv_path)
        for csv_path in sorted(data_dir.glob("*.csv"))
    }