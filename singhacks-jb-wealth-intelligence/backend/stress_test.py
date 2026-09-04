"""Core deterministic calculations for the stress-test workbench."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from .stress_types import HoldingShockResult, NAMED_SCENARIOS


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