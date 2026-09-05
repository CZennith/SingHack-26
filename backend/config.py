"""Runtime configuration for local/private and preview/demo modes.

Database-backed API functions use this configuration and open ``wealth_db_path``
with DuckDB's read-only option. Demo mode remains the safe default.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "db" / "wealth.duckdb"


class ConfigurationError(ValueError):
    """The runtime data-source configuration is unsafe or incomplete."""


def _boolean(value: str | None) -> bool:
    if value is None:
        return True
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError("DEMO_MODE must be true or false")


@dataclass(frozen=True)
class RuntimeConfig:
    demo_mode: bool
    wealth_db_path: Path | None


def load_runtime_config(environment: Mapping[str, str] | None = None) -> RuntimeConfig:
    """Load safe runtime settings without opening or modifying any data source."""
    values = os.environ if environment is None else environment
    demo_mode = _boolean(values.get("DEMO_MODE"))
    configured_path = values.get("WEALTH_DB_PATH", "").strip()
    database_path = Path(configured_path).expanduser().resolve() if configured_path else None
    if not demo_mode and database_path is None:
        raise ConfigurationError("WEALTH_DB_PATH is required when DEMO_MODE=false")
    return RuntimeConfig(demo_mode=demo_mode, wealth_db_path=database_path)
