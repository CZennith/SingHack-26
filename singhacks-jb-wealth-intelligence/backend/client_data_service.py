"""Build deterministic, auditable client facts from repository records.

This module is the sole service boundary for non-generated client data.  It
may calculate values and rule-based flags, but it must not generate narrative
copy or make LLM calls.
"""

import json

import pandas as pd

if __package__:
    from .data_repository import (
        get_client,
        get_client_cash_needs,
        get_client_commitments,
        get_client_facilities,
        get_client_holdings,
        get_client_portfolios,
        get_client_rm_notes,
        get_client_transactions,
        get_event_log,
        get_instruments_for_holdings,
        get_market_context,
    )
else:  # Support ``uvicorn main:app`` from inside ``backend``.
    from data_repository import (
        get_client,
        get_client_cash_needs,
        get_client_commitments,
        get_client_facilities,
        get_client_holdings,
        get_client_portfolios,
        get_client_rm_notes,
        get_client_transactions,
        get_event_log,
        get_instruments_for_holdings,
        get_market_context,
    )

_COLOURS = ["#1f1d1a", "#5d7a8c", "#a57d52", "#59725f", "#866d8c", "#8c887f"]

# This is deliberately limited to information that can help the model describe
# the client and their relationship context. Portfolio and facility facts are
# kept in their own context groups for the other insight generators.
_PROFILE_SUMMARY_CLIENT_FIELDS = (
    "client_id",
    "client_name",
    "age",
    "gender",
    "nationality",
    "country_of_residence",
    "tax_domicile",
    "booking_centre",
    "base_currency",
    "wealth_band",
    "total_aum_usd",
    "life_stage",
    "source_of_wealth",
    "risk_profile",
    "risk_tolerance_score",
    "investment_horizon_years",
    "liquidity_needs",
    "objectives",
    "client_since",
    "kyc_review_due",
    "pep_status",
    "reporting_language",
)


def _profile_summary_context(client, rm_notes) -> dict:
    """Build a JSON-ready, profile-only prompt payload from sourced records.

    RM notes are presented in chronological order and retain their dates and
    channels so the model can distinguish a current client statement from an
    older observation. They are source material, not established fact.
    """
    client_description = client.loc[
        [field for field in _PROFILE_SUMMARY_CLIENT_FIELDS if field in client.index]
    ]
    note_fields = ["note_id", "note_date", "channel", "note"]
    notes = rm_notes.sort_values("note_date", kind="stable") if not rm_notes.empty else rm_notes
    return {
        # The JSON round-trip converts pandas/numpy scalars to primitives, so
        # this dictionary can be passed straight to an LLM SDK's JSON encoder.
        "client_description": json.loads(client_description.to_json()),
        "rm_notes": json.loads(
            notes.loc[:, [field for field in note_fields if field in notes.columns]]
            .to_json(orient="records", date_format="iso")
        ),
    }


def _portfolio_explanation_context(holdings) -> dict:
    """Build dated, client-explainable attribution evidence for the LLM.

    The model receives movement facts and the *controlled* 2026 event log. It
    must connect an event only where the event's transmission channel and an
    instrument's exposure metadata support the link; it must not substitute
    remembered current events for the supplied event records.
    """
    if holdings.empty:
        return {
            "instruction": "No holding valuations are available for explanation.",
            "portfolio_value_history": [],
            "holding_movements": [],
            "instrument_exposures": [],
            "market_snapshots": [],
            "event_log_2026": [],
        }

    holdings = holdings.copy()
    holdings["snapshot_date"] = holdings["snapshot_date"].astype(str)
    snapshots = sorted(holdings["snapshot_date"].unique())
    portfolio_values = holdings.groupby("snapshot_date", as_index=False)["market_value_usd"].sum()
    portfolio_values = portfolio_values.sort_values("snapshot_date")
    portfolio_values["previous_value_usd"] = portfolio_values["market_value_usd"].shift()
    portfolio_values["value_change_usd"] = (
        portfolio_values["market_value_usd"] - portfolio_values["previous_value_usd"]
    )
    portfolio_values["return_pct"] = (
        portfolio_values["value_change_usd"] / portfolio_values["previous_value_usd"] * 100
    )

    movements = []
    keys = ["portfolio_id", "instrument_id"]
    columns = keys + ["instrument_name", "quantity", "price_local", "market_value_usd", "weight_pct"]
    for previous_date, current_date in zip(snapshots, snapshots[1:]):
        previous = holdings.loc[holdings["snapshot_date"] == previous_date, columns].copy()
        current = holdings.loc[holdings["snapshot_date"] == current_date, columns].copy()
        comparison = previous.merge(current, on=keys, how="inner", suffixes=("_start", "_end"))
        if comparison.empty:
            continue
        comparison["period_start"] = previous_date
        comparison["period_end"] = current_date
        comparison["value_change_usd"] = (
            comparison["market_value_usd_end"] - comparison["market_value_usd_start"]
        )
        comparison["price_return_pct"] = (
            (comparison["price_local_end"] / comparison["price_local_start"] - 1) * 100
        )
        comparison["quantity_changed"] = comparison["quantity_start"] != comparison["quantity_end"]
        movements.append(comparison)

    movement_columns = [
        "period_start", "period_end", "portfolio_id", "instrument_id", "instrument_name_end",
        "quantity_start", "quantity_end", "price_local_start", "price_local_end",
        "price_return_pct", "market_value_usd_start", "market_value_usd_end",
        "value_change_usd", "weight_pct_end", "quantity_changed",
    ]
    movement_frame = (
        pd.concat(movements, ignore_index=True).loc[:, movement_columns]
        if movements
        else holdings.iloc[0:0]
    )
    instruments = get_instruments_for_holdings(holdings)
    instrument_columns = [
        "instrument_id", "instrument_name", "asset_class", "sub_asset_class", "sector",
        "region", "currency", "liquidity_tier", "underlying_reference",
    ]
    event_log = get_event_log().copy()
    event_log["event_date"] = event_log["event_date"].astype(str)
    event_log = event_log.loc[
        (event_log["event_date"] >= "2026-01-01")
        & (event_log["event_date"] <= snapshots[-1])
    ].sort_values("event_date")
    market = get_market_context().copy()
    market["snapshot_date"] = market["snapshot_date"].astype(str)
    market = market.loc[market["snapshot_date"].isin(snapshots)].sort_values(
        ["snapshot_date", "series_id"]
    )

    return {
        "instruction": (
            "For 2026 events, use event_log_2026 as the sole event source. "
            "If it conflicts with model knowledge, event_log_2026 wins. Explain "
            "only supported links between event transmission channels, market "
            "snapshots, instrument exposures, and observed holding movements."
        ),
        "as_of": snapshots[-1],
        "portfolio_value_history": json.loads(portfolio_values.to_json(orient="records")),
        "holding_movements": json.loads(movement_frame.to_json(orient="records")),
        "instrument_exposures": json.loads(
            instruments.loc[:, instrument_columns].to_json(orient="records")
        ),
        "market_snapshots": json.loads(market.to_json(orient="records")),
        "event_log_2026": json.loads(event_log.to_json(orient="records")),
    }


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

    rm_notes = get_client_rm_notes(client_id)
    holdings = get_client_holdings(client_id)
    context = {
        "client": client,
        "portfolios": get_client_portfolios(client_id),
        "holdings": holdings,
        "facilities": get_client_facilities(client_id),
        "cash_needs": get_client_cash_needs(client_id),
        "commitments": get_client_commitments(client_id),
        "transactions": get_client_transactions(client_id),
        "rm_notes": rm_notes,
    }
    context["profile_summary"] = _profile_summary_context(client, rm_notes)
    context["portfolio_explanation"] = _portfolio_explanation_context(holdings)
    context["dossier"] = build_client_dossier(client_id)
    return context
