from __future__ import annotations

from src.calculators.exposure_base import build_exposure_base
from src.calculators.exposure_changes import calculate_exposure_changes


def test_direct_exposure_does_not_use_underlying_reference():
    def make(value, as_of):
        return {"snapshot_metadata": {"client_id": "CL-X", "as_of_date": as_of, "period_start": as_of, "period_end": as_of, "calculation_version": "1.0.0"}, "client": {"client_id": "CL-X"}, "portfolios": [{"portfolio_id": "PF-X", "client_id": "CL-X"}], "portfolio_summaries": [], "holdings": [{"snapshot_date": as_of, "portfolio_id": "PF-X", "client_id": "CL-X", "instrument_id": "SP-X", "instrument_name": "Structured", "asset_class": "Structured Products", "sub_asset_class": "Structured Products", "sector": "Financials", "region": "Asia", "instrument_ccy": "USD", "market_value_usd": value, "underlying_reference": "Underlying Basket"}], "transactions": [], "planned_cash_needs": [], "commitments": [], "credit_facilities": [], "rm_notes": [], "market_events": [], "data_quality_flags": [], "source_references": []}
    current = build_exposure_base(make(100, "2026-08-26"))
    previous = build_exposure_base(make(90, "2026-06-30"))
    result = calculate_exposure_changes(current, previous)
    assert current["client_total"]["market_value_usd"] == 100.0
    assert len(current["by_instrument"]) == 1
    assert result["result_metadata"]["input_current_exposure_version"] == "1.0.0"


def test_empty_exposure_bases_still_compare():
    def make(as_of):
        return {"snapshot_metadata": {"client_id": "CL-X", "as_of_date": as_of, "period_start": as_of, "period_end": as_of, "calculation_version": "1.0.0"}, "client": {"client_id": "CL-X"}, "portfolios": [], "portfolio_summaries": [], "holdings": [], "transactions": [], "planned_cash_needs": [], "commitments": [], "credit_facilities": [], "rm_notes": [], "market_events": [], "data_quality_flags": [], "source_references": []}
    result = calculate_exposure_changes(build_exposure_base(make("2026-08-26")), build_exposure_base(make("2026-06-30")))
    assert result["facts"] == []
    assert result["warnings"]
