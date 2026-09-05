from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from src.build_database import build_database
from src.validate_database import SNAPSHOT_DATES


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def connection(tmp_path_factory):
    db = tmp_path_factory.mktemp("quality") / "wealth.duckdb"
    build_database(ROOT / "data", db)
    conn = duckdb.connect(str(db), read_only=True)
    yield conn
    conn.close()


def test_normalized_snapshot_grains(connection):
    assert connection.execute("SELECT COUNT(*) FROM portfolio_valuations").fetchone()[0] == 120
    assert connection.execute("SELECT COUNT(*) FROM instrument_prices").fetchone()[0] == 310
    assert connection.execute("SELECT COUNT(*) FROM facility_snapshots").fetchone()[0] == 25
    for table, key in (("portfolio_valuations", "portfolio_id, snapshot_date"), ("instrument_prices", "instrument_id, snapshot_date"), ("facility_snapshots", "facility_id, snapshot_date")):
        assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == connection.execute(f"SELECT COUNT(DISTINCT ({key})) FROM {table}").fetchone()[0]


def test_snapshot_dates_are_exact(connection):
    expected = set(SNAPSHOT_DATES)
    for table in ("holdings_snapshots", "portfolio_valuations", "instrument_prices", "facility_snapshots"):
        actual = {row[0].isoformat() for row in connection.execute(f"SELECT DISTINCT snapshot_date FROM {table}").fetchall()}
        assert actual == expected


def test_nullable_source_fields_remain_nullable(connection):
    assert connection.execute("SELECT COUNT(*) FROM clients WHERE age IS NULL").fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM holdings_snapshots WHERE sector IS NULL").fetchone()[0] == 5
    assert connection.execute("SELECT COUNT(*) FROM instruments WHERE underlying_reference IS NULL").fetchone()[0] == 53


def test_key_relationships_have_no_orphans(connection):
    checks = [
        ("portfolios", "client_id", "clients", "client_id"),
        ("holdings_snapshots", "portfolio_id", "portfolios", "portfolio_id"),
        ("holdings_snapshots", "instrument_id", "instruments", "instrument_id"),
        ("transactions", "portfolio_id", "portfolios", "portfolio_id"),
        ("commitments", "client_id", "clients", "client_id"),
        ("credit_facilities", "collateral_portfolio_id", "portfolios", "portfolio_id"),
        ("planned_cash_needs", "client_id", "clients", "client_id"),
        ("rm_notes", "client_id", "clients", "client_id"),
    ]
    for child, child_col, parent, parent_col in checks:
        count = connection.execute(f"SELECT COUNT(*) FROM {child} c LEFT JOIN {parent} p ON c.{child_col} = p.{parent_col} WHERE p.{parent_col} IS NULL").fetchone()[0]
        assert count == 0, (child, child_col)
