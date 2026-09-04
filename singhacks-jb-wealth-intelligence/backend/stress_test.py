"""Core deterministic calculations for the stress-test workbench."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from .stress_types import HoldingShockResult, LTVStressRow, NAMED_SCENARIOS


AS_OF = "2026-08-26"


def _number(value: Any, default: float = 0.0) -> float:
    """Convert a CSV value to a finite float, tolerating blank cells."""
    converted = pd.to_numeric(value, errors="coerce")
    return default if pd.isna(converted) else float(converted)


def _text(value: Any) -> str:
    return "" if pd.isna(value) else str(value).strip()


def _scenario_values(scenario: str | Mapping[str, Any]) -> Mapping[str, Any]:
    if isinstance(scenario, str):
        try:
            return NAMED_SCENARIOS[scenario]
        except KeyError as error:
            raise ValueError(f"Unknown scenario: {scenario}") from error
    return scenario


def _effective_exposure(
    holding: pd.Series,
    instruments_by_id: Mapping[str, pd.Series],
) -> tuple[str, str, bool]:
    instrument = instruments_by_id.get(_text(holding.get("instrument_id")))
    underlying_reference = _text(instrument.get("underlying_reference")) if instrument is not None else ""
    underlying = instruments_by_id.get(underlying_reference) if underlying_reference else None
    if underlying is not None:
        return (
            _text(underlying.get("asset_class")),
            _text(underlying.get("sector")),
            True,
        )
    return _text(holding.get("asset_class")), _text(holding.get("sector")), False


def _instrument_index(instruments: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        _text(row["instrument_id"]): row
        for _, row in instruments.iterrows()
        if _text(row.get("instrument_id"))
    }


def apply_shock(
    client_id: str,
    scenario: str | Mapping[str, Any],
    data: Mapping[str, pd.DataFrame],
    as_of: str = AS_OF,
) -> list[HoldingShockResult]:
    """Apply a scenario to all current holdings for one client.

    Results include every holding, including holdings with a zero shock. This is
    intentional: downstream calculations need the complete shocked collateral
    set, while presentation code can select the most impacted ten separately.
    """
    scenario_values = _scenario_values(scenario)
    shocks = scenario_values.get("shocks", {})
    sector_overrides = scenario_values.get("sector_overrides", {})
    holdings = data["holdings"]
    instruments_by_id = _instrument_index(data["instruments"])
    current = holdings[
        holdings["client_id"].eq(client_id)
        & holdings["snapshot_date"].astype(str).eq(as_of)
    ]

    results: list[HoldingShockResult] = []
    for _, holding in current.iterrows():
        asset_class, sector, looked_through = _effective_exposure(holding, instruments_by_id)
        shock_pct = _number(sector_overrides.get(sector, shocks.get(asset_class, 0.0)))
        current_value = _number(holding.get("market_value_usd"))
        shocked_value = current_value * (1.0 + shock_pct / 100.0)
        advance_rate = _number(holding.get("advance_rate_pct"))
        results.append(
            HoldingShockResult(
                instrument_id=_text(holding.get("instrument_id")),
                instrument_name=_text(holding.get("instrument_name")),
                effective_asset_class=asset_class,
                effective_sector=sector,
                look_through_applied=looked_through,
                current_value_usd=current_value,
                shocked_value_usd=shocked_value,
                dollar_change_usd=shocked_value - current_value,
                advance_rate_pct=advance_rate,
                shocked_lending_value_usd=shocked_value * advance_rate / 100.0,
            )
        )
    return results


def summarize_shock_results(results: list[HoldingShockResult]) -> dict[str, Any]:
    """Return portfolio totals and the ten holdings with largest absolute impact."""
    total_current = sum(result.current_value_usd for result in results)
    total_shocked = sum(result.shocked_value_usd for result in results)
    net_impact = total_shocked - total_current
    return {
        "total_current_value_usd": total_current,
        "total_shocked_value_usd": total_shocked,
        "net_dollar_impact_usd": net_impact,
        "net_pct_change": (net_impact / total_current * 100.0) if total_current else 0.0,
        "top_impacted_holdings": sorted(
            results,
            key=lambda result: abs(result.dollar_change_usd),
            reverse=True,
        )[:10],
    }


# ---------------------------------------------------------------------------
# FX helpers
# ---------------------------------------------------------------------------

def _build_fx_rates(market_context: pd.DataFrame, as_of: str) -> dict[str, float]:
    """Return a dict of {series_id: value} for the given snapshot date.

    Only FX series are needed here, but we load all rows for the date to avoid
    a second filter pass. The caller converts currency amounts using ``to_usd()``.
    """
    snapshot = market_context[market_context["snapshot_date"].astype(str) == as_of]
    return {
        _text(row["series_id"]): _number(row["value"])
        for _, row in snapshot.iterrows()
        if _text(row.get("series_id"))
    }


def to_usd(amount: float, currency: str, fx_rates: dict[str, float]) -> float:
    """Convert *amount* in *currency* to USD using the supplied FX rate dict.

    Convention matches the data dictionary:
      - USDSGD = SGD per USD  → divide by rate to get USD
      - USDHKD = HKD per USD  → divide by rate to get USD
      - EURUSD = USD per EUR  → multiply by rate to get USD
      - GBPUSD = USD per GBP  → multiply by rate to get USD
    """
    if currency == "USD":
        return amount
    if currency == "SGD":
        rate = fx_rates.get("USDSGD", 1.0)
        return amount / rate if rate else amount
    if currency == "HKD":
        rate = fx_rates.get("USDHKD", 1.0)
        return amount / rate if rate else amount
    if currency == "EUR":
        rate = fx_rates.get("EURUSD", 1.0)
        return amount * rate
    if currency == "GBP":
        rate = fx_rates.get("GBPUSD", 1.0)
        return amount * rate
    # Unknown currency — return amount unchanged (best-effort)
    return amount


# ---------------------------------------------------------------------------
# LTV stress engine
# ---------------------------------------------------------------------------

def _safe_ltv(drawn: float, lending_value: float) -> float | None:
    """Compute LTV as a percentage, returning None if lending value is zero.

    Returning None (rather than ±infinity) allows the frontend to render
    "N/A" instead of a nonsense number.
    """
    if lending_value == 0.0:
        return None
    return drawn / lending_value * 100.0


def compute_ltv_stress(
    client_id: str,
    shocked_lending_values: list[HoldingShockResult],
    data: Mapping[str, pd.DataFrame],
    as_of: str = AS_OF,
) -> list[LTVStressRow]:
    """Compute Lombard LTV stress for all facilities belonging to *client_id*.

    Two independent stress views are produced for each facility:

    1. **Stand-alone haircut stress** (always computed): the CSV column
       ``lending_value_2026-08-26`` is reduced by −10%, −20%, and −30% to
       show sensitivity independent of any scenario.

    2. **Scenario-based stress** (only when *shocked_lending_values* is
       non-empty): the shocked lending values from ``apply_shock()`` are
       summed per collateral portfolio and used as the facility's stressed
       collateral value.

    The ``drawn_2026-08-26`` amount is converted to USD from the facility's
    native currency using the ``market_context.csv`` FX snapshot.
    """
    fx_rates = _build_fx_rates(data["market_context"], as_of)
    facilities = data["credit_facilities"]

    # Filter to Lombard facilities for this client only.
    lombard = facilities[
        facilities["client_id"].eq(client_id)
        & facilities["facility_type"].str.contains("Lombard", case=False, na=False)
    ]

    # Pre-compute scenario lending value per collateral portfolio so we do the
    # aggregation once rather than once per facility.
    scenario_by_portfolio: dict[str, float] = {}
    if shocked_lending_values:
        holdings_df = data["holdings"]
        # Map instrument_id → portfolio_id using the holdings snapshot.
        snapshot_holdings = holdings_df[
            holdings_df["client_id"].eq(client_id)
            & holdings_df["snapshot_date"].astype(str).eq(as_of)
        ]
        instrument_to_portfolio: dict[str, str] = {
            _text(row["instrument_id"]): _text(row["portfolio_id"])
            for _, row in snapshot_holdings.iterrows()
            if _text(row.get("instrument_id")) and _text(row.get("portfolio_id"))
        }
        for shock_result in shocked_lending_values:
            portfolio_id = instrument_to_portfolio.get(shock_result.instrument_id, "")
            if portfolio_id:
                scenario_by_portfolio[portfolio_id] = (
                    scenario_by_portfolio.get(portfolio_id, 0.0)
                    + shock_result.shocked_lending_value_usd
                )

    rows: list[LTVStressRow] = []
    for _, fac in lombard.iterrows():
        facility_id = _text(fac.get("facility_id"))
        facility_ccy = _text(fac.get("facility_ccy")) or "USD"
        collateral_portfolio_id = _text(fac.get("collateral_portfolio_id"))

        # Drawn amount → convert to USD.
        drawn_raw = _number(fac.get(f"drawn_{as_of}"))
        drawn_usd = to_usd(drawn_raw, facility_ccy, fx_rates)

        # Base lending value from CSV (already in facility CCY → convert to USD).
        base_lending_raw = _number(fac.get(f"lending_value_{as_of}"))
        base_lending_usd = to_usd(base_lending_raw, facility_ccy, fx_rates)

        # Current LTV — read from CSV directly (pre-computed, authoritative).
        current_ltv = _number(fac.get(f"ltv_pct_{as_of}"))
        margin_call_ltv = _number(fac.get("margin_call_ltv_pct"))

        # Stand-alone haircut stress (−10%, −20%, −30%).
        stressed_10 = base_lending_usd * 0.90
        stressed_20 = base_lending_usd * 0.80
        stressed_30 = base_lending_usd * 0.70

        ltv_10 = _safe_ltv(drawn_usd, stressed_10)
        ltv_20 = _safe_ltv(drawn_usd, stressed_20)
        ltv_30 = _safe_ltv(drawn_usd, stressed_30)

        headroom_10 = stressed_10 - drawn_usd
        headroom_20 = stressed_20 - drawn_usd
        headroom_30 = stressed_30 - drawn_usd

        # Scenario-based stress (only when shocked collateral is available).
        scenario_lending = scenario_by_portfolio.get(collateral_portfolio_id)
        scenario_ltv: float | None = None
        scenario_headroom: float | None = None
        if scenario_lending is not None:
            scenario_ltv = _safe_ltv(drawn_usd, scenario_lending)
            scenario_headroom = scenario_lending - drawn_usd

        rows.append(
            LTVStressRow(
                facility_id=facility_id,
                drawn_usd=drawn_usd,
                current_lending_value_usd=base_lending_usd,
                current_ltv_pct=current_ltv,
                margin_call_ltv_pct=margin_call_ltv,
                ltv_minus_10=ltv_10 if ltv_10 is not None else float("inf"),
                ltv_minus_20=ltv_20 if ltv_20 is not None else float("inf"),
                ltv_minus_30=ltv_30 if ltv_30 is not None else float("inf"),
                scenario_ltv=scenario_ltv,
                headroom_minus_10=headroom_10,
                headroom_minus_20=headroom_20,
                headroom_minus_30=headroom_30,
                scenario_headroom=scenario_headroom,
            )
        )

    return rows
