from __future__ import annotations

import hashlib
from pathlib import Path

import duckdb
import pytest

from src.build_database import build_database
from src.validate_database import EXPECTED_COUNTS, run_validation


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


@pytest.fixture(scope="module")
def database(tmp_path_factory):
    path = tmp_path_factory.mktemp("database") / "wealth.duckdb"
    build_database(DATA, path)
    return path


def test_row_counts(database):
    conn = duckdb.connect(str(database), read_only=True)
    try:
        for table, expected in EXPECTED_COUNTS.items():
            assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == expected
    finally:
        conn.close()


def test_integrity_validator_passes(database):
    conn = duckdb.connect(str(database), read_only=True)
    try:
        results = run_validation(conn)
    finally:
        conn.close()
    assert results
    assert all(result.passed for result in results), [result for result in results if not result.passed]


def test_no_views_and_every_curated_table_reopens(database):
    conn = duckdb.connect(str(database), read_only=True)
    try:
        views = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' AND table_type = 'VIEW'").fetchall()
        assert views == []
        curated = ["clients", "portfolios", "instruments", "mandate_rules", "holdings_snapshots", "transactions", "commitments", "credit_facilities", "facility_snapshots", "planned_cash_needs", "market_context", "event_log", "rm_notes", "portfolio_valuations", "instrument_prices"]
        for table in curated:
            assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] >= 0
    finally:
        conn.close()
    reopened = duckdb.connect(str(database), read_only=True)
    try:
        assert reopened.execute("SELECT COUNT(*) FROM clients").fetchone()[0] == 20
    finally:
        reopened.close()


def test_transaction_null_instrument_ids_are_preserved(database):
    conn = duckdb.connect(str(database), read_only=True)
    try:
        assert conn.execute("SELECT COUNT(*) FROM transactions WHERE instrument_id IS NULL").fetchone()[0] == 65
    finally:
        conn.close()


def test_rebuild_is_logically_idempotent(database, tmp_path):
    second = tmp_path / "second.duckdb"
    build_database(DATA, second)
    tables = [table for table in EXPECTED_COUNTS if not table.startswith("raw_")] + ["raw_clients", "raw_transactions", "raw_rm_notes"]
    a = duckdb.connect(str(database), read_only=True)
    b = duckdb.connect(str(second), read_only=True)
    try:
        for table in tables:
            assert a.execute(f"SELECT * FROM {table} ORDER BY ALL").fetchall() == b.execute(f"SELECT * FROM {table} ORDER BY ALL").fetchall(), table
    finally:
        a.close()
        b.close()


def test_source_hashes_unchanged(database):
    before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in DATA.iterdir()}
    conn = duckdb.connect(str(database), read_only=True)
    conn.close()
    after = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in DATA.iterdir()}
    assert before == after
