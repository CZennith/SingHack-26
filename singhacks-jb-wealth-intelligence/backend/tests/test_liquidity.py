"""Unit tests for compute_lcr() and the to_usd() FX helper.

Tests cover:
1. FX conversions for SGD, EUR, HKD, GBP using 2026-08-26 market_context rates.
2. Zero-obligations case: LCR = None, status = COVERED, note = "No obligations in window".
3. Sell-to-cover ordering: holding with larger unrealised loss ranks first.
4. Life-event flag detection: business-sale client with large upcoming need triggers flag.
5. Life-stage keyword exclusion: non-matching life_stage produces no flag.
"""
from __future__ import annotations

import math
from datetime import date

import pandas as pd
import pytest

from backend.stress_test import to_usd
from backend.liquidity import compute_lcr, life_event_flags


# ---------------------------------------------------------------------------
# Realistic FX rates from market_context.csv for 2026-08-26
# ---------------------------------------------------------------------------
RATES = {
    "USDSGD": 1.352,
    "USDHKD": 7.81,
    "EURUSD": 1.092,
    "GBPUSD": 1.282,
}


# ---------------------------------------------------------------------------
# Test 1: FX conversions use correct convention per currency pair
# ---------------------------------------------------------------------------

def test_to_usd_sgd_divides_by_usdsgd_rate() -> None:
    """SGD → USD: divide by USDSGD (= 1.352 SGD per 1 USD)."""
    result = to_usd(1_352_000.0, "SGD", RATES)
    assert result == pytest.approx(1_352_000.0 / 1.352, rel=1e-6)


def test_to_usd_hkd_divides_by_usdhkd_rate() -> None:
    """HKD → USD: divide by USDHKD (= 7.81 HKD per 1 USD)."""
    result = to_usd(7_810_000.0, "HKD", RATES)
    assert result == pytest.approx(7_810_000.0 / 7.81, rel=1e-6)


def test_to_usd_eur_multiplies_by_eurusd_rate() -> None:
    """EUR → USD: multiply by EURUSD (= 1.092 USD per 1 EUR)."""
    result = to_usd(1_000_000.0, "EUR", RATES)
    assert result == pytest.approx(1_000_000.0 * 1.092, rel=1e-6)


def test_to_usd_gbp_multiplies_by_gbpusd_rate() -> None:
    """GBP → USD: multiply by GBPUSD (= 1.282 USD per 1 GBP)."""
    result = to_usd(500_000.0, "GBP", RATES)
    assert result == pytest.approx(500_000.0 * 1.282, rel=1e-6)


def test_to_usd_identity_for_usd() -> None:
    """USD amounts must be returned unchanged."""
    assert to_usd(1_234_567.89, "USD", RATES) == pytest.approx(1_234_567.89)


# ---------------------------------------------------------------------------
# Shared fixture builders
# ---------------------------------------------------------------------------

def _fx_rows() -> list[dict]:
    return [
        {"snapshot_date": "2026-08-26", "series_id": k, "value": v}
        for k, v in RATES.items()
    ]


def _make_data(
    tier1_holdings: list[dict] | None = None,
    needs: list[dict] | None = None,
    life_stage: str = "Wealth accumulation",
    client_id: str = "CL-TEST",
) -> dict:
    holdings_rows = tier1_holdings or []
    needs_rows = needs or []
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
        "market_context": pd.DataFrame(_fx_rows()),
        "clients": pd.DataFrame([{
            "client_id": client_id,
            "life_stage": life_stage,
        }]),
    }


def _holding(
    instrument_id: str,
    name: str,
    value_usd: float,
    pnl: float,
    client_id: str = "CL-TEST",
) -> dict:
    return {
        "client_id": client_id,
        "snapshot_date": "2026-08-26",
        "instrument_id": instrument_id,
        "instrument_name": name,
        "asset_class": "Equity",
        "sector": "Diversified",
        "market_value_usd": value_usd,
        "liquidity_tier": "Daily",
        "unrealised_pnl_base": pnl,
        "advance_rate_pct": 65.0,
    }


# ---------------------------------------------------------------------------
# Test 2: Zero obligations → LCR = None, status COVERED
# ---------------------------------------------------------------------------

def test_zero_obligations_returns_none_lcr_and_covered_status() -> None:
    """When there are no 60-day obligations, LCR must be None and status COVERED.

    The design specifies this edge case explicitly: "If Total_60_Day_Obligations
    == 0: LCR = +∞, status = COVERED". We represent +∞ as None.
    """
    data = _make_data(
        tier1_holdings=[_holding("CASH", "USD Cash", 5_000_000.0, 0.0)],
        needs=[],  # no needs at all
    )
    result = compute_lcr("CL-TEST", data, as_of=date(2026, 8, 26))

    assert result.lcr is None, (
        f"Expected LCR = None when no obligations, got {result.lcr}"
    )
    assert result.status == "COVERED", (
        f"Expected status COVERED when no obligations, got {result.status}"
    )
    assert result.total_60d_obligations_usd == 0.0


# ---------------------------------------------------------------------------
# Test 3: Sell-to-cover ordering — largest loss ranks first
# ---------------------------------------------------------------------------

def test_sell_to_cover_orders_by_largest_loss_first() -> None:
    """Holdings must be ranked by unrealised_pnl_base ascending (loss first).

    We set up three Tier-1 holdings with distinct P&L values:
    - BOND:  P&L = −80,000 (largest loss → should rank 1)
    - STOCK: P&L = −20,000 (small loss → should rank 2)
    - GOLD:  P&L = +50,000 (gain → should rank 3)

    Tax-efficiency reasoning: selling the loss first harvests a tax benefit
    that partially offsets the forced liquidation cost.
    """
    data = _make_data(
        tier1_holdings=[
            _holding("STOCK", "Equity Fund", 2_000_000.0, -20_000.0),
            _holding("BOND", "Bond Fund", 3_000_000.0, -80_000.0),
            _holding("GOLD", "Gold ETF", 1_500_000.0, 50_000.0),
        ],
        needs=[{
            "client_id": "CL-TEST",
            "need_id": "CN-X",
            "description": "Test need",
            "currency": "USD",
            "amount": 1_000_000.0,
            "due_from": "2026-09-01",
            "due_to": "2026-09-30",
        }],
    )
    result = compute_lcr("CL-TEST", data, as_of=date(2026, 8, 26))

    sell_list = result.sell_to_cover
    assert len(sell_list) >= 2

    # First ranked item must have the most negative P&L.
    assert sell_list[0]["instrument_name"] == "Bond Fund", (
        f"Expected 'Bond Fund' (loss = −80k) at rank 1, got {sell_list[0]['instrument_name']}"
    )
    assert sell_list[1]["instrument_name"] == "Equity Fund", (
        f"Expected 'Equity Fund' (loss = −20k) at rank 2, got {sell_list[1]['instrument_name']}"
    )
    # Gain holder should be last.
    assert sell_list[-1]["instrument_name"] == "Gold ETF", (
        f"Expected 'Gold ETF' (gain) last, got {sell_list[-1]['instrument_name']}"
    )

    # All items must have estimated_settle_days = 2 (T+2 convention).
    for item in sell_list:
        assert item["estimated_settle_days"] == 2


# ---------------------------------------------------------------------------
# Test 4: Life-event flag triggers for a business-sale client
# ---------------------------------------------------------------------------

def test_life_event_flag_triggers_for_business_sale_client() -> None:
    """A client with 'business sale' in life_stage and a large upcoming need
    within 18 months should generate a life-event flag.

    Setup:
    - life_stage = "Pre-liquidity event"   (contains "pre-liquidity event" keyword)
    - Tier-1 = USD 5,000,000
    - Upcoming need in 12 months = USD 3,000,000 (= 60% of Tier-1, well above 20%)
    - We don't set LCR explicitly here; life_event_flags() will still flag
      because the need exceeds 20% of Tier-1 AND the life_stage matches.
    """
    flags = life_event_flags(
        client_id="CL-TEST",
        tier1_value=5_000_000.0,
        lcr=0.8,  # below 1.2 threshold
        data=_make_data(
            life_stage="Pre-liquidity event",
            needs=[{
                "client_id": "CL-TEST",
                "need_id": "CN-FLAG",
                "description": "Business sale related payment",
                "currency": "USD",
                "amount": 3_000_000.0,
                "due_from": "2027-02-01",   # within 18 months of 2026-08-26
                "due_to": "2027-03-31",
            }],
        ),
        as_of=date(2026, 8, 26),
    )

    assert len(flags) >= 1, "Expected at least one life-event flag for a pre-liquidity client"
    flag = flags[0]
    assert flag["amount_usd"] == pytest.approx(3_000_000.0)
    assert "pre-liquidity" in flag["life_stage_note"].lower() or "pre-liquidity" in flag["life_stage_note"].lower()


# ---------------------------------------------------------------------------
# Test 5: Life-stage keyword exclusion — no flag for unmatched life_stage
# ---------------------------------------------------------------------------

def test_life_event_flag_not_raised_for_non_matching_life_stage() -> None:
    """When life_stage does not match any keyword, no flag must be emitted.

    Even with a large upcoming need, a client with 'Wealth accumulation' as
    their life stage should not trigger a life-event flag.
    """
    flags = life_event_flags(
        client_id="CL-TEST",
        tier1_value=5_000_000.0,
        lcr=0.8,
        data=_make_data(
            life_stage="Wealth accumulation",  # does NOT match any keyword
            needs=[{
                "client_id": "CL-TEST",
                "need_id": "CN-FLAG",
                "description": "Property purchase",
                "currency": "USD",
                "amount": 4_000_000.0,
                "due_from": "2027-01-01",
                "due_to": "2027-06-30",
            }],
        ),
        as_of=date(2026, 8, 26),
    )
    assert flags == [], (
        f"Expected no flags for non-matching life_stage 'Wealth accumulation', got {flags}"
    )
