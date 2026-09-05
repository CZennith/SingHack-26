"""Unit tests for the look-through concentration analyzer.

Tests verify:
1. A structured product's market value moves from its stated bucket to the
   underlying's bucket after look-through.
2. ELEVATED badge fires when post_pct is between 80% and 100% of mandate limit.
3. Hidden concentration callout fires when gap > 5 pp of AUM.
"""
from __future__ import annotations

import pandas as pd
import pytest

from backend.look_through import concentration_result, concentration_table


# ---------------------------------------------------------------------------
# Shared fixture builder (mirrors test_lookthrough_properties.py pattern)
# ---------------------------------------------------------------------------

def _holding(
    instrument_id: str,
    asset_class: str,
    sector: str,
    market_value: float,
    client_id: str = "CL-TEST",
) -> dict:
    return {
        "client_id": client_id,
        "snapshot_date": "2026-08-26",
        "portfolio_id": "PF-TEST",
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


def _build_data(
    holdings: list[dict],
    instruments: list[dict],
    mandate_limit_pct: float | None = None,
    asset_class_for_limit: str = "Equity",
    client_id: str = "CL-TEST",
) -> dict:
    portfolios = pd.DataFrame([{
        "portfolio_id": "PF-TEST",
        "client_id": client_id,
        "mandate_code": "TESTM",
        "service_model": "Discretionary",
    }])
    if mandate_limit_pct is not None:
        mandates = pd.DataFrame([{
            "mandate_code": "TESTM",
            "mandate_name": "Test",
            "asset_class": asset_class_for_limit,
            "min_pct": 0.0,
            "target_pct": 50.0,
            "max_pct": 100.0,
            "max_single_position_pct": mandate_limit_pct,
        }])
    else:
        mandates = pd.DataFrame(
            columns=["mandate_code", "mandate_name", "asset_class",
                     "min_pct", "target_pct", "max_pct", "max_single_position_pct"]
        )
    return {
        "holdings": pd.DataFrame(holdings),
        "instruments": pd.DataFrame(instruments),
        "portfolios": portfolios,
        "mandates": mandates,
    }


# ---------------------------------------------------------------------------
# Test 1: Structured product value moves to underlying's bucket after look-through
# ---------------------------------------------------------------------------

def test_structured_product_value_moves_to_underlying_bucket() -> None:
    """The market value of a structured product should appear in the underlying's
    (asset_class, sector) bucket after look-through, not in 'Structured Products'.

    Setup:
    - 1 Equity holding (STOCK-A) in Equity / Information Technology: USD 1,000
    - 1 Structured Product (SP-A) with underlying_reference = STOCK-A: USD 2,000
    - 1 Cash holding: USD 500

    Pre-look-through:
      Equity / IT       = 1,000
      Structured / ...  = 2,000
      Cash              = 500

    Post-look-through:
      Equity / IT       = 3,000  (1,000 from STOCK-A + 2,000 migrated from SP-A)
      Structured / ...  = 0      (SP-A has been substituted)
      Cash              = 500
    """
    data = _build_data(
        holdings=[
            _holding("STOCK-A", "Equity", "Information Technology", 1_000.0),
            _holding("SP-A", "Structured Products", "Multi", 2_000.0),
            _holding("CASH", "Cash and Equivalents", "Cash", 500.0),
        ],
        instruments=[
            _instrument("STOCK-A", "Equity", "Information Technology"),
            _instrument("SP-A", "Structured Products", "Multi",
                        underlying_reference="STOCK-A"),
            _instrument("CASH", "Cash and Equivalents", "Cash"),
        ],
    )
    rows = concentration_table("CL-TEST", data)

    # Build lookup by (asset_class, sector) for easy assertions.
    by_key = {(r.asset_class, r.sector): r for r in rows}

    # Equity / IT bucket: must contain 3,000 post-look-through.
    eq_it = by_key.get(("Equity", "Information Technology"))
    assert eq_it is not None, "Expected an Equity/IT row in results"
    assert eq_it.post_look_through_value_usd == pytest.approx(3_000.0), (
        f"Expected post-look-through Equity/IT = 3000, got {eq_it.post_look_through_value_usd}"
    )
    assert eq_it.pre_look_through_value_usd == pytest.approx(1_000.0), (
        "Pre-look-through Equity/IT should be only the direct equity holding"
    )
    assert eq_it.post_look_through_value_usd > eq_it.pre_look_through_value_usd, (
        "Post-look-through Equity/IT must exceed pre-look-through (SP value migrated in)"
    )

    # Structured Products bucket: must have 0 post-look-through value (all migrated).
    sp_row = by_key.get(("Structured Products", "Multi"))
    if sp_row is not None:
        assert sp_row.post_look_through_value_usd == pytest.approx(0.0), (
            "Structured Products bucket should be empty post-look-through"
        )


# ---------------------------------------------------------------------------
# Test 2: ELEVATED badge fires when 80% ≤ post_pct < 100% of mandate limit
# ---------------------------------------------------------------------------

def test_elevated_badge_when_post_pct_between_80_and_100_percent_of_limit() -> None:
    """Status = ELEVATED when post_pct is ≥ 80% but < 100% of mandate limit.

    Setup: total AUM = 100,000. Mandate limit = 20% of AUM (20,000).
    We put a single equity holding at 18,000 = 18% of AUM.
    18% >= 80% of 20% (= 16%) → ELEVATED.
    18% < 20% → not BREACH.
    """
    total_aum = 100_000.0
    # Equity holding at 18% of AUM — sits in the ELEVATED band (80–100% of 20% limit).
    equity_val = 18_000.0
    cash_val = total_aum - equity_val  # 82,000 to make AUM = 100,000

    data = _build_data(
        holdings=[
            _holding("EQ", "Equity", "Technology", equity_val),
            _holding("CASH", "Cash and Equivalents", "Cash", cash_val),
        ],
        instruments=[
            _instrument("EQ", "Equity", "Technology",
                        concentration_limit_applies="Y"),
            _instrument("CASH", "Cash and Equivalents", "Cash"),
        ],
        mandate_limit_pct=20.0,
        asset_class_for_limit="Equity",
    )
    rows = concentration_table("CL-TEST", data)
    by_key = {(r.asset_class, r.sector): r for r in rows}

    eq_row = by_key.get(("Equity", "Technology"))
    assert eq_row is not None
    assert eq_row.status == "ELEVATED", (
        f"Expected ELEVATED for {eq_row.post_look_through_pct:.2f}% vs 20% limit, "
        f"got {eq_row.status}"
    )


# ---------------------------------------------------------------------------
# Test 3: Hidden concentration callout fires when gap > 5 pp of AUM
# ---------------------------------------------------------------------------

def test_hidden_concentration_callout_fires_when_gap_exceeds_5pp() -> None:
    """A HiddenConcentration discovery should be emitted when the look-through
    gap exceeds 5 percentage points of total AUM.

    Setup: total AUM = 100,000.
    - STOCK-B (Equity / IT): 5,000 (5% of AUM)
    - SP-B references STOCK-B: 20,000 (20% of AUM)
    - CASH: 75,000

    Pre-look-through Equity/IT: 5,000 = 5% of AUM
    Post-look-through Equity/IT: 25,000 = 25% of AUM
    Gap = 20 pp → well above the 5 pp threshold → hidden concentration emitted.
    """
    total_aum = 100_000.0
    stock_val = 5_000.0
    sp_val = 20_000.0
    cash_val = total_aum - stock_val - sp_val  # 75,000

    data = _build_data(
        holdings=[
            _holding("STOCK-B", "Equity", "Information Technology", stock_val),
            _holding("SP-B", "Structured Products", "Multi", sp_val),
            _holding("CASH", "Cash and Equivalents", "Cash", cash_val),
        ],
        instruments=[
            _instrument("STOCK-B", "Equity", "Information Technology"),
            _instrument("SP-B", "Structured Products", "Multi",
                        underlying_reference="STOCK-B"),
            _instrument("CASH", "Cash and Equivalents", "Cash"),
        ],
    )
    result = concentration_result("CL-TEST", data)

    hidden = result["hidden_concentration_discoveries"]
    assert len(hidden) >= 1, (
        "Expected at least one hidden concentration discovery when gap = 20 pp"
    )

    # Find the IT discovery.
    it_discovery = next(
        (h for h in hidden if "Information Technology" in h.get("exposure_name", "")
         or "Information Technology" in h.get("explanation", "")),
        None,
    )
    assert it_discovery is not None, (
        f"Expected a discovery for Equity/IT. Got: {hidden}"
    )
    assert it_discovery["gap_pct"] == pytest.approx(20.0, abs=0.01), (
        f"Expected gap = 20 pp, got {it_discovery['gap_pct']}"
    )
