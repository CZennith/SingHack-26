"""Integration tests for the book-wide scenario engine and backend API router.

Task 9.3 (book-wide integration):
  - run_book_scenario with 'hormuz-escalation' against the real CSV fixtures
  - All 20 clients appear; scenario_rank is a permutation of 1..20
  - Result completes in < 3 seconds (Requirement 12.6)

Task 10.3 (router integration) will extend this file once stress_router.py exists.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from backend.data_loader import load_all
from backend.book_scenario import run_book_scenario


# ---------------------------------------------------------------------------
# Shared fixture: load the real CSV data set once for the session.
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@pytest.fixture(scope="module")
def real_data():
    """Load all CSVs from the data directory once per test session."""
    if not DATA_DIR.exists():
        pytest.skip(f"Data directory not found: {DATA_DIR}")
    return load_all(DATA_DIR)


# ---------------------------------------------------------------------------
# Helper: expected client count from clients.csv
# ---------------------------------------------------------------------------

def _expected_client_count(data: dict) -> int:
    return len(data["clients"])


# ---------------------------------------------------------------------------
# Test 9.3a: All clients appear in the result
# ---------------------------------------------------------------------------

def test_book_scenario_returns_all_clients(real_data: dict) -> None:
    """run_book_scenario must return one entry per client in clients.csv."""
    n_clients = _expected_client_count(real_data)
    results = run_book_scenario("hormuz-escalation", real_data)

    assert len(results) == n_clients, (
        f"Expected {n_clients} clients in book scenario, got {len(results)}"
    )

    result_ids = {r["client_id"] for r in results}
    expected_ids = set(real_data["clients"]["client_id"].astype(str).str.strip())
    assert result_ids == expected_ids, (
        f"Missing clients: {expected_ids - result_ids}\n"
        f"Extra clients: {result_ids - expected_ids}"
    )


# ---------------------------------------------------------------------------
# Test 9.3b: scenario_rank is a permutation of 1..n
# ---------------------------------------------------------------------------

def test_book_scenario_ranks_are_permutation(real_data: dict) -> None:
    """scenario_rank values must form a dense 1-based permutation with no gaps."""
    n_clients = _expected_client_count(real_data)
    results = run_book_scenario("hormuz-escalation", real_data)

    ranks = sorted(r["scenario_rank"] for r in results)
    assert ranks == list(range(1, n_clients + 1)), (
        f"scenario_rank is not a permutation of 1..{n_clients}: {ranks}"
    )


# ---------------------------------------------------------------------------
# Test 9.3c: Result completes within 3 seconds
# ---------------------------------------------------------------------------

def test_book_scenario_completes_within_3_seconds(real_data: dict) -> None:
    """The full 20-client computation must complete in < 3 seconds (Req 12.6)."""
    start = time.perf_counter()
    results = run_book_scenario("hormuz-escalation", real_data)
    elapsed = time.perf_counter() - start

    assert elapsed < 3.0, (
        f"Book scenario took {elapsed:.2f}s — exceeds the 3-second limit (Req 12.6)"
    )
    # Also make sure we got results (not an early empty return).
    assert len(results) > 0


# ---------------------------------------------------------------------------
# Test 9.3d: Result fields have the correct types and non-trivial values
# ---------------------------------------------------------------------------

def test_book_scenario_result_fields_have_correct_types(real_data: dict) -> None:
    """Each result dict must have the correct field types and sensible values."""
    results = run_book_scenario("tech-selloff", real_data)

    for row in results:
        assert isinstance(row["client_id"], str), f"client_id not str: {row}"
        assert isinstance(row["client_name"], str), f"client_name not str: {row}"
        assert isinstance(row["total_current_value_usd"], float), f"total_current not float: {row}"
        assert isinstance(row["total_shocked_value_usd"], float), f"total_shocked not float: {row}"
        assert isinstance(row["net_dollar_impact_usd"], float), f"net_impact not float: {row}"
        assert isinstance(row["net_pct_change"], float), f"net_pct_change not float: {row}"
        assert isinstance(row["ltv_breach"], bool), f"ltv_breach not bool: {row}"
        assert isinstance(row["scenario_rank"], int), f"scenario_rank not int: {row}"

        # Total values should be positive.
        assert row["total_current_value_usd"] >= 0.0
        assert row["total_shocked_value_usd"] >= 0.0

        # Scenario rank must be positive.
        assert row["scenario_rank"] >= 1


# ---------------------------------------------------------------------------
# Test 9.3e: Sorting invariant — LTV breach clients always rank first
# ---------------------------------------------------------------------------

def test_book_scenario_breach_clients_rank_first(real_data: dict) -> None:
    """All clients with ltv_breach=True must have lower scenario_rank than
    clients with ltv_breach=False (when both exist in the result set).
    """
    results = run_book_scenario("hormuz-escalation", real_data)

    breach_ranks = [r["scenario_rank"] for r in results if r["ltv_breach"]]
    no_breach_ranks = [r["scenario_rank"] for r in results if not r["ltv_breach"]]

    if breach_ranks and no_breach_ranks:
        assert max(breach_ranks) < min(no_breach_ranks), (
            f"Breach clients have ranks {sorted(breach_ranks)}; "
            f"non-breach clients have ranks {sorted(no_breach_ranks)}. "
            "Breach clients should always rank lower (i.e., more urgent)."
        )


# ---------------------------------------------------------------------------
# Test 9.3f: Tech-selloff scenario applies negative equity shock to all clients
# ---------------------------------------------------------------------------

def test_tech_selloff_produces_negative_net_impact_for_equity_heavy_clients(
    real_data: dict,
) -> None:
    """Under the tech-selloff scenario (Equity −8%, IT sector −20%), clients
    with material equity/tech holdings must show a negative net_dollar_impact_usd.
    """
    results = run_book_scenario("tech-selloff", real_data)

    # At least some clients should have a negative impact (losses from equity shock).
    negative_impact_clients = [r for r in results if r["net_dollar_impact_usd"] < 0]
    assert len(negative_impact_clients) > 0, (
        "Expected at least some clients to have negative net impact under tech-selloff"
    )


# ---------------------------------------------------------------------------
# Test 9.3g: All five named scenarios complete without errors
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("scenario_id", [
    "hormuz-escalation",
    "hormuz-de-escalation",
    "tech-selloff",
    "rate-shock",
    "gold-consolidation",
])
def test_all_named_scenarios_run_without_errors(real_data: dict, scenario_id: str) -> None:
    """Every named scenario must complete without raising an exception."""
    results = run_book_scenario(scenario_id, real_data)
    n_clients = _expected_client_count(real_data)
    assert len(results) == n_clients, (
        f"Scenario '{scenario_id}' returned {len(results)} clients, expected {n_clients}"
    )
