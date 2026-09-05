from __future__ import annotations

import json
from copy import deepcopy

import pytest

from src.calculators.exposure_base import build_exposure_base
from src.calculators.exposure_changes import ExposureChangeError, calculate_exposure_changes
from src.client_snapshot import validate_snapshot
from src.contracts.validation import validate_result


def snapshot(as_of: str, holdings: list[dict]) -> dict:
    return {
        "snapshot_metadata": {"client_id": "CL-X", "as_of_date": as_of, "period_start": as_of, "period_end": as_of, "calculation_version": "1.0.0"},
        "client": {"client_id": "CL-X"}, "portfolios": [{"portfolio_id": "PF-X", "client_id": "CL-X"}], "portfolio_summaries": [], "holdings": holdings,
        "transactions": [], "planned_cash_needs": [], "commitments": [], "credit_facilities": [], "rm_notes": [], "market_events": [], "data_quality_flags": [], "source_references": [],
    }


def holding(instrument_id: str, value: float, **kwargs) -> dict:
    return {"snapshot_date": kwargs.pop("snapshot_date", "2026-08-26"), "portfolio_id": "PF-X", "client_id": "CL-X", "instrument_id": instrument_id, "instrument_name": instrument_id, "asset_class": "Equity", "sub_asset_class": "Equity", "sector": "Technology", "region": "Global", "instrument_ccy": "USD", "market_value_usd": value, **kwargs}


def changes(current_holdings, previous_holdings):
    current = build_exposure_base(snapshot("2026-08-26", current_holdings))
    previous = build_exposure_base(snapshot("2026-06-30", previous_holdings))
    return calculate_exposure_changes(current, previous)


def instrument_fact(result, instrument_id):
    return next(item for item in result["facts"] if item["scope"]["dimension"] == "instrument" and item["scope"]["instrument_id"] == instrument_id)


def test_added_exited_changed_unchanged_and_zero_percentage_change():
    result = changes([holding("ADDED", 100), holding("CHANGED", 200), holding("SAME", 50)], [holding("EXITED", 100, snapshot_date="2026-06-30"), holding("CHANGED", 150, snapshot_date="2026-06-30"), holding("SAME", 50, snapshot_date="2026-06-30")])
    assert instrument_fact(result, "ADDED")["status"] == "added"
    assert instrument_fact(result, "EXITED")["status"] == "exited"
    assert instrument_fact(result, "CHANGED")["status"] == "changed"
    assert instrument_fact(result, "SAME")["status"] == "unchanged"
    assert instrument_fact(result, "ADDED")["percentage_change"] is None
    assert all(item["evidence_ids"] for item in result["facts"])
    validate_result(result)


def test_structured_reference_is_not_double_counted():
    current = [holding("STRUCTURED", 100, underlying_reference="Basket A")]
    base = build_exposure_base(snapshot("2026-08-26", current))
    assert base["client_total"]["market_value_usd"] == 100.0
    assert len(base["by_instrument"]) == 1
    assert base["by_instrument"][0]["underlying_reference"] == "Basket A"
    assert base["exposure_metadata"]["look_through_included"] is False


def test_changes_are_deterministic_and_json_serializable():
    current = [holding("B", 200), holding("A", 100)]
    previous = [holding("A", 100, snapshot_date="2026-06-30"), holding("B", 100, snapshot_date="2026-06-30")]
    first = changes(current, previous)
    second = changes(current, previous)
    assert first == second
    assert json.dumps(first, allow_nan=False) == json.dumps(second, allow_nan=False)


def test_mismatched_clients_and_same_dates_reject():
    current = build_exposure_base(snapshot("2026-08-26", [holding("A", 1)]))
    previous = deepcopy(current)
    with pytest.raises(ExposureChangeError, match="different"):
        calculate_exposure_changes(current, previous)
    previous["exposure_metadata"]["as_of_date"] = "2026-06-30"
    previous["exposure_metadata"]["client_id"] = "CL-Y"
    with pytest.raises(ExposureChangeError, match="same client_id"):
        calculate_exposure_changes(current, previous)
