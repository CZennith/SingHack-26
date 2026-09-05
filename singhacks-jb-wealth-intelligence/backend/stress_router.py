"""FastAPI router for all /api/stress-test/* endpoints.

Mounted in api.py via ``app.include_router(stress_router)``.

Endpoints
---------
POST /api/stress-test/run
    Full stress suite for one client: macro shock + LTV + mandate guard + narrative.

GET  /api/stress-test/look-through?client_id=...
    Look-through concentration analysis for one client.

GET  /api/stress-test/liquidity?client_id=...
    60-day LCR calculation, sell-to-cover, and life-event flags for one client.

POST /api/stress-test/book-scenario
    Scenario shock across all 20 clients — returns ranked impact leaderboard.

GET  /api/stress-test/narrative?client_id=...&scenario_id=...
    2-4 sentence scenario narrative for a specific client and scenario.

Requirements: 3.1, 4.1, 5.1, 6.1, 8.1, 12.2
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, field_validator

if __package__:
    from .book_scenario import run_book_scenario
    from .data_loader import load_all
    from .liquidity import compute_lcr
    from .look_through import concentration_result
    from .scenario_narrative import generate_narrative
    from .stress_test import apply_shock, compute_ltv_stress, mandate_guard, summarize_shock_results
    from .stress_types import NAMED_SCENARIOS
else:
    from book_scenario import run_book_scenario
    from data_loader import load_all
    from liquidity import compute_lcr
    from look_through import concentration_result
    from scenario_narrative import generate_narrative
    from stress_test import apply_shock, compute_ltv_stress, mandate_guard, summarize_shock_results
    from stress_types import NAMED_SCENARIOS

# ---------------------------------------------------------------------------
# Router setup
# ---------------------------------------------------------------------------

stress_router = APIRouter(prefix="/stress-test", tags=["stress-test"])

# DATA_DIR is resolved relative to this file so the router always reads from
# the same CSV fixtures as the rest of the backend.
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# rm_notes.json lives alongside the CSVs.
RM_NOTES_PATH = DATA_DIR / "rm_notes.json"

# Cache the data dict at module level (loaded once on first request, reused
# for all subsequent calls within the same process lifetime).
_DATA_CACHE: dict[str, Any] | None = None


def _get_data() -> dict[str, Any]:
    global _DATA_CACHE  # noqa: PLW0603
    if _DATA_CACHE is None:
        _DATA_CACHE = load_all(DATA_DIR)
        # Attach rm_notes as a list of dicts so modules can consume it.
        if RM_NOTES_PATH.exists():
            try:
                with RM_NOTES_PATH.open(encoding="utf-8") as f:
                    _DATA_CACHE["rm_notes"] = json.load(f)
            except (OSError, json.JSONDecodeError):
                _DATA_CACHE["rm_notes"] = []
        else:
            _DATA_CACHE["rm_notes"] = []
    return _DATA_CACHE


def _client_exists(client_id: str, data: dict[str, Any]) -> bool:
    clients_df = data.get("clients")
    if clients_df is None:
        return False
    return bool(clients_df["client_id"].eq(client_id).any())


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------

class ShockConfig(BaseModel):
    """Per-scenario shock configuration.

    ``scenario_id`` is one of the five named scenario IDs or "custom".
    ``shocks`` maps asset class names to shock percentages.
    ``sector_overrides`` optionally overrides shock at the sector level.
    """

    scenario_id: str
    shocks: dict[str, float] = {}
    sector_overrides: dict[str, float] = {}

    @field_validator("shocks", "sector_overrides", mode="before")
    @classmethod
    def _validate_shock_range(cls, v: dict[str, float]) -> dict[str, float]:
        """All shock values must be in the closed interval [−100, 100]."""
        for key, pct in (v or {}).items():
            if not (-100.0 <= pct <= 100.0):
                raise ValueError(
                    f"shock_pct for '{key}' is {pct:.2f} — "
                    "values must be in the range [−100, 100]."
                )
        return v


class StressRunRequest(BaseModel):
    client_id: str
    scenario: ShockConfig
    as_of: date = date(2026, 8, 26)


class BookScenarioRequest(BaseModel):
    scenario: ShockConfig
    as_of: date = date(2026, 8, 26)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_scenario_config(shock_config: ShockConfig) -> dict[str, Any]:
    """Return a scenario dict that apply_shock() can consume.

    Named scenarios pull shocks from NAMED_SCENARIOS and let the caller
    override individual values.  Custom scenarios use the caller's shocks
    directly.
    """
    if shock_config.scenario_id in NAMED_SCENARIOS:
        base = dict(NAMED_SCENARIOS[shock_config.scenario_id])
        # Caller overrides take precedence over named-scenario defaults.
        merged_shocks = {**base.get("shocks", {}), **shock_config.shocks}
        merged_overrides = {**base.get("sector_overrides", {}), **shock_config.sector_overrides}
        return {
            **base,
            "shocks": merged_shocks,
            "sector_overrides": merged_overrides,
        }
    # Custom scenario — use caller's shocks as-is.
    return {
        "label": shock_config.scenario_id,
        "shocks": shock_config.shocks,
        "sector_overrides": shock_config.sector_overrides,
    }


def _build_recommendations(
    client_id: str,
    shock_summary: dict[str, Any],
    ltv_rows: list[Any],
    lcr_result: Any,
    data: dict[str, Any],
    as_of_str: str,
) -> list[dict[str, Any]]:
    """Derive a set of RM recommendations from stress results for mandate_guard input."""
    recs: list[dict[str, Any]] = []

    # 1. Macro shock: if net impact > 5%, recommend reviewing largest loser.
    top = shock_summary.get("top_impacted_holdings", [])
    if shock_summary.get("net_pct_change", 0) < -5.0 and top:
        worst = top[0]
        recs.append({
            "action_verb": "Reduce",
            "asset_class": worst.effective_asset_class,
            "holding_name": worst.instrument_name,
            "weight_change": -5.0,
            "rationale": (
                f"Scenario impact of {shock_summary['net_pct_change']:.1f}% driven by "
                f"{worst.instrument_name} ({worst.effective_asset_class}). "
                "Consider reducing exposure to limit further downside."
            ),
        })

    # 2. LTV: if any facility breaches margin call, recommend reducing Lombard utilisation.
    for ltv_row in ltv_rows:
        scenario_ltv = ltv_row.scenario_ltv
        if scenario_ltv is not None and scenario_ltv >= ltv_row.margin_call_ltv_pct:
            recs.append({
                "action_verb": "Reduce",
                "asset_class": "Fixed Income",
                "holding_name": ltv_row.facility_id,
                "weight_change": -10.0,
                "rationale": (
                    f"Lombard facility {ltv_row.facility_id} scenario LTV "
                    f"{scenario_ltv:.1f}% ≥ margin call threshold "
                    f"{ltv_row.margin_call_ltv_pct:.1f}%. "
                    "Reducing collateral exposure or paying down the facility is advised."
                ),
            })

    # 3. Liquidity: if LCR < 1.0, recommend selling a Tier-1 holding.
    if lcr_result.lcr is not None and lcr_result.lcr < 1.0 and lcr_result.sell_to_cover:
        top_sell = lcr_result.sell_to_cover[0]
        recs.append({
            "action_verb": "Sell",
            "asset_class": "Cash and Equivalents",
            "holding_name": top_sell["instrument_name"],
            "weight_change": -8.0,
            "rationale": (
                f"60-day LCR is {lcr_result.lcr:.2f} — below 1.0. "
                f"Consider selling {top_sell['instrument_name']} "
                f"(daily liquid, unrealised P&L {top_sell['unrealised_pnl_usd']:,.0f} USD) "
                "to meet upcoming obligations."
            ),
        })

    return recs


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@stress_router.post("/run")
def run_stress_test(req: StressRunRequest) -> dict[str, Any]:
    """Full stress suite for one client.

    Returns macro shock results, LTV stress, recommendations (mandate-checked),
    scenario narrative, and projected urgency score impact.
    """
    data = _get_data()
    as_of_str = req.as_of.strftime("%Y-%m-%d")

    if not _client_exists(req.client_id, data):
        raise HTTPException(status_code=404, detail=f"Client '{req.client_id}' not found.")

    scenario_config = _resolve_scenario_config(req.scenario)

    # --- Macro shock ---
    shock_results = apply_shock(req.client_id, scenario_config, data, as_of=as_of_str)
    shock_summary = summarize_shock_results(shock_results)

    # --- LTV stress ---
    ltv_rows = compute_ltv_stress(req.client_id, shock_results, data, as_of=as_of_str)

    # --- Liquidity ---
    lcr_result = compute_lcr(req.client_id, data, as_of=req.as_of)

    # --- Recommendations (before mandate guard) ---
    raw_recs = _build_recommendations(
        req.client_id, shock_summary, ltv_rows, lcr_result, data, as_of_str
    )

    # --- Mandate guard ---
    guarded_recs = mandate_guard(req.client_id, raw_recs, data, as_of=as_of_str)

    # --- Narrative ---
    top_holdings: list[tuple[str, str]] = [
        (h.instrument_name, h.effective_asset_class)
        for h in shock_summary["top_impacted_holdings"][:3]
    ]
    narrative_text = generate_narrative(
        req.client_id, req.scenario.scenario_id, top_holdings, data
    )

    # --- Serialise results ---
    result_id = "sr-" + uuid.uuid4().hex[:8]

    scenario_label = scenario_config.get(
        "label", NAMED_SCENARIOS.get(req.scenario.scenario_id, {}).get("label", req.scenario.scenario_id)
    )

    return {
        "result_id": result_id,
        "as_of": as_of_str,
        "client_id": req.client_id,
        "scenario": {
            "id": req.scenario.scenario_id,
            "label": scenario_label,
        },
        "macro_shock": {
            "client_id": req.client_id,
            "scenario_id": req.scenario.scenario_id,
            "as_of": as_of_str,
            "total_current_value_usd": shock_summary["total_current_value_usd"],
            "total_shocked_value_usd": shock_summary["total_shocked_value_usd"],
            "net_dollar_impact_usd": shock_summary["net_dollar_impact_usd"],
            "net_pct_change": shock_summary["net_pct_change"],
            "top_impacted_holdings": [
                {
                    "instrument_id": h.instrument_id,
                    "instrument_name": h.instrument_name,
                    "asset_class": h.effective_asset_class,
                    "look_through_applied": h.look_through_applied,
                    "current_value_usd": h.current_value_usd,
                    "shocked_value_usd": h.shocked_value_usd,
                    "dollar_change_usd": h.dollar_change_usd,
                    "advance_rate_pct": h.advance_rate_pct,
                    "shocked_lending_value_usd": h.shocked_lending_value_usd,
                }
                for h in shock_summary["top_impacted_holdings"]
            ],
        },
        "ltv_stress": {
            "client_id": req.client_id,
            "facilities": [
                {
                    "facility_id": r.facility_id,
                    "facility_type": "Lombard",
                    "drawn_usd": r.drawn_usd,
                    "current_ltv_pct": r.current_ltv_pct,
                    "margin_call_ltv_pct": r.margin_call_ltv_pct,
                    "ltv_at_minus_10_pct": r.ltv_minus_10 if r.ltv_minus_10 != float("inf") else None,
                    "ltv_at_minus_20_pct": r.ltv_minus_20 if r.ltv_minus_20 != float("inf") else None,
                    "ltv_at_minus_30_pct": r.ltv_minus_30 if r.ltv_minus_30 != float("inf") else None,
                    "scenario_ltv_pct": r.scenario_ltv,
                    "headroom_at_minus_10_usd": r.headroom_minus_10,
                    "headroom_at_minus_20_usd": r.headroom_minus_20,
                    "headroom_at_minus_30_usd": r.headroom_minus_30,
                    "scenario_headroom_usd": r.scenario_headroom,
                }
                for r in ltv_rows
            ],
        },
        "liquidity": {
            "client_id": req.client_id,
            "as_of": as_of_str,
            "total_60d_obligations_usd": lcr_result.total_60d_obligations_usd,
            "tier1_liquid_value_usd": lcr_result.tier1_liquid_value_usd,
            "lcr": lcr_result.lcr,
            "status": lcr_result.status,
            "surplus_or_gap_usd": lcr_result.surplus_or_gap_usd,
            "sell_to_cover": lcr_result.sell_to_cover,
            "life_event_flags": lcr_result.life_event_flags,
        },
        "narrative": narrative_text,
        "recommendations": guarded_recs,
    }


@stress_router.get("/look-through")
def get_look_through(
    client_id: str = Query(..., description="Client identifier, e.g. CL-0002"),
    as_of: str = Query("2026-08-26", description="Snapshot date (YYYY-MM-DD)"),
) -> dict[str, Any]:
    """Look-through concentration analysis for one client."""
    data = _get_data()

    if not _client_exists(client_id, data):
        raise HTTPException(status_code=404, detail=f"Client '{client_id}' not found.")

    result = concentration_result(client_id, data, as_of=as_of)

    return {
        "client_id": client_id,
        "as_of": as_of,
        "total_aum_usd": result["total_aum_usd"],
        "concentrations": [
            {
                "exposure_name": row.exposure_name,
                "asset_class": row.asset_class,
                "sector": row.sector,
                "pre_look_through_pct": row.pre_look_through_pct,
                "post_look_through_pct": row.post_look_through_pct,
                "mandate_limit_pct": row.mandate_limit_pct,
                "status": row.status,
            }
            for row in result["concentrations"]
        ],
        "hidden_concentration_discoveries": result["hidden_concentration_discoveries"],
    }


@stress_router.get("/liquidity")
def get_liquidity(
    client_id: str = Query(..., description="Client identifier, e.g. CL-0002"),
    as_of: str = Query("2026-08-26", description="Snapshot date (YYYY-MM-DD)"),
) -> dict[str, Any]:
    """60-day LCR calculation, sell-to-cover list, and life-event flags."""
    data = _get_data()

    if not _client_exists(client_id, data):
        raise HTTPException(status_code=404, detail=f"Client '{client_id}' not found.")

    as_of_date = date.fromisoformat(as_of)
    result = compute_lcr(client_id, data, as_of=as_of_date)

    return {
        "client_id": client_id,
        "as_of": as_of,
        "total_60d_obligations_usd": result.total_60d_obligations_usd,
        "tier1_liquid_value_usd": result.tier1_liquid_value_usd,
        "lcr": result.lcr,
        "status": result.status,
        "surplus_or_gap_usd": result.surplus_or_gap_usd,
        "sell_to_cover": result.sell_to_cover,
        "life_event_flags": result.life_event_flags,
    }


@stress_router.post("/book-scenario")
def post_book_scenario(req: BookScenarioRequest) -> dict[str, Any]:
    """Scenario shock across all 20 clients — returns ranked impact leaderboard."""
    data = _get_data()
    as_of_str = req.as_of.strftime("%Y-%m-%d")
    scenario_config = _resolve_scenario_config(req.scenario)

    clients_result = run_book_scenario(scenario_config, data)

    scenario_label = scenario_config.get(
        "label", NAMED_SCENARIOS.get(req.scenario.scenario_id, {}).get("label", req.scenario.scenario_id)
    )

    return {
        "scenario": {
            "id": req.scenario.scenario_id,
            "label": scenario_label,
        },
        "as_of": as_of_str,
        "clients": clients_result,
    }


@stress_router.get("/narrative")
def get_narrative(
    client_id: str = Query(..., description="Client identifier, e.g. CL-0002"),
    scenario_id: str = Query(..., description="Named scenario ID or 'custom'"),
    as_of: str = Query("2026-08-26", description="Snapshot date (YYYY-MM-DD)"),
) -> dict[str, Any]:
    """2–4 sentence scenario narrative for a specific client and scenario."""
    data = _get_data()

    if not _client_exists(client_id, data):
        raise HTTPException(status_code=404, detail=f"Client '{client_id}' not found.")

    # Derive top affected holdings for context (run a quick shock to find them).
    if scenario_id in NAMED_SCENARIOS:
        shock_results = apply_shock(client_id, scenario_id, data, as_of=as_of)
        shock_summary = summarize_shock_results(shock_results)
        top_holdings: list[tuple[str, str]] = [
            (h.instrument_name, h.effective_asset_class)
            for h in shock_summary["top_impacted_holdings"][:3]
        ]
    else:
        top_holdings = []

    narrative_text = generate_narrative(client_id, scenario_id, top_holdings, data)

    return {
        "narrative": narrative_text,
        "top_affected_holdings": [name for name, _ in top_holdings],
    }
