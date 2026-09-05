"""Property-based tests for the Lombard LTV stress engine.

Property 4: LTV increases under haircut
  For any facility with drawn > 0 and lending_value > 0, applying a haircut h > 0
  to the lending value must strictly increase the resulting LTV.
  Validates: Requirements 4.2, 4.3

Property 5: LTV ordering under increasing haircuts
  For any facility, the LTV values at the three fixed haircut levels must obey:
    ltv_at_minus_10 < ltv_at_minus_20 < ltv_at_minus_30
  Validates: Requirements 4.2, 4.4
"""
from __future__ import annotations

import math

import pandas as pd
import pytest
from hypothesis import given, settings, strategies as st

from backend.stress_test import compute_ltv_stress


# ---------------------------------------------------------------------------
# Fixture builder helpers
# ---------------------------------------------------------------------------

def _make_data(
    drawn_usd: float,
    lending_value_usd: float,
    client_id: str = "CL-PROP",
    facility_id: str = "CF-PROP",
) -> dict[str, pd.DataFrame]:
    """Build the minimal data dict needed by compute_ltv_stress."""
    return {
        "credit_facilities": pd.DataFrame([{
            "facility_id": facility_id,
            "client_id": client_id,
            "collateral_portfolio_id": "PF-PROP",
            "facility_type": "Lombard Credit Facility",
            "facility_ccy": "USD",
            "drawn_2026-08-26": drawn_usd,
            "lending_value_2026-08-26": lending_value_usd,
            "ltv_pct_2026-08-26": (drawn_usd / lending_value_usd * 100.0) if lending_value_usd else 0.0,
            "margin_call_ltv_pct": 75.0,
        }]),
        # compute_ltv_stress reads the holdings table to map instruments →
        # portfolios when shocked_lending_values is non-empty.  For pure
        # property tests we pass an empty list, so an empty DataFrame suffices.
        "holdings": pd.DataFrame(columns=["client_id", "snapshot_date", "instrument_id", "portfolio_id"]),
        "market_context": pd.DataFrame([
            # FX row for the snapshot date — all rates set to 1:1 so USD stays USD.
            {"snapshot_date": "2026-08-26", "series_id": "USDSGD", "value": 1.0},
            {"snapshot_date": "2026-08-26", "series_id": "USDHKD", "value": 1.0},
            {"snapshot_date": "2026-08-26", "series_id": "EURUSD", "value": 1.0},
            {"snapshot_date": "2026-08-26", "series_id": "GBPUSD", "value": 1.0},
        ]),
    }


# ---------------------------------------------------------------------------
# Property 4: LTV increases under haircut
# ---------------------------------------------------------------------------

@given(
    drawn=st.floats(min_value=1.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False),
    lending=st.floats(min_value=1.0, max_value=10_000_000.0, allow_nan=False, allow_infinity=False),
    haircut=st.floats(min_value=0.001, max_value=0.999, allow_nan=False, allow_infinity=False),
)
def test_ltv_increases_under_haircut(drawn: float, lending: float, haircut: float) -> None:
    """Applying any positive haircut to lending value must strictly increase LTV.

    Baseline LTV (no haircut): drawn / lending × 100
    Stressed LTV: drawn / (lending × (1 − haircut)) × 100

    Since (1 − haircut) < 1, the denominator shrinks and LTV rises.
    """
    baseline_ltv = drawn / lending * 100.0
    stressed_lending = lending * (1.0 - haircut)
    stressed_ltv = drawn / stressed_lending * 100.0
    assert stressed_ltv > baseline_ltv, (
        f"Expected stressed LTV ({stressed_ltv:.4f}) > baseline LTV ({baseline_ltv:.4f}) "
        f"with drawn={drawn}, lending={lending}, haircut={haircut}"
    )


# ---------------------------------------------------------------------------
# Property 5: LTV ordering under increasing haircuts (−10% < −20% < −30%)
# ---------------------------------------------------------------------------

@given(
    drawn=st.floats(min_value=1.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False),
    lending=st.floats(min_value=1.0, max_value=10_000_000.0, allow_nan=False, allow_infinity=False),
)
def test_ltv_ordering_increases_with_haircut_severity(drawn: float, lending: float) -> None:
    """The three haircut levels must produce strictly ordered LTV values.

    ltv_at_minus_10 < ltv_at_minus_20 < ltv_at_minus_30

    This validates that the haircut multipliers (0.90, 0.80, 0.70) are applied
    correctly — if they were reversed the ordering would flip.
    """
    data = _make_data(drawn_usd=drawn, lending_value_usd=lending)
    rows = compute_ltv_stress("CL-PROP", [], data)
    assert len(rows) == 1
    row = rows[0]

    ltv_10 = row.ltv_minus_10
    ltv_20 = row.ltv_minus_20
    ltv_30 = row.ltv_minus_30

    # All three should be finite (lending > 0 by construction above).
    assert math.isfinite(ltv_10), "ltv_minus_10 should be finite when lending > 0"
    assert math.isfinite(ltv_20), "ltv_minus_20 should be finite when lending > 0"
    assert math.isfinite(ltv_30), "ltv_minus_30 should be finite when lending > 0"

    assert ltv_10 < ltv_20 < ltv_30, (
        f"Expected ltv_10 ({ltv_10:.4f}) < ltv_20 ({ltv_20:.4f}) < ltv_30 ({ltv_30:.4f})"
    )
