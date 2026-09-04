"""Deterministic global book prioritization from the synthetic CSV dataset."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_AS_OF = date(2026, 8, 26)
RULE_WEIGHTS = {
    "high_lombard_utilisation": 40,
    "cash_need_within_60_days": 30,
    "mandate_drift": 30,
}


def _load(data_dir: Path, filename: str) -> pd.DataFrame:
    return pd.read_csv(data_dir / filename)


def _risk_level(score: int) -> str:
    if score >= 70:
        return "CRITICAL"
    if score >= 40:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"


def _credit_triggers(facilities: pd.DataFrame) -> dict[str, dict[str, Any]]:
    lombard = facilities[
        facilities["facility_type"].str.contains("Lombard", case=False, na=False)
        & (pd.to_numeric(facilities["utilisation_pct_current"], errors="coerce") > 70)
    ]
    triggers: dict[str, dict[str, Any]] = {}
    for _, row in lombard.iterrows():
        triggers.setdefault(row["client_id"], {
            "code": "HIGH_LOMBARD_UTILISATION",
            "points": RULE_WEIGHTS["high_lombard_utilisation"],
            "label": "Lombard credit utilization above 70%",
            "evidence": [],
        })["evidence"].append({
            "facility_id": row["facility_id"],
            "utilisation_pct_current": float(row["utilisation_pct_current"]),
        })
    return triggers


def _cash_triggers(cash_needs: pd.DataFrame, as_of: date) -> dict[str, dict[str, Any]]:
    needs = cash_needs.copy()
    needs["due_from_date"] = pd.to_datetime(needs["due_from"], errors="coerce").dt.date
    cutoff = as_of + timedelta(days=60)
    needs = needs[needs["due_from_date"].between(as_of, cutoff)]

    triggers: dict[str, dict[str, Any]] = {}
    for _, row in needs.iterrows():
        triggers.setdefault(row["client_id"], {
            "code": "CASH_NEED_WITHIN_60_DAYS",
            "points": RULE_WEIGHTS["cash_need_within_60_days"],
            "label": "Planned cash need due within 60 days",
            "evidence": [],
        })["evidence"].append({
            "need_id": row["need_id"],
            "description": row["description"],
            "due_from": row["due_from"],
            "amount": float(row["amount"]),
            "currency": row["currency"],
        })
    return triggers


def _mandate_triggers(
    portfolios: pd.DataFrame,
    holdings: pd.DataFrame,
    mandates: pd.DataFrame,
    as_of: date,
) -> dict[str, dict[str, Any]]:
    managed = portfolios[portfolios["service_model"].ne("Custody")]
    current_holdings = holdings[holdings["snapshot_date"].eq(as_of.isoformat())]
    allocations = (
        current_holdings.groupby(["portfolio_id", "client_id", "asset_class"], as_index=False)["weight_pct"]
        .sum()
    )
    allocations = allocations.merge(
        managed[["portfolio_id", "mandate_code"]], on="portfolio_id", how="inner"
    )
    allocations = allocations.merge(
        mandates[["mandate_code", "asset_class", "min_pct", "max_pct"]],
        on=["mandate_code", "asset_class"],
        how="left",
    )
    breached = allocations[
        allocations["min_pct"].notna()
        & ((allocations["weight_pct"] < allocations["min_pct"]) | (allocations["weight_pct"] > allocations["max_pct"]))
    ]

    triggers: dict[str, dict[str, Any]] = {}
    for _, row in breached.iterrows():
        triggers.setdefault(row["client_id"], {
            "code": "MANDATE_DRIFT",
            "points": RULE_WEIGHTS["mandate_drift"],
            "label": "Managed portfolio allocation outside mandate limits",
            "evidence": [],
        })["evidence"].append({
            "portfolio_id": row["portfolio_id"],
            "mandate_code": row["mandate_code"],
            "asset_class": row["asset_class"],
            "weight_pct": round(float(row["weight_pct"]), 4),
            "min_pct": float(row["min_pct"]),
            "max_pct": float(row["max_pct"]),
        })
    return triggers


def calculate_prioritization(
    data_dir: Path,
    as_of: date = DEFAULT_AS_OF,
) -> dict[str, Any]:
    clients = _load(data_dir, "clients.csv")
    portfolios = _load(data_dir, "portfolios.csv")
    holdings = _load(data_dir, "holdings.csv")
    mandates = _load(data_dir, "mandates.csv")
    facilities = _load(data_dir, "credit_facilities.csv")
    cash_needs = _load(data_dir, "planned_cash_needs.csv")

    trigger_maps = (
        _credit_triggers(facilities),
        _cash_triggers(cash_needs, as_of),
        _mandate_triggers(portfolios, holdings, mandates, as_of),
    )
    leaderboard = []
    for _, client in clients.iterrows():
        client_id = client["client_id"]
        triggers = [trigger_map[client_id] for trigger_map in trigger_maps if client_id in trigger_map]
        score = sum(trigger["points"] for trigger in triggers)
        leaderboard.append({
            "client_id": client_id,
            "client_name": client["client_name"],
            "total_aum_usd": float(client["total_aum_usd"]),
            "urgency_score": score,
            "risk_level": _risk_level(score),
            "trigger_reasons": triggers,
        })

    leaderboard.sort(
        key=lambda row: (-row["urgency_score"], -len(row["trigger_reasons"]), -row["total_aum_usd"], row["client_id"])
    )
    for rank, row in enumerate(leaderboard, start=1):
        row["rank"] = rank

    return {
        "as_of": as_of.isoformat(),
        "rule_weights": RULE_WEIGHTS,
        "clients": leaderboard,
    }


if __name__ == "__main__":
    import json

    repository_root = Path(__file__).resolve().parent.parent
    print(json.dumps(calculate_prioritization(repository_root / "data"), indent=2))