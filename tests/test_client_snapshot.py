from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

from src.client_snapshot import SnapshotInputError, build_all_client_snapshots, build_client_snapshot, main


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "wealth.duckdb"


@pytest.fixture(scope="module")
def connection():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    yield con
    con.close()


@pytest.fixture
def cl1_snapshot(connection):
    return build_client_snapshot(connection, "CL-0001", "2026-08-26", "2026-01-01", "2026-08-26")


def test_known_client_and_portfolio_consolidation(cl1_snapshot):
    assert cl1_snapshot["client"]["client_id"] == "CL-0001"
    assert [item["portfolio_id"] for item in cl1_snapshot["portfolios"]] == ["PF-0001", "PF-0002"]
    assert len(cl1_snapshot["holdings"]) == 11
    assert len(cl1_snapshot["planned_cash_needs"]) == 1
    assert len(cl1_snapshot["commitments"]) == 0
    assert len(cl1_snapshot["credit_facilities"]) == 1
    assert len(cl1_snapshot["rm_notes"]) == 2
    assert len(cl1_snapshot["transactions"]) == 21
    assert len(cl1_snapshot["market_events"]) == 15


def test_no_cross_client_data_leakage(cl1_snapshot):
    assert all(item["client_id"] == "CL-0001" for item in cl1_snapshot["portfolios"])
    portfolio_ids = {item["portfolio_id"] for item in cl1_snapshot["portfolios"]}
    assert all(item["client_id"] == "CL-0001" and item["portfolio_id"] in portfolio_ids for item in cl1_snapshot["holdings"])
    for section in ("transactions", "planned_cash_needs", "commitments", "credit_facilities", "rm_notes"):
        assert all(item["client_id"] == "CL-0001" for item in cl1_snapshot[section])


def test_exact_as_of_filtering(cl1_snapshot):
    assert {item["snapshot_date"] for item in cl1_snapshot["holdings"]} == {"2026-08-26"}
    assert {item["snapshot_date"] for item in cl1_snapshot["credit_facilities"]} == {"2026-08-26"}


def test_period_filtering_is_inclusive(connection):
    snapshot = build_client_snapshot(connection, "CL-0001", "2026-08-26", "2026-06-30", "2026-08-26")
    assert all("2026-06-30" <= item["trade_date"] <= "2026-08-26" for item in snapshot["transactions"])
    assert all("2026-06-30" <= item["note_date"] <= "2026-08-26" for item in snapshot["rm_notes"])
    assert all("2026-06-30" <= item["event_date"] <= "2026-08-26" for item in snapshot["market_events"])
    assert any(item["trade_date"] == "2026-06-30" for item in snapshot["transactions"])


def test_portfolio_level_preservation_and_instrument_enrichment(cl1_snapshot):
    holdings_by_portfolio = {portfolio_id: [item for item in cl1_snapshot["holdings"] if item["portfolio_id"] == portfolio_id] for portfolio_id in ("PF-0001", "PF-0002")}
    assert all(holdings_by_portfolio.values())
    assert {item["portfolio_id"] for item in cl1_snapshot["holdings"]} == {"PF-0001", "PF-0002"}
    for holding in cl1_snapshot["holdings"]:
        assert holding["instrument_id"]
        assert "underlying_reference" in holding
        assert "sustainability_excluded" in holding
        assert "concentration_limit_applies" in holding
    assert any(item["underlying_reference"] is None for item in cl1_snapshot["holdings"])


def test_static_sections_and_mandate_details(cl1_snapshot):
    assert cl1_snapshot["client"]["objectives"]
    assert all("mandate_code" in item and "mandate_rules" in item for item in cl1_snapshot["portfolios"])
    assert cl1_snapshot["portfolios"][0]["mandate_rules"]
    for section in ("planned_cash_needs", "commitments", "credit_facilities", "rm_notes", "market_events"):
        assert section in cl1_snapshot
    assert cl1_snapshot["source_references"]
    assert {item["table"] for item in cl1_snapshot["source_references"]} >= {"clients", "portfolios", "holdings_snapshots", "transactions", "planned_cash_needs", "credit_facilities", "rm_notes", "event_log"}


def test_null_preservation(cl1_snapshot):
    # Transactions with no instrument reference remain in the output.
    null_transactions = [item for item in cl1_snapshot["transactions"] if item["instrument_id"] is None]
    assert null_transactions
    assert all("instrument_id" in item for item in null_transactions)
    assert any(item["underlying_reference"] is None for item in cl1_snapshot["holdings"])


def test_invalid_inputs(connection):
    with pytest.raises(SnapshotInputError, match="Unknown client_id"):
        build_client_snapshot(connection, "CL-9999", "2026-08-26")
    with pytest.raises(SnapshotInputError, match="valid available snapshot dates"):
        build_client_snapshot(connection, "CL-0001", "2026-08-27")
    with pytest.raises(SnapshotInputError, match="Invalid period_start"):
        build_client_snapshot(connection, "CL-0001", "2026-08-26", "not-a-date")
    with pytest.raises(SnapshotInputError, match="after period_end"):
        build_client_snapshot(connection, "CL-0001", "2026-08-26", "2026-08-27", "2026-08-26")


def test_cli_missing_database(tmp_path):
    assert main(["--db-path", str(tmp_path / "missing.duckdb"), "--client-id", "CL-0001", "--as-of-date", "2026-08-26"]) == 1


def test_default_period_uses_previous_snapshot(connection):
    snapshot = build_client_snapshot(connection, "CL-0001", "2026-08-26")
    assert snapshot["snapshot_metadata"]["period_start"] == "2026-06-30"
    assert snapshot["snapshot_metadata"]["period_end"] == "2026-08-26"


def test_deterministic_json_and_no_python_only_objects(connection):
    first = build_client_snapshot(connection, "CL-0001", "2026-08-26", "2026-01-01", "2026-08-26")
    second = build_client_snapshot(connection, "CL-0001", "2026-08-26", "2026-01-01", "2026-08-26")
    assert first == second
    json.dumps(first)

    def assert_plain(value):
        assert not isinstance(value, (date, datetime, Decimal))
        if isinstance(value, dict):
            for child in value.values():
                assert_plain(child)
        elif isinstance(value, list):
            for child in value:
                assert_plain(child)

    assert_plain(first)


def test_batch_construction_and_isolation(connection):
    snapshots = build_all_client_snapshots(connection, "2026-08-26", "2026-01-01", "2026-08-26")
    assert len(snapshots) == 20
    assert len({item["snapshot_metadata"]["client_id"] for item in snapshots}) == 20
    for snapshot in snapshots:
        client_id = snapshot["snapshot_metadata"]["client_id"]
        portfolio_ids = {item["portfolio_id"] for item in snapshot["portfolios"]}
        assert snapshot["client"]["client_id"] == client_id
        assert all(item["client_id"] == client_id for item in snapshot["portfolios"])
        assert all(item["client_id"] == client_id and item["portfolio_id"] in portfolio_ids for item in snapshot["holdings"])
        assert all(item["client_id"] == client_id for section in ("transactions", "planned_cash_needs", "commitments", "credit_facilities", "rm_notes") for item in snapshot[section])


def test_read_only_behavior(connection):
    before_tables = connection.execute("SELECT table_name, table_type FROM information_schema.tables WHERE table_schema = 'main' ORDER BY table_name").fetchall()
    before_counts = connection.execute("SELECT table_name, estimated_size FROM duckdb_tables() ORDER BY table_name").fetchall()
    before_mtime = DB_PATH.stat().st_mtime_ns
    build_client_snapshot(connection, "CL-0001", "2026-08-26")
    assert connection.execute("SELECT table_name, table_type FROM information_schema.tables WHERE table_schema = 'main' ORDER BY table_name").fetchall() == before_tables
    assert connection.execute("SELECT table_name, estimated_size FROM duckdb_tables() ORDER BY table_name").fetchall() == before_counts
    assert DB_PATH.stat().st_mtime_ns == before_mtime
