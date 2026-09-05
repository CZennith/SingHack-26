from __future__ import annotations

import hashlib
from pathlib import Path

import duckdb
import pytest

from src.client_snapshot import build_client_snapshot, validate_snapshot


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "wealth.duckdb"
OUTPUTS_PATH = ROOT / "outputs"


def _tree_fingerprint(root: Path) -> tuple[tuple[str, str, str], ...]:
    if not root.exists():
        return ()
    entries: list[tuple[str, str, str]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            entries.append((relative, "directory", ""))
        elif path.is_file():
            entries.append((relative, "file", hashlib.sha256(path.read_bytes()).hexdigest()))
        else:
            entries.append((relative, "other", ""))
    return tuple(entries)


@pytest.fixture(scope="session", autouse=True)
def generated_outputs_are_immutable_during_tests():
    """Make accidental coupling to or mutation of generated outputs visible."""
    before = _tree_fingerprint(OUTPUTS_PATH)
    yield
    assert _tree_fingerprint(OUTPUTS_PATH) == before, (
        "the test suite modified outputs/; tests must use tmp_path or checked-in fixtures"
    )


@pytest.fixture(scope="session")
def client_snapshot_0001() -> dict:
    connection = duckdb.connect(str(DB_PATH.resolve()), read_only=True)
    try:
        snapshot = build_client_snapshot(
            connection,
            "CL-0001",
            "2026-08-26",
            period_start="2026-01-01",
            period_end="2026-08-26",
        )
    finally:
        connection.close()
    return validate_snapshot(snapshot)
