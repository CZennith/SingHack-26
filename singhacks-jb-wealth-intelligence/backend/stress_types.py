"""Shared immutable result types and named scenario definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HoldingShockResult:
    instrument_id: str
    instrument_name: str
    effective_asset_class: str
    effective_sector: str
    look_through_applied: bool
    current_value_usd: float
    shocked_value_usd: float
    dollar_change_usd: float
    advance_rate_pct: float
    shocked_lending_value_usd: float


@dataclass(frozen=True)
class LTVStressRow:
    facility_id: str
    drawn_usd: float
    current_lending_value_usd: float
    current_ltv_pct: float
    margin_call_ltv_pct: float
    ltv_minus_10: float
    ltv_minus_20: float
    ltv_minus_30: float
    scenario_ltv: float | None
    headroom_minus_10: float
    headroom_minus_20: float
    headroom_minus_30: float
    scenario_headroom: float | None


@dataclass(frozen=True)
class ConcentrationRow:
    exposure_name: str
    asset_class: str
    sector: str
    pre_look_through_value_usd: float
    post_look_through_value_usd: float
    pre_look_through_pct: float
    post_look_through_pct: float
    mandate_limit_pct: float | None
    status: str


@dataclass(frozen=True)
class LiquidityResult:
    total_60d_obligations_usd: float
    tier1_liquid_value_usd: float
    lcr: float
    surplus_or_gap_usd: float
    sell_to_cover: list[dict[str, Any]]
    life_event_flags: list[dict[str, Any]]


NAMED_SCENARIOS: dict[str, dict[str, Any]] = {
    "hormuz-escalation": {
        "label": "Strait of Hormuz Escalation",
        "severity": "Severe",
        "shocks": {
            "Commodities": +40.0,
            "Equity": -8.0,
            "Fixed Income": +3.0,
            "Alternatives": +15.0,
        },
        "sector_overrides": {
            "Airlines": -20.0,
            "Information Technology": +0.0,
            "Energy": +40.0,
        },
        "event_log_ref": "2026-02-28",
    },
    "hormuz-de-escalation": {
        "label": "Hormuz Reopens / De-escalation",
        "shocks": {
            "Commodities": -25.0,
            "Equity": +5.0,
            "Alternatives": -8.0,
        },
        "sector_overrides": {"Airlines": +12.0, "Energy": -25.0},
        "event_log_ref": None,
    },
    "tech-selloff": {
        "label": "Tech Sector Selloff",
        "shocks": {"Equity": -8.0},
        "sector_overrides": {"Information Technology": -20.0},
        "event_log_ref": "2026-06-15",
    },
    "rate-shock": {
        "label": "Rate Shock — Fed Hikes",
        "shocks": {"Fixed Income": -12.0, "Equity": -8.0},
        "sector_overrides": {},
        "event_log_ref": None,
    },
    "gold-consolidation": {
        "label": "Gold Consolidation",
        "shocks": {"Alternatives": -15.0, "Commodities": -15.0},
        "sector_overrides": {},
        "event_log_ref": "2026-01-28",
    },
}