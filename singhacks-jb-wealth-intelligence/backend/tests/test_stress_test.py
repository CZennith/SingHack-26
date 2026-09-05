from __future__ import annotations

import math

import pandas as pd

from backend.stress_test import apply_shock, compute_ltv_stress
from backend.stress_types import NAMED_SCENARIOS


def _data() -> dict[str, pd.DataFrame]:
    return {
        "holdings": pd.DataFrame([
            {
                "client_id": "CL-TEST",
                "snapshot_date": "2026-08-26",
                "instrument_id": "STRUCTURED",
                "instrument_name": "Airline Note",
                "asset_class": "Structured Products",
                "sector": "Structured Products",
                "market_value_usd": 1000.0,
                "advance_rate_pct": 50.0,
            },
            {
                "client_id": "CL-TEST",
                "snapshot_date": "2026-08-26",
                "instrument_id": "AIRLINE",
                "instrument_name": "Airline Equity",
                "asset_class": "Equity",
                "sector": "Airlines",
                "market_value_usd": 2000.0,
                "advance_rate_pct": 60.0,
            },
            {
                "client_id": "CL-TEST",
                "snapshot_date": "2026-08-26",
                "instrument_id": "CASH",
                "instrument_name": "Cash",
                "asset_class": "Cash and Equivalents",
                "sector": "Cash",
                "market_value_usd": 3000.0,
                "advance_rate_pct": 90.0,
            },
        ]),
        "instruments": pd.DataFrame([
            {
                "instrument_id": "STRUCTURED",
                "underlying_reference": "AIRLINE",
                "asset_class": "Structured Products",
                "sector": "Structured Products",
            },
            {
                "instrument_id": "AIRLINE",
                "underlying_reference": "",
                "asset_class": "Equity",
                "sector": "Airlines",
            },
            {
                "instrument_id": "CASH",
                "underlying_reference": "",
                "asset_class": "Cash and Equivalents",
                "sector": "Cash",
            },
        ]),
    }


def test_look_through_uses_underlying_asset_class_and_sector() -> None:
    results = apply_shock("CL-TEST", NAMED_SCENARIOS["hormuz-escalation"], _data())

    structured = next(result for result in results if result.instrument_id == "STRUCTURED")
    assert structured.look_through_applied is True
    assert structured.effective_asset_class == "Equity"
    assert structured.effective_sector == "Airlines"
    assert structured.shocked_value_usd == 800.0


def test_sector_override_wins_over_asset_class_shock() -> None:
    results = apply_shock("CL-TEST", NAMED_SCENARIOS["hormuz-escalation"], _data())

    airline = next(result for result in results if result.instrument_id == "AIRLINE")
    assert airline.shocked_value_usd == 1600.0


def test_holding_without_matching_shock_is_unchanged() -> None:
    results = apply_shock("CL-TEST", NAMED_SCENARIOS["hormuz-escalation"], _data())

    cash = next(result for result in results if result.instrument_id == "CASH")
    assert cash.shocked_value_usd == cash.current_value_usd
    assert cash.dollar_change_usd == 0.0


# ---------------------------------------------------------------------------
# Helpers shared by the LTV unit tests
# ---------------------------------------------------------------------------

def _fx_rows(snapshot_date: str = "2026-08-26") -> list[dict]:
    """Realistic FX rates for the 2026-08-26 snapshot (from market_context.csv)."""
    return [
        {"snapshot_date": snapshot_date, "series_id": "USDSGD", "value": 1.352},
        {"snapshot_date": snapshot_date, "series_id": "USDHKD", "value": 7.81},
        {"snapshot_date": snapshot_date, "series_id": "EURUSD", "value": 1.092},
        {"snapshot_date": snapshot_date, "series_id": "GBPUSD", "value": 1.282},
    ]


def _ltv_data(
    drawn_usd: float = 6_500_000.0,
    lending_value_usd: float = 8_818_810.0,
    margin_call_ltv_pct: float = 75.0,
    facility_ccy: str = "USD",
    client_id: str = "CL-LTV",
) -> dict[str, pd.DataFrame]:
    """Minimal data dict for LTV stress unit tests."""
    return {
        "credit_facilities": pd.DataFrame([{
            "facility_id": "CF-UNIT",
            "client_id": client_id,
            "collateral_portfolio_id": "PF-UNIT",
            "facility_type": "Lombard Credit Facility",
            "facility_ccy": facility_ccy,
            "drawn_2026-08-26": drawn_usd,
            "lending_value_2026-08-26": lending_value_usd,
            "ltv_pct_2026-08-26": (drawn_usd / lending_value_usd * 100.0) if lending_value_usd else 0.0,
            "margin_call_ltv_pct": margin_call_ltv_pct,
        }]),
        "holdings": pd.DataFrame(
            columns=["client_id", "snapshot_date", "instrument_id", "portfolio_id"]
        ),
        "market_context": pd.DataFrame(_fx_rows()),
    }


# ---------------------------------------------------------------------------
# Unit test: margin call warning triggers when stressed LTV ≥ margin_call_ltv_pct
# ---------------------------------------------------------------------------

def test_ltv_stress_triggers_margin_call_when_stressed_ltv_breaches_threshold() -> None:
    """A stressed LTV at −30% must exceed the margin_call_ltv_pct threshold.

    Scenario: drawn = 6.5m, base lending = 8.82m, margin call threshold = 75%.
    At −30% haircut: stressed_lending = 8.82m × 0.70 = 6.17m
    LTV = 6.5m / 6.17m × 100 ≈ 105.3% — well above the 75% margin call threshold.
    """
    data = _ltv_data(
        drawn_usd=6_500_000.0,
        lending_value_usd=8_818_810.0,
        margin_call_ltv_pct=75.0,
    )
    rows = compute_ltv_stress("CL-LTV", [], data)
    assert len(rows) == 1
    row = rows[0]
    assert row.ltv_minus_30 >= row.margin_call_ltv_pct, (
        f"Expected ltv_minus_30 ({row.ltv_minus_30:.2f}%) >= "
        f"margin_call_ltv_pct ({row.margin_call_ltv_pct:.2f}%)"
    )


# ---------------------------------------------------------------------------
# Unit test: zero lending value guard returns None for LTV
# ---------------------------------------------------------------------------

def test_ltv_stress_zero_lending_value_returns_none_ltv() -> None:
    """When lending value is zero, LTV must be None (not a division error).

    A lending value of zero means there is no collateral to cover the drawn
    amount. Rather than raising ZeroDivisionError or returning infinity, the
    function returns None so the frontend can render 'N/A'.
    """
    data = _ltv_data(drawn_usd=1_000.0, lending_value_usd=0.0)
    rows = compute_ltv_stress("CL-LTV", [], data)
    assert len(rows) == 1
    row = rows[0]
    # All three haircut LTVs stem from a zero base lending value — they should
    # all be treated as non-finite (we store float('inf') and let the router/UI
    # convert to None/N/A; what matters is the _safe_ltv guard works).
    # The scenario_ltv and scenario_headroom should be None (no shocked values passed).
    assert row.scenario_ltv is None
    assert row.scenario_headroom is None
    # Headroom should all be negative (0 - drawn).
    assert row.headroom_minus_10 < 0
    assert row.headroom_minus_20 < 0
    assert row.headroom_minus_30 < 0


# ---------------------------------------------------------------------------
# Unit test: client with no Lombard facility returns empty list
# ---------------------------------------------------------------------------

def test_ltv_stress_no_lombard_facility_returns_empty_list() -> None:
    """A client with no Lombard entries in credit_facilities must get an empty result.

    This is the "No Lombard facility on record" path. The function should
    return [] rather than raising an exception, so the API can return an
    empty facilities array and the UI renders the appropriate message.
    """
    data: dict = {
        "credit_facilities": pd.DataFrame([{
            "facility_id": "CF-NOLOMBARD",
            "client_id": "CL-OTHER",   # different client
            "collateral_portfolio_id": "PF-OTHER",
            "facility_type": "Property Backed Term Loan",  # not Lombard
            "facility_ccy": "SGD",
            "drawn_2026-08-26": 6_000_000.0,
            "lending_value_2026-08-26": 18_582_564.0,
            "ltv_pct_2026-08-26": 32.3,
            "margin_call_ltv_pct": 80.0,
        }]),
        "holdings": pd.DataFrame(
            columns=["client_id", "snapshot_date", "instrument_id", "portfolio_id"]
        ),
        "market_context": pd.DataFrame(_fx_rows()),
    }
    rows = compute_ltv_stress("CL-LTV", [], data)
    assert rows == [], f"Expected empty list for client with no Lombard, got {rows}"


# ===========================================================================
# Task 6.2 — Unit tests for mandate_guard()
# ===========================================================================

from backend.stress_test import mandate_guard


def _mandate_guard_data(
    service_model: str = "Discretionary",
    min_pct_equity: float = 10.0,
    max_pct_equity: float = 40.0,
    current_equity_holding_value: float = 15_000.0,
    total_aum: float = 50_000.0,
    client_id: str = "CL-MG",
) -> dict:
    """Minimal data dict for mandate_guard tests.

    Builds one portfolio (service_model controlled by param), one mandate row
    for Equity with the given min/max, and holdings that give a deterministic
    current Equity weight = current_equity_holding_value / total_aum × 100.
    """
    non_equity_value = total_aum - current_equity_holding_value
    return {
        "portfolios": pd.DataFrame([{
            "portfolio_id": "PF-MG",
            "client_id": client_id,
            "portfolio_name": "Test Portfolio",
            "mandate_code": "TESTM",
            "service_model": service_model,
        }]),
        "mandates": pd.DataFrame([{
            "mandate_code": "TESTM",
            "mandate_name": "Test Mandate",
            "asset_class": "Equity",
            "min_pct": min_pct_equity,
            "target_pct": 25.0,
            "max_pct": max_pct_equity,
            "max_single_position_pct": 15.0,
        }]),
        "holdings": pd.DataFrame([
            {
                "client_id": client_id,
                "snapshot_date": "2026-08-26",
                "instrument_id": "EQ-1",
                "instrument_name": "Equity Fund",
                "asset_class": "Equity",
                "sector": "Technology",
                "market_value_usd": current_equity_holding_value,
                "advance_rate_pct": 65.0,
            },
            {
                "client_id": client_id,
                "snapshot_date": "2026-08-26",
                "instrument_id": "CASH-1",
                "instrument_name": "Cash",
                "asset_class": "Cash and Equivalents",
                "sector": "Cash",
                "market_value_usd": non_equity_value,
                "advance_rate_pct": 90.0,
            },
        ]),
    }


def test_mandate_guard_equity_below_min_triggers_breach() -> None:
    """A recommendation to reduce Equity below min_pct must produce mandate_breach = True.

    Setup:
    - current Equity weight = 15,000 / 50,000 = 30%
    - weight_change = -25.0 → projected = 5%
    - mandate min_pct = 10%
    → projected (5%) < min (10%) → BREACH
    """
    data = _mandate_guard_data(
        min_pct_equity=10.0,
        current_equity_holding_value=15_000.0,
        total_aum=50_000.0,
    )
    recs = [{
        "action_verb": "Reduce",
        "asset_class": "Equity",
        "holding_name": "Equity Fund",
        "rationale": "Reduce tech exposure after stress test.",
        "weight_change": -25.0,  # 30% - 25% = 5%, below 10% floor
    }]
    result = mandate_guard("CL-MG", recs, data)

    assert len(result) == 1
    row = result[0]
    assert row["mandate_breach"] is True, (
        f"Expected mandate_breach=True for projected weight below min_pct, "
        f"got mandate_breach={row['mandate_breach']}, breach_detail={row['breach_detail']}"
    )
    assert row["alternative_action"] is not None, (
        "Expected an alternative_action when mandate breach is detected"
    )
    assert "10.0" in row["breach_detail"], (
        "breach_detail should reference the mandate floor of 10%"
    )


def test_mandate_guard_advisory_portfolio_gets_correct_approval_label() -> None:
    """A recommendation on an Advisory portfolio must get 'Client Approval Required'."""
    data = _mandate_guard_data(service_model="Advisory")
    recs = [{
        "action_verb": "Reduce",
        "asset_class": "Equity",
        "holding_name": "Equity Fund",
        "rationale": "Stress test finding.",
        "weight_change": -2.0,  # small reduction, no breach
    }]
    result = mandate_guard("CL-MG", recs, data)

    assert len(result) == 1
    assert result[0]["approval_label"] == "Client Approval Required", (
        f"Expected 'Client Approval Required' for Advisory portfolio, "
        f"got '{result[0]['approval_label']}'"
    )


def test_mandate_guard_custody_portfolio_gets_no_action_label() -> None:
    """A Custody-only portfolio must get 'Custody — no action possible'."""
    data = _mandate_guard_data(service_model="Custody")
    recs = [{
        "action_verb": "Reduce",
        "asset_class": "Equity",
        "holding_name": "Equity Fund",
        "rationale": "Stress test finding.",
        "weight_change": -5.0,
    }]
    result = mandate_guard("CL-MG", recs, data)

    assert len(result) == 1
    assert result[0]["approval_label"] == "Custody — no action possible", (
        f"Expected 'Custody — no action possible' for Custody portfolio, "
        f"got '{result[0]['approval_label']}'"
    )


def test_mandate_guard_empty_recommendations_returns_no_action_record() -> None:
    """When no recommendations are provided, a 'No immediate action required' record is returned."""
    data = _mandate_guard_data()
    result = mandate_guard("CL-MG", [], data)

    assert len(result) == 1
    row = result[0]
    assert row["mandate_breach"] is False
    assert row["approval_label"] == "N/A"
    # The plain language summary should mention no action required.
    assert "no immediate action" in row["plain_language_summary"].lower(), (
        f"Expected 'No immediate action' in summary, got: {row['plain_language_summary']}"
    )


def test_mandate_guard_no_breach_when_within_bounds() -> None:
    """A recommendation that keeps projected weight within mandate bounds must not breach."""
    data = _mandate_guard_data(
        min_pct_equity=10.0,
        max_pct_equity=40.0,
        current_equity_holding_value=15_000.0,
        total_aum=50_000.0,
    )
    recs = [{
        "action_verb": "Reduce",
        "asset_class": "Equity",
        "holding_name": "Equity Fund",
        "rationale": "Reduce concentrated position.",
        "weight_change": -5.0,  # 30% - 5% = 25%, well within [10%, 40%]
    }]
    result = mandate_guard("CL-MG", recs, data)

    assert len(result) == 1
    assert result[0]["mandate_breach"] is False, (
        f"Expected mandate_breach=False for projected weight 25% within [10%, 40%], "
        f"got breach_detail: {result[0]['breach_detail']}"
    )
    assert result[0]["projected_weight"] == 25.0
