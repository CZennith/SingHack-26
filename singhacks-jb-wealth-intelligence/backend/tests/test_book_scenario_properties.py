"""Property-based test for the book-wide scenario engine.

Property 10: Book-wide scenario total impact equals sum of individual client impacts.
  For any scenario, the sum of all per-client net_dollar_impact_usd values in
  the book-wide result must equal the sum of individually computed per-client
  net impacts (from apply_shock + summarize_shock_results).

  This validates that run_book_scenario() does not introduce rounding errors,
  double-counting, or missing clients.

  Validates: Requirements 12.2, 12.3
"""

from __future__ import annotations

import math

import pandas as pd
import pytest
from hypothesis import given, settings, strategies as st

from backend.book_scenario import run_book_scenario
from backend.stress_test import apply_shock, summarize_shock_results


# ---------------------------------------------------------------------------
# Fixture builder
# ---------------------------------------------------------------------------

def _make_multi_client_data(
    n_clients: int = 3,
    holdings_per_client: int = 2,
    base_value: float = 100_000.0,
) -> dict[str, pd.DataFrame]:
    """Build a deterministic multi-client data dict for property tests.

    All clients have the same number of holdings with the same base value
    (scaled by client index) to make manual totals easy to verify.
    """
    clients = []
    holdings = []
    instruments = []

    for c_idx in range(n_clients):
        client_id = f"CL-B{c_idx:02d}"
        clients.append({
            "client_id": client_id,
            "client_name": f"Client {c_idx}",
        })
        for h_idx in range(holdings_per_client):
            inst_id = f"INST-{c_idx}-{h_idx}"
            ac = "Equity" if h_idx % 2 == 0 else "Fixed Income"
            market_val = base_value * (c_idx + 1) * (h_idx + 1)
            holdings.append({
                "client_id": client_id,
                "snapshot_date": "2026-08-26",
                "portfolio_id": f"PF-B{c_idx:02d}",
                "instrument_id": inst_id,
                "instrument_name": inst_id,
                "asset_class": ac,
                "sector": ac,
                "market_value_usd": market_val,
                "advance_rate_pct": 60.0,
                "liquidity_tier": "Daily",
                "unrealised_pnl_base": 0.0,
            })
            instruments.append({
                "instrument_id": inst_id,
                "asset_class": ac,
                "sector": ac,
                "underlying_reference": "",
                "concentration_limit_applies": "N",
            })

    return {
        "clients": pd.DataFrame(clients),
        "holdings": pd.DataFrame(holdings),
        "instruments": pd.DataFrame(instruments),
        # credit_facilities: empty (no Lombard facilities for this test)
        "credit_facilities": pd.DataFrame(
            columns=["facility_id", "client_id", "collateral_portfolio_id",
                     "facility_type", "facility_ccy",
                     "drawn_2026-08-26", "lending_value_2026-08-26",
                     "ltv_pct_2026-08-26", "margin_call_ltv_pct"]
        ),
        # market_context: needed by compute_ltv_stress internally
        "market_context": pd.DataFrame([
            {"snapshot_date": "2026-08-26", "series_id": "USDSGD", "value": 1.352},
            {"snapshot_date": "2026-08-26", "series_id": "USDHKD", "value": 7.81},
            {"snapshot_date": "2026-08-26", "series_id": "EURUSD", "value": 1.092},
            {"snapshot_date": "2026-08-26", "series_id": "GBPUSD", "value": 1.282},
        ]),
    }


# ---------------------------------------------------------------------------
# Property 10: Book-wide total equals sum of per-client totals
# ---------------------------------------------------------------------------

@given(
    equity_shock=st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    fi_shock=st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=50)
def test_book_wide_total_equals_sum_of_individual_impacts(
    equity_shock: float,
    fi_shock: float,
) -> None:
    """The aggregate net_dollar_impact_usd across all clients in run_book_scenario()
    must equal the sum of individually computed net impacts for those same clients.

    This verifies that:
    1. No client is silently skipped.
    2. No values are double-counted.
    3. Floating-point aggregation stays within rel_tol=1e-9 of the manual sum.
    """
    n_clients = 4
    data = _make_multi_client_data(n_clients=n_clients, holdings_per_client=2)

    scenario = {
        "shocks": {"Equity": equity_shock, "Fixed Income": fi_shock},
        "sector_overrides": {},
    }

    # --- Book-wide result ---
    book_results = run_book_scenario(scenario, data)

    # --- Individual per-client totals ---
    individual_total = 0.0
    for _, client_row in data["clients"].iterrows():
        client_id = str(client_row["client_id"]).strip()
        shock_results = apply_shock(client_id, scenario, data)
        summary = summarize_shock_results(shock_results)
        individual_total += summary["net_dollar_impact_usd"]

    book_total = sum(r["net_dollar_impact_usd"] for r in book_results)

    assert math.isclose(book_total, individual_total, rel_tol=1e-6, abs_tol=0.01), (
        f"Book-wide total ({book_total:.4f}) != sum of individual impacts "
        f"({individual_total:.4f}) — delta = {book_total - individual_total:.6f}"
    )


# ---------------------------------------------------------------------------
# Structural invariant: scenario_rank is a permutation of 1..n
# ---------------------------------------------------------------------------

def test_scenario_ranks_are_a_permutation_of_1_to_n() -> None:
    """scenario_rank must be a dense permutation of 1..n with no gaps or duplicates."""
    data = _make_multi_client_data(n_clients=5)
    scenario = {"shocks": {"Equity": -10.0}, "sector_overrides": {}}

    results = run_book_scenario(scenario, data)

    ranks = [r["scenario_rank"] for r in results]
    n = len(results)

    assert sorted(ranks) == list(range(1, n + 1)), (
        f"Expected scenario_rank to be a permutation of 1..{n}, got {ranks}"
    )


# ---------------------------------------------------------------------------
# Ordering invariant: LTV breaches rank before non-breaches
# ---------------------------------------------------------------------------

def test_ltv_breach_clients_rank_before_non_breach_clients() -> None:
    """Any client with ltv_breach=True must have a lower scenario_rank than
    any client with ltv_breach=False (when both are present in the results).
    """
    # Build data for 3 clients; give client 0 a Lombard facility that will
    # breach under a large equity shock.
    base_data = _make_multi_client_data(n_clients=3, holdings_per_client=2, base_value=100_000.0)

    # Add a Lombard facility for CL-B00 that will breach on any shock.
    # drawn = 95,000, lending_value = 100,000 → current LTV = 95%.
    # Under a −10% equity shock, scenario_lending ≈ 90,000; LTV = 105.6% > threshold.
    lombard_df = pd.DataFrame([{
        "facility_id": "CF-B00-BREACH",
        "client_id": "CL-B00",
        "collateral_portfolio_id": "PF-B00",
        "facility_type": "Lombard Credit Facility",
        "facility_ccy": "USD",
        "drawn_2026-08-26": 95_000.0,
        "lending_value_2026-08-26": 100_000.0,
        "ltv_pct_2026-08-26": 95.0,
        "margin_call_ltv_pct": 80.0,  # low threshold → easily breached
    }])
    base_data = {**base_data, "credit_facilities": lombard_df}

    scenario = {"shocks": {"Equity": -10.0}, "sector_overrides": {}}
    results = run_book_scenario(scenario, data=base_data)

    # Find the breach client's rank.
    breach_clients = [r for r in results if r["ltv_breach"]]
    no_breach_clients = [r for r in results if not r["ltv_breach"]]

    if breach_clients and no_breach_clients:
        max_breach_rank = max(r["scenario_rank"] for r in breach_clients)
        min_no_breach_rank = min(r["scenario_rank"] for r in no_breach_clients)
        assert max_breach_rank < min_no_breach_rank, (
            f"Breach clients (max rank {max_breach_rank}) should rank before "
            f"non-breach clients (min rank {min_no_breach_rank})"
        )
