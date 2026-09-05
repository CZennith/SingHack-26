from __future__ import annotations

import math

from hypothesis import given, strategies as st
import pandas as pd

from backend.stress_test import apply_shock


@st.composite
def positive_values(draw: st.DrawFn) -> tuple[float, float, float]:
    return (
        draw(st.floats(min_value=0.01, max_value=1_000_000, allow_nan=False, allow_infinity=False)),
        draw(st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False)),
        draw(st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False)),
    )


def _run_shock(market_value: float, shock_pct: float, advance_rate: float):
    data = {
        "holdings": pd.DataFrame([
            {
                "client_id": "CL-TEST",
                "snapshot_date": "2026-08-26",
                "instrument_id": "TEST",
                "instrument_name": "Test holding",
                "asset_class": "Equity",
                "sector": "Broad Market",
                "market_value_usd": market_value,
                "advance_rate_pct": advance_rate,
            },
        ]),
        "instruments": pd.DataFrame([
            {
                "instrument_id": "TEST",
                "underlying_reference": "",
                "asset_class": "Equity",
                "sector": "Broad Market",
            },
        ]),
    }
    return apply_shock(
        "CL-TEST",
        {"shocks": {"Equity": shock_pct}, "sector_overrides": {}},
        data,
    )[0]


@given(positive_values())
def test_shock_application_is_multiplicative_scale(values: tuple[float, float, float]) -> None:
    market_value, shock_pct, advance_rate = values
    result = _run_shock(market_value, shock_pct, advance_rate)

    assert math.isclose(result.shocked_value_usd, market_value * (1 + shock_pct / 100))
    assert math.isclose(
        result.shocked_lending_value_usd,
        result.shocked_value_usd * advance_rate / 100,
    )


@given(st.floats(min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False))
def test_zero_shock_is_identity(market_value: float) -> None:
    result = _run_shock(market_value, 0.0, 50.0)
    assert result.shocked_value_usd == market_value
    assert result.dollar_change_usd == 0.0


@given(
    st.floats(min_value=0.01, max_value=1_000_000, allow_nan=False, allow_infinity=False),
    st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False),
    st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False),
)
def test_shock_monotonicity(
    market_value: float,
    lower_shock_pct: float,
    higher_shock_pct: float,
) -> None:
    lower_shock_pct, higher_shock_pct = sorted((lower_shock_pct, higher_shock_pct))
    lower_result = _run_shock(market_value, lower_shock_pct, 50.0)
    higher_result = _run_shock(market_value, higher_shock_pct, 50.0)
    assert lower_result.shocked_value_usd <= higher_result.shocked_value_usd