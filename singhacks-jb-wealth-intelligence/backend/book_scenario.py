"""Book-wide scenario engine.

Applies a stress scenario to every client in clients.csv and returns a ranked
per-client impact summary.  All CSVs are read from the supplied ``data`` dict
so no additional I/O occurs after the initial load — this keeps the full
20-client run well within the 3-second target (Requirement 12.6).

Public API
----------
run_book_scenario(scenario, data) -> list[dict]
    Returns a list of per-client summary dicts, sorted and ranked by:
      1. ltv_breach DESC (clients with a margin-call breach rank first)
      2. abs(net_dollar_impact_usd) DESC

    Each dict contains:
        client_id                 str
        client_name               str
        total_current_value_usd   float
        total_shocked_value_usd   float
        net_dollar_impact_usd     float
        net_pct_change            float
        ltv_breach                bool
        ltv_breach_facility_id    str | None
        scenario_rank             int   (1-based)

Requirements: 12.2, 12.3, 12.6
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

if __package__:
    from .stress_test import apply_shock, compute_ltv_stress, summarize_shock_results, _text
else:
    from stress_test import apply_shock, compute_ltv_stress, summarize_shock_results, _text


def run_book_scenario(
    scenario: str | Mapping[str, Any],
    data: Mapping[str, pd.DataFrame],
) -> list[dict[str, Any]]:
    """Run a stress scenario across all clients and return a ranked impact list.

    Parameters
    ----------
    scenario:
        Either a named scenario ID string (e.g. ``"tech-selloff"``) or a
        scenario config dict with ``shocks`` and ``sector_overrides`` keys,
        matching the shape expected by ``apply_shock()``.
    data:
        The full data dict from ``data_loader.load_all()`` — must contain at
        least ``clients``, ``holdings``, ``instruments``, ``credit_facilities``,
        and ``market_context``.

    Returns
    -------
    A list of per-client dicts sorted by impact severity, each assigned a
    ``scenario_rank`` starting at 1.
    """
    clients_df: pd.DataFrame = data["clients"]
    results: list[dict[str, Any]] = []

    for _, client_row in clients_df.iterrows():
        client_id = _text(client_row.get("client_id"))
        client_name = _text(client_row.get("client_name"))
        if not client_id:
            continue

        # ------------------------------------------------------------------
        # 1. Apply macro shock to this client's holdings.
        # ------------------------------------------------------------------
        shock_results = apply_shock(client_id, scenario, data)
        summary = summarize_shock_results(shock_results)

        # ------------------------------------------------------------------
        # 2. Compute Lombard LTV stress using shocked lending values.
        # ------------------------------------------------------------------
        ltv_rows = compute_ltv_stress(client_id, shock_results, data)

        # ------------------------------------------------------------------
        # 3. Check whether any Lombard facility would breach its margin-call
        #    threshold under the scenario-based stressed LTV.
        # ------------------------------------------------------------------
        ltv_breach = False
        ltv_breach_facility_id: str | None = None

        for ltv_row in ltv_rows:
            scenario_ltv = ltv_row.scenario_ltv
            if scenario_ltv is not None and scenario_ltv >= ltv_row.margin_call_ltv_pct:
                ltv_breach = True
                ltv_breach_facility_id = ltv_row.facility_id
                break  # First breaching facility is sufficient

        results.append({
            "client_id": client_id,
            "client_name": client_name,
            "total_current_value_usd": round(summary["total_current_value_usd"], 2),
            "total_shocked_value_usd": round(summary["total_shocked_value_usd"], 2),
            "net_dollar_impact_usd": round(summary["net_dollar_impact_usd"], 2),
            "net_pct_change": round(summary["net_pct_change"], 4),
            "ltv_breach": ltv_breach,
            "ltv_breach_facility_id": ltv_breach_facility_id,
        })

    # ------------------------------------------------------------------
    # 4. Sort: LTV breaches first, then by absolute dollar impact DESC.
    # ------------------------------------------------------------------
    results.sort(
        key=lambda r: (
            not r["ltv_breach"],              # False sorts before True, so negate
            -abs(r["net_dollar_impact_usd"]),  # larger absolute impact first
        )
    )

    # ------------------------------------------------------------------
    # 5. Assign 1-based scenario_rank.
    # ------------------------------------------------------------------
    for rank, row in enumerate(results, start=1):
        row["scenario_rank"] = rank

    return results
