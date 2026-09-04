from __future__ import annotations

import pandas as pd

from backend.stress_test import apply_shock
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