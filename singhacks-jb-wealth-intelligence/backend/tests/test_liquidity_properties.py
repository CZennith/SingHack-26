"""Property-based tests for the liquidity coverage ratio engine.

Property 6: LCR coverage invariant — COVERED iff Tier1 >= Obligations.
  The status field must be 'COVERED' if and only if tier1_liquid_value_usd
  is >= total_60d_obligations_usd.
  Validates: Requirements 6.3, 6.4, 6.5

Property 7: LCR formula round-trip — LCR >= 1 iff surplus_or_gap >= 0.
  When obligations > 0, LCR = tier1 / obligations, so LCR >= 1 iff
  tier1 >= obligations iff surplus_or_gap = (tier1 - obligations) >= 0.
  Validates: Requirements 6.3, 6.4, 6.5
"""
from __future__ import annotations

import math
from datetime import date

import pandas as pd
import pytest
from hypothesis import given, settings, strategies as st

from backend.liquidity import compute_lcr


# ---------------------------------------------------------------------------
# Minimal data builder for LCR property tests
# ---------------------------------------------------------------------------

def _make_lcr_data(
    tier1_value: float = 0.0,
    obligation_amount: float = 0.0,
    obligation_currency: str = "USD",
    client_id: str = "CL-PROP",
    include_obligation: bool = True,
) -> dict:
    """Build the minimal data dict required by compute_lcr().

    - One Tier-1 holding worth tier1_value USD (or 0 if tier1_value == 0).
    - Optionally one planned cash need for obligation_amount.
    - No commitments.
    - FX rates set to identity (1 USD = 1 USD, etc.) to avoid conversion noise.
    """
    holdings_rows = []
    if tier1_value > 0:
        holdings_rows.append({
            "client_id": client_id,
            "snapshot_date": "2026-08-26",
            "instrument_id": "CASH-T1",
            "instrument_name": "USD Call Deposit",
            "asset_class": "Cash and Equivalents",
            "sector": "Cash",
            "market_value_usd": tier1_value,
            "liquidity_tier": "Daily",
            "unrealised_pnl_base": 0.0,
            "advance_rate_pct": 90.0,
        })

    needs_rows = []
    if include_obligation and obligation_amount > 0:
        needs_rows.append({
            "client_id": client_id,
            "need_id": "CN-PROP",
            "description": "Test need",
            "currency": obligation_currency,
            "amount": obligation_amount,
            "due_from": "2026-09-01",   # within 60 days of 2026-08-26
            "due_to": "2026-09-30",
        })

    fx_rows = [
        {"snapshot_date": "2026-08-26", "series_id": "USDSGD", "value": 1.352},
        {"snapshot_date": "2026-08-26", "series_id": "USDHKD", "value": 7.81},
        {"snapshot_date": "2026-08-26", "series_id": "EURUSD", "value": 1.092},
        {"snapshot_date": "2026-08-26", "series_id": "GBPUSD", "value": 1.282},
    ]

    return {
        "holdings": pd.DataFrame(holdings_rows) if holdings_rows else pd.DataFrame(
            columns=["client_id", "snapshot_date", "instrument_id", "instrument_name",
                     "asset_class", "sector", "market_value_usd", "liquidity_tier",
                     "unrealised_pnl_base", "advance_rate_pct"]
        ),
        "planned_cash_needs": pd.DataFrame(needs_rows) if needs_rows else pd.DataFrame(
            columns=["client_id", "need_id", "description", "currency",
                     "amount", "due_from", "due_to"]
        ),
        "commitments": pd.DataFrame(
            columns=["client_id", "commitment_id", "currency", "uncalled", "expected_call_window"]
        ),
        "market_context": pd.DataFrame(fx_rows),
        "clients": pd.DataFrame([{
            "client_id": client_id,
            "life_stage": "Wealth accumulation",  # does not match life-event keywords
        }]),
    }


# ---------------------------------------------------------------------------
# Property 6: LCR coverage invariant
# ---------------------------------------------------------------------------

@given(
    tier1=st.floats(min_value=0.0, max_value=50_000_000.0, allow_nan=False, allow_infinity=False),
    obligation=st.floats(min_value=0.01, max_value=50_000_000.0, allow_nan=False, allow_infinity=False),
)
def test_lcr_covered_iff_tier1_gte_obligations(tier1: float, obligation: float) -> None:
    """Status must be COVERED iff tier1 >= obligation (when obligations > 0).

    This validates that the COVERED/SHORTFALL split is correctly derived from
    the LCR value and not from any other condition.
    """
    data = _make_lcr_data(tier1_value=tier1, obligation_amount=obligation)
    result = compute_lcr("CL-PROP", data, as_of=date(2026, 8, 26))

    if tier1 >= obligation:
        assert result.status == "COVERED", (
            f"Expected COVERED when tier1={tier1:.2f} >= obligation={obligation:.2f}, "
            f"got {result.status}"
        )
    else:
        assert result.status == "SHORTFALL", (
            f"Expected SHORTFALL when tier1={tier1:.2f} < obligation={obligation:.2f}, "
            f"got {result.status}"
        )


# ---------------------------------------------------------------------------
# Property 7: LCR formula round-trip
# ---------------------------------------------------------------------------

@given(
    tier1=st.floats(min_value=0.01, max_value=50_000_000.0, allow_nan=False, allow_infinity=False),
    obligation=st.floats(min_value=0.01, max_value=50_000_000.0, allow_nan=False, allow_infinity=False),
)
def test_lcr_gte_one_iff_surplus_gte_zero(tier1: float, obligation: float) -> None:
    """LCR >= 1 iff surplus_or_gap >= 0 (when obligations > 0).

    The formula LCR = tier1 / obligation ensures:
      LCR >= 1 ↔ tier1 >= obligation ↔ tier1 - obligation >= 0 = surplus_or_gap

    Any rounding or sign error in the implementation would break this invariant.
    """
    data = _make_lcr_data(tier1_value=tier1, obligation_amount=obligation)
    result = compute_lcr("CL-PROP", data, as_of=date(2026, 8, 26))

    lcr = result.lcr
    surplus = result.surplus_or_gap_usd

    assert lcr is not None, "LCR must be non-None when obligations > 0"

    if lcr >= 1.0:
        assert surplus >= -0.01, (
            f"Expected surplus >= 0 when LCR={lcr:.4f} >= 1, got surplus={surplus:.2f}"
        )
    else:
        assert surplus <= 0.01, (
            f"Expected surplus <= 0 when LCR={lcr:.4f} < 1, got surplus={surplus:.2f}"
        )
