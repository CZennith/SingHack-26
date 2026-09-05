from __future__ import annotations

import json
from pathlib import Path
from decimal import Decimal

import duckdb
import pytest

from src.calculators.exposure_base import ExposureInputError, build_exposure_base
from src.client_snapshot import build_client_snapshot, validate_snapshot


DB = str(Path(__file__).resolve().parents[2] / "db" / "wealth.duckdb")


def _snapshot(con, client_id: str, as_of: str):
    return build_client_snapshot(con, client_id, as_of)


@pytest.fixture(scope="module")
def connection():
    con = duckdb.connect(DB, read_only=True)
    yield con
    con.close()


def test_every_client_builds_valid_exposure_base(connection):
    client_ids = [row[0] for row in connection.execute("SELECT client_id FROM clients ORDER BY client_id").fetchall()]
    assert len(client_ids) == 20
    for client_id in client_ids:
        base = build_exposure_base(_snapshot(connection, client_id, "2026-08-26"))
        assert base["exposure_metadata"]["client_id"] == client_id
        assert base["exposure_metadata"]["look_through_included"] is False
        json.dumps(base, allow_nan=False)
        assert base["client_total"]["portfolio_count"] >= 1


def test_no_cross_client_leakage(connection):
    client_ids = {row[0] for row in connection.execute("SELECT client_id FROM clients").fetchall()}
    for client_id in sorted(client_ids):
        base = build_exposure_base(_snapshot(connection, client_id, "2026-08-26"))
        assert base["exposure_metadata"]["client_id"] == client_id
        encoded = json.dumps(base)
        for other_client_id in client_ids - {client_id}:
            assert other_client_id not in encoded
        assert all(ref["keys"]["client_id"] == client_id for ref in base["source_references"])


def test_portfolio_and_dimension_conservation(connection):
    for client_id, in connection.execute("SELECT client_id FROM clients ORDER BY client_id").fetchall():
        base = build_exposure_base(_snapshot(connection, client_id, "2026-08-26"))
        total = Decimal(str(base["client_total"]["market_value_usd"]))
        portfolio_total = sum((Decimal(str(row["market_value_usd"])) for row in base["by_portfolio"]), Decimal(0))
        assert abs(portfolio_total - total) <= Decimal("0.0001")
        for table in ("by_asset_class", "by_sub_asset_class", "by_sector", "by_region", "by_currency", "by_instrument"):
            dimension_total = sum((Decimal(str(row["market_value_usd"])) for row in base[table]), Decimal(0))
            assert abs(dimension_total - total) <= Decimal("0.0001"), (client_id, table)


def test_weight_totals_and_known_cl1_regression(connection):
    base = build_exposure_base(_snapshot(connection, "CL-0001", "2026-08-26"))
    assert base["client_total"]["holding_count"] == 11
    assert base["client_total"]["market_value_usd"] == pytest.approx(46571821.48)
    values = {row["portfolio_id"]: row["market_value_usd"] for row in base["by_portfolio"]}
    assert values["PF-0001"] == pytest.approx(26883844.94)
    assert values["PF-0002"] == pytest.approx(19687976.54)
    for table in ("by_asset_class", "by_sub_asset_class", "by_sector", "by_region", "by_currency", "by_instrument"):
        assert sum(row["weight_pct"] for row in base[table]) == pytest.approx(100.0, abs=0.0001)
    assert all(row["weight_pct"] == pytest.approx(100.0) for row in base["by_portfolio"])


def test_empty_holdings_returns_zero_with_warning():
    snapshot = {
        "snapshot_metadata": {"client_id": "CL-X", "as_of_date": "2026-08-26", "period_start": "2026-06-30", "period_end": "2026-08-26", "calculation_version": "1.0.0"},
        "client": {"client_id": "CL-X"},
        "portfolios": [{"portfolio_id": "PF-X", "client_id": "CL-X"}],
        "portfolio_summaries": [], "holdings": [], "transactions": [], "planned_cash_needs": [],
        "commitments": [], "credit_facilities": [], "rm_notes": [], "market_events": [],
        "data_quality_flags": [], "source_references": [],
    }
    base = build_exposure_base(snapshot)
    assert base["client_total"] == {"market_value_usd": 0.0, "holding_count": 0, "portfolio_count": 1}
    assert base["warnings"][0]["warning_type"] == "empty_holdings"


def test_null_dimensions_are_retained_with_warning():
    snapshot = {
        "snapshot_metadata": {"client_id": "CL-X", "as_of_date": "2026-08-26", "period_start": "2026-06-30", "period_end": "2026-08-26", "calculation_version": "1.0.0"},
        "client": {"client_id": "CL-X"},
        "portfolios": [{"portfolio_id": "PF-X", "client_id": "CL-X"}],
        "portfolio_summaries": [],
        "holdings": [{"snapshot_date": "2026-08-26", "portfolio_id": "PF-X", "client_id": "CL-X", "instrument_id": "I-X", "instrument_name": "Example", "asset_class": "Equity", "sub_asset_class": "Equity", "sector": None, "region": None, "instrument_ccy": "USD", "market_value_usd": 100.0, "underlying_reference": None}],
        "transactions": [], "planned_cash_needs": [], "commitments": [], "credit_facilities": [], "rm_notes": [], "market_events": [], "data_quality_flags": [], "source_references": [],
    }
    base = build_exposure_base(snapshot)
    assert len(base["by_sector"]) == 1 and base["by_sector"][0]["key"] is None
    assert len(base["by_region"]) == 1 and base["by_region"][0]["key"] is None
    assert {warning["dimension"] for warning in base["warnings"]} == {"sector", "region"}


def test_duplicate_holding_identity_and_malformed_numeric_reject():
    holding = {"snapshot_date": "2026-08-26", "portfolio_id": "PF-X", "client_id": "CL-X", "instrument_id": "I-X", "instrument_name": "Example", "asset_class": "Equity", "sub_asset_class": "Equity", "sector": "Tech", "region": "Global", "instrument_ccy": "USD", "market_value_usd": 100.0}
    snapshot = {"snapshot_metadata": {"client_id": "CL-X", "as_of_date": "2026-08-26", "period_start": "2026-06-30", "period_end": "2026-08-26", "calculation_version": "1.0.0"}, "client": {"client_id": "CL-X"}, "portfolios": [{"portfolio_id": "PF-X", "client_id": "CL-X"}], "portfolio_summaries": [], "holdings": [holding, dict(holding)], "transactions": [], "planned_cash_needs": [], "commitments": [], "credit_facilities": [], "rm_notes": [], "market_events": [], "data_quality_flags": [], "source_references": []}
    with pytest.raises(ExposureInputError, match="duplicate holding identity"):
        build_exposure_base(snapshot)
    malformed = json.loads(json.dumps(snapshot))
    malformed["holdings"] = [dict(holding, market_value_usd="not-a-number")]
    with pytest.raises(ExposureInputError, match="malformed numeric"):
        build_exposure_base(malformed)
