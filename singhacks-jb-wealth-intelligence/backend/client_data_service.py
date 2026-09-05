"""Build deterministic, auditable client facts from repository records.

This module is the sole service boundary for non-generated client data.  It
may calculate values and rule-based flags, but it must not generate narrative
copy or make LLM calls.
"""

from data_repository import (
    get_client,
    get_client_cash_needs,
    get_client_commitments,
    get_client_facilities,
    get_client_holdings,
    get_client_portfolios,
    get_client_rm_notes,
    get_client_transactions,
)

_COLOURS = ["#1f1d1a", "#5d7a8c", "#a57d52", "#59725f", "#866d8c", "#8c887f"]


def _money(amount: float, currency: str = "USD") -> str:
    symbol = {"USD": "$", "SGD": "S$", "EUR": "€", "HKD": "HK$"}.get(currency, f"{currency} ")
    return f"{symbol}{amount / 1_000_000:.1f}M"


def build_client_dossier(client_id: str) -> dict:
    """Calculate and return the factual payload for the dossier endpoint."""
    client = get_client(client_id)
    if client is None:
        raise LookupError(f"Unknown client: {client_id}")

    portfolios = get_client_portfolios(client_id)
    holdings = get_client_holdings(client_id)
    facilities = get_client_facilities(client_id)
    latest = holdings.loc[holdings["snapshot_date"] == holdings["snapshot_date"].max()].copy() if not holdings.empty else holdings
    valuation_date = str(latest["snapshot_date"].iloc[0]) if not latest.empty else None
    total_value = float(latest["market_value_usd"].sum())
    allocation = [
        {"label": str(label), "percentage": round(float(value / total_value * 100), 1), "color": _COLOURS[index % len(_COLOURS)]}
        for index, (label, value) in enumerate(latest.groupby("asset_class")["market_value_usd"].sum().sort_values(ascending=False).items())
    ] if total_value else []
    cash_value = float(latest.loc[latest["asset_class"] == "Cash and Equivalents", "market_value_usd"].sum())
    liquid_value = float(latest.loc[latest["liquidity_tier"].isin(["Daily", "Weekly"]), "market_value_usd"].sum())
    history = holdings.groupby("snapshot_date", as_index=False)["market_value_usd"].sum().sort_values("snapshot_date")
    points = [{"date": str(row.snapshot_date), "value": round(float(row.market_value_usd), 2), "label": str(row.snapshot_date)} for row in history.itertuples()]
    start, end = (points[0]["value"], points[-1]["value"]) if points else (0, 0)
    delta = (end - start) / start * 100 if start else 0
    ltv = float(facilities["ltv_pct_2026-08-26"].max()) if not facilities.empty else 0.0
    drawn = float(facilities["drawn_2026-08-26"].sum()) if not facilities.empty else 0.0
    facility_currency = str(facilities["facility_ccy"].iloc[0]) if not facilities.empty else str(client["base_currency"])
    status = "CRITICAL" if ltv >= 75 else "ELEVATED" if ltv >= 60 else "NORMAL"
    risk = "CRITICAL" if ltv >= 75 else "HIGH" if ltv >= 60 else "MEDIUM" if float(client["risk_tolerance_score"]) <= 4 else "LOW"
    mandate = str(portfolios["mandate_name"].iloc[0]) if not portfolios.empty else str(client["risk_profile"])
    top = latest.nlargest(5, "market_value_usd")
    return {
        "id": client_id, "ref": client_id, "name": str(client["client_name"]), "initials": "".join(part[0] for part in str(client["client_name"]).split()[:2]).upper(),
        "tier": str(client["wealth_band"]), "mandate": mandate, "aum": _money(total_value), "riskLevel": risk, "headlineIssue": f"Facility LTV: {ltv:.1f}%",
        "summary": "Deterministic profile and portfolio data; advisory interpretation loads separately.", "tags": [f"Risk profile: {client['risk_profile']}", f"LTV: {ltv:.1f}%", f"Liquid assets: {liquid_value / total_value * 100:.1f}%" if total_value else "No valuation"], "suggestedNextStep": "Load advisory analysis for RM review.",
        "asOf": valuation_date, "valuationAsOf": valuation_date, "relationshipManager": {"name": str(client["rm_name"]), "title": str(client["rm_desk"])},
        "about": {"bio": f"{client['life_stage']}. Stated objectives: {client['objectives']}", "age": int(client["age"]), "occupation": str(client["source_of_wealth"]), "clientSince": int(str(client["client_since"])[:4])},
        "portfolio": {"totalValue": _money(total_value), "totalValueSubtext": "Aggregated market value (USD)", "cashLiquidity": _money(cash_value), "cashLiquidityPercent": f"{cash_value / total_value * 100:.1f}%" if total_value else "0.0%", "cashLiquiditySubtext": f"{_money(liquid_value)} daily/weekly liquidity", "borrowingUtilisation": _money(drawn, facility_currency), "borrowingLtvPercent": round(ltv, 1), "borrowingStatus": status, "allocation": allocation, "trajectory": {"deltaPercent": f"{delta:+.1f}%", "deltaPeriod": "First to latest snapshot", "startLabel": points[0]["date"] if points else "—", "troughLabel": min(points, key=lambda point: point["value"])["date"] if points else "—", "endLabel": points[-1]["date"] if points else "—", "points": points}, "topHoldings": [{"id": str(row.instrument_id), "name": str(row.instrument_name), "ticker": str(row.instrument_id), "sector": str(row.sector), "value": _money(float(row.market_value_usd)), "percentage": round(float(row.market_value_usd / total_value * 100), 1) if total_value else 0} for row in top.itertuples()], "remainingHoldingsNote": f"{len(latest) - len(top)} additional positions in the {valuation_date or 'unavailable'} valuation snapshot."},
    }


def build_client_llm_context(client_id: str) -> dict:
    """Return only sourced facts that may be supplied to an LLM.

    TODO: expose calculated values, rule-based flags, source identifiers and
    dated RM/context records. Do not include unvalidated model output here.
    """
    client = get_client(client_id)
    if client is None:
        raise LookupError(f"Unknown client: {client_id}")

    context = {
        "client": client,
        "portfolios": get_client_portfolios(client_id),
        "holdings": get_client_holdings(client_id),
        "facilities": get_client_facilities(client_id),
        "cash_needs": get_client_cash_needs(client_id),
        "commitments": get_client_commitments(client_id),
        "transactions": get_client_transactions(client_id),
        "rm_notes": get_client_rm_notes(client_id),
    }
    context["dossier"] = build_client_dossier(client_id)
    return context
