"""Property-based tests for the look-through concentration analyzer.

Property 8: Look-through is a substitution, not addition — total AUM unchanged.
  The sum of all post-look-through market values must equal the sum of all
  pre-look-through market values (which equals total portfolio AUM).
  Validates: Requirements 5.2, 5.3

Property 9: Concentration status classification is total and exclusive.
  Every ConcentrationRow must have a status in the set
  {BREACH, ELEVATED, OK, NO_LIMIT}, and that status must be logically
  consistent with its post_look_through_pct and mandate_limit_pct values.
  Validates: Requirements 5.6, 5.7
"""
from __future__ import annotations

import math

import pandas as pd
import pytest
from hypothesis import given, settings, strategies as st

from backend.look_through import concentration_result


# ---------------------------------------------------------------------------
# Data builder
# ---------------------------------------------------------------------------

VALID_STATUSES = frozenset({"BREACH", "ELEVATED", "OK", "NO_LIMIT"})


def _build_data(
    holdings: list[dict],
    instruments: list[dict],
    mandate_limit_pct: float | None = None,
    client_id: str = "CL-PROP",
) -> dict:
    """Build the minimal data dict for concentration_result()."""
    portfolios_rows = [{
        "portfolio_id": "PF-PROP",
        "client_id": client_id,
        "mandate_code": "TEST",
        "service_model": "Discretionary",
    }]
    mandates_rows: list[dict] = []
    if mandate_limit_pct is not None:
        # Add a mandate row for every asset class referenced in instruments,
        # so all exposures get the same cap.
        asset_classes = {inst.get("asset_class", "Equity") for inst in instruments}
        for ac in asset_classes:
            mandates_rows.append({
                "mandate_code": "TEST",
                "mandate_name": "Test Mandate",
                "asset_class": ac,
                "min_pct": 0.0,
                "target_pct": 50.0,
                "max_pct": 100.0,
                "max_single_position_pct": mandate_limit_pct,
            })

    return {
        "holdings": pd.DataFrame(holdings),
        "instruments": pd.DataFrame(instruments),
        "portfolios": pd.DataFrame(portfolios_rows),
        "mandates": pd.DataFrame(mandates_rows) if mandates_rows else pd.DataFrame(
            columns=["mandate_code", "mandate_name", "asset_class",
                     "min_pct", "target_pct", "max_pct", "max_single_position_pct"]
        ),
    }


def _holding(
    instrument_id: str,
    asset_class: str,
    sector: str,
    market_value: float,
    client_id: str = "CL-PROP",
) -> dict:
    return {
        "client_id": client_id,
        "snapshot_date": "2026-08-26",
        "portfolio_id": "PF-PROP",
        "instrument_id": instrument_id,
        "instrument_name": instrument_id,
        "asset_class": asset_class,
        "sector": sector,
        "market_value_usd": market_value,
    }


def _instrument(
    instrument_id: str,
    asset_class: str,
    sector: str,
    underlying_reference: str = "",
    concentration_limit_applies: str = "N",
) -> dict:
    return {
        "instrument_id": instrument_id,
        "asset_class": asset_class,
        "sector": sector,
        "underlying_reference": underlying_reference,
        "concentration_limit_applies": concentration_limit_applies,
    }


# ---------------------------------------------------------------------------
# Property 8: Look-through preserves total AUM
# ---------------------------------------------------------------------------

@given(
    eq_val=st.floats(min_value=0.01, max_value=5_000_000.0, allow_nan=False, allow_infinity=False),
    sp_val=st.floats(min_value=0.01, max_value=5_000_000.0, allow_nan=False, allow_infinity=False),
    cash_val=st.floats(min_value=0.01, max_value=5_000_000.0, allow_nan=False, allow_infinity=False),
)
def test_look_through_preserves_total_aum(
    eq_val: float, sp_val: float, cash_val: float
) -> None:
    """Total AUM before and after look-through must be identical.

    We create a portfolio with:
    - One Equity holding (STOCK)
    - One Structured Product (SP) that references STOCK via look-through
    - One Cash holding (CASH) with no look-through

    After look-through, SP's value moves to the Equity/Stock bucket.
    But the SUM of all post-look-through bucket values must still equal
    eq_val + sp_val + cash_val.
    """
    data = _build_data(
        holdings=[
            _holding("STOCK", "Equity", "Technology", eq_val),
            _holding("SP", "Structured Products", "Multi", sp_val),
            _holding("CASH", "Cash and Equivalents", "Cash", cash_val),
        ],
        instruments=[
            _instrument("STOCK", "Equity", "Technology"),
            _instrument("SP", "Structured Products", "Multi",
                        underlying_reference="STOCK"),
            _instrument("CASH", "Cash and Equivalents", "Cash"),
        ],
    )
    result = concentration_result("CL-PROP", data)
    rows = result["concentrations"]

    # Sum of all post-look-through values must equal total AUM.
    total_post = sum(row.post_look_through_value_usd for row in rows)
    expected_total = eq_val + sp_val + cash_val

    assert math.isclose(total_post, expected_total, rel_tol=1e-9), (
        f"Post-look-through total {total_post} ≠ expected AUM {expected_total}"
    )

    # Also verify via result['total_aum_usd'].
    assert math.isclose(result["total_aum_usd"], expected_total, rel_tol=1e-4, abs_tol=0.01)


@given(
    n_instruments=st.integers(min_value=1, max_value=8),
    values=st.lists(
        st.floats(min_value=0.01, max_value=1_000_000.0, allow_nan=False, allow_infinity=False),
        min_size=1, max_size=8,
    ),
)
def test_look_through_preserves_aum_no_structured_products(
    n_instruments: int, values: list[float]
) -> None:
    """When there are no structured products, total AUM is trivially preserved."""
    asset_classes = ["Equity", "Fixed Income", "Cash and Equivalents",
                     "Alternatives", "Commodities"]
    n = min(n_instruments, len(values))
    holdings = []
    instruments_list = []
    for i in range(n):
        iid = f"INST-{i}"
        ac = asset_classes[i % len(asset_classes)]
        holdings.append(_holding(iid, ac, "Sector", values[i]))
        instruments_list.append(_instrument(iid, ac, "Sector"))

    data = _build_data(holdings=holdings, instruments=instruments_list)
    result = concentration_result("CL-PROP", data)
    rows = result["concentrations"]

    total_post = sum(row.post_look_through_value_usd for row in rows)
    expected = sum(values[:n])
    assert math.isclose(total_post, expected, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# Property 9: Concentration status classification is total and exclusive
# ---------------------------------------------------------------------------

@given(
    market_value=st.floats(min_value=1.0, max_value=10_000_000.0, allow_nan=False, allow_infinity=False),
    mandate_limit=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False),
)
def test_status_is_one_of_valid_values(market_value: float, mandate_limit: float) -> None:
    """Every row must have a status in {BREACH, ELEVATED, OK, NO_LIMIT}.

    We use a single-instrument portfolio so there's exactly one row, and we
    verify the status is valid and consistent with the pct vs limit.
    """
    # Single instrument with concentration_limit_applies = "Y" so it gets a mandate check.
    data = _build_data(
        holdings=[_holding("INST", "Equity", "Technology", market_value)],
        instruments=[_instrument("INST", "Equity", "Technology",
                                 concentration_limit_applies="Y")],
        mandate_limit_pct=mandate_limit,
    )
    result = concentration_result("CL-PROP", data)
    rows = result["concentrations"]
    assert len(rows) == 1

    row = rows[0]
    assert row.status in VALID_STATUSES, (
        f"Unexpected status '{row.status}' — must be one of {VALID_STATUSES}"
    )

    # Logical consistency: status must match the pct vs limit relationship.
    pct = row.post_look_through_pct
    limit = row.mandate_limit_pct
    assert limit is not None, "Expected a mandate limit to be set"

    if row.status == "BREACH":
        assert pct >= limit, f"BREACH but pct {pct} < limit {limit}"
    elif row.status == "ELEVATED":
        assert pct >= limit * 0.80, f"ELEVATED but pct {pct} < 80% of limit {limit}"
        assert pct < limit, f"ELEVATED but pct {pct} >= limit {limit}"
    elif row.status == "OK":
        assert pct < limit * 0.80, f"OK but pct {pct} >= 80% of limit {limit}"
    # NO_LIMIT is not reachable here because we supplied a mandate_limit_pct.


@given(
    market_value=st.floats(min_value=1.0, max_value=10_000_000.0, allow_nan=False, allow_infinity=False),
)
def test_status_is_no_limit_when_no_mandate_applies(market_value: float) -> None:
    """When concentration_limit_applies = 'N', status must always be NO_LIMIT."""
    data = _build_data(
        holdings=[_holding("INST", "Equity", "Technology", market_value)],
        instruments=[_instrument("INST", "Equity", "Technology",
                                 concentration_limit_applies="N")],
        mandate_limit_pct=15.0,  # Has a mandate, but instrument opts out.
    )
    result = concentration_result("CL-PROP", data)
    rows = result["concentrations"]
    assert len(rows) == 1
    assert rows[0].status == "NO_LIMIT", (
        f"Expected NO_LIMIT when concentration_limit_applies='N', got {rows[0].status}"
    )
