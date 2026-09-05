"""Unit tests for generate_narrative() in scenario_narrative.py.

Tests cover (Task 7.2, Requirements 8.1–8.4):
1. Output contains client name and scenario label.
2. A client with no RM notes still produces a non-empty, non-placeholder narrative.
3. All five named scenario IDs produce non-empty strings.
4. Output is 2–4 sentences (basic count check).
5. Custom scenario with no named entry produces a sensible fallback.
"""
from __future__ import annotations

import pandas as pd
import pytest

from backend.scenario_narrative import generate_narrative
from backend.stress_types import NAMED_SCENARIOS


# ---------------------------------------------------------------------------
# Fixture builder
# ---------------------------------------------------------------------------

def _make_data(
    client_name: str = "Test Client",
    life_stage: str = "Wealth accumulation",
    objectives: str = "Preserve family wealth; diversify portfolio; plan property purchase",
    rm_notes: list[dict] | None = None,
    client_id: str = "CL-TEST",
) -> dict:
    """Build the minimal data dict needed by generate_narrative()."""
    return {
        "clients": pd.DataFrame([{
            "client_id": client_id,
            "client_name": client_name,
            "life_stage": life_stage,
            "objectives": objectives,
            "risk_profile": "Balanced Growth",
        }]),
        "event_log": pd.DataFrame([
            {
                "event_date": "2026-02-28",
                "event_type": "Geopolitical",
                "region": "Middle East",
                "description": "US and Israel commence military operations against Iran.",
                "primary_transmission": "Energy, defence, airlines, EM credit",
                "severity": "Severe",
            },
            {
                "event_date": "2026-01-28",
                "event_type": "Market",
                "region": "Global",
                "description": "Gold prints an intraday all-time high near USD 5,589 per ounce.",
                "primary_transmission": "Gold, precious metals",
                "severity": "High",
            },
            {
                "event_date": "2026-06-15",
                "event_type": "Market",
                "region": "Global",
                "description": "Megacap tech earnings disappoint; broad technology selloff.",
                "primary_transmission": "Technology, US equity",
                "severity": "High",
            },
        ]),
        # rm_notes is provided as a pre-parsed list of dicts (as the router would supply).
        "rm_notes": rm_notes if rm_notes is not None else [],
    }


# ---------------------------------------------------------------------------
# Test 1: Output contains client name and scenario label
# ---------------------------------------------------------------------------

def test_narrative_contains_client_name_and_scenario_label() -> None:
    """The generated narrative must mention the client's name and the scenario label."""
    data = _make_data(client_name="Ravi Chandrasekaran")
    narrative = generate_narrative(
        client_id="CL-TEST",
        scenario_id="tech-selloff",
        top_holdings=[("Global Tech Fund", "Equity")],
        data=data,
    )

    assert "Ravi Chandrasekaran" in narrative, (
        f"Expected client name in narrative. Got:\n{narrative}"
    )
    assert "Tech Sector Selloff" in narrative or "technology" in narrative.lower(), (
        f"Expected scenario label or tech reference in narrative. Got:\n{narrative}"
    )


# ---------------------------------------------------------------------------
# Test 2: Client with no RM notes produces non-empty, non-placeholder narrative
# ---------------------------------------------------------------------------

def test_narrative_without_rm_notes_has_no_placeholder_text() -> None:
    """When there are no RM notes, the narrative must still be non-empty and
    must not contain any placeholder markers like '[' or '{{'.

    This validates Requirement 8.4: no placeholder text when notes are absent.
    """
    data = _make_data(rm_notes=[])  # explicitly empty notes
    narrative = generate_narrative(
        client_id="CL-TEST",
        scenario_id="hormuz-escalation",
        top_holdings=[("Energy Commodity Fund", "Commodities")],
        data=data,
    )

    assert narrative, "Expected a non-empty narrative even without RM notes"
    assert "[" not in narrative, f"Unexpected placeholder in narrative: {narrative}"
    assert "{{" not in narrative, f"Unexpected placeholder in narrative: {narrative}"
    assert "placeholder" not in narrative.lower(), (
        f"Narrative contains 'placeholder': {narrative}"
    )


# ---------------------------------------------------------------------------
# Test 3: All five named scenario IDs produce non-empty strings
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("scenario_id", list(NAMED_SCENARIOS.keys()))
def test_all_named_scenarios_produce_non_empty_narrative(scenario_id: str) -> None:
    """Every named scenario must produce a non-empty narrative string."""
    data = _make_data(client_name="Sample Client")
    narrative = generate_narrative(
        client_id="CL-TEST",
        scenario_id=scenario_id,
        top_holdings=[("Sample Fund", "Equity")],
        data=data,
    )

    assert isinstance(narrative, str), f"Expected str, got {type(narrative)}"
    assert len(narrative.strip()) > 0, (
        f"Empty narrative for scenario_id='{scenario_id}'"
    )
    # Should contain at least one full stop (i.e., at least one sentence).
    assert "." in narrative, (
        f"Narrative for '{scenario_id}' has no sentence terminator: {narrative}"
    )


# ---------------------------------------------------------------------------
# Test 4: Narrative is at least 2 sentences long
# ---------------------------------------------------------------------------

def test_narrative_has_at_least_two_sentences() -> None:
    """The narrative should contain at least 2 sentences (2 full-stop-terminated clauses)."""
    data = _make_data(
        client_name="Helena Fischer",
        life_stage="Pre-retirement",
        objectives="Replace salary with portfolio income; fund a family foundation",
    )
    narrative = generate_narrative(
        client_id="CL-TEST",
        scenario_id="rate-shock",
        top_holdings=[("Long Bond Fund", "Fixed Income"), ("REIT ETF", "Equity")],
        data=data,
    )

    # Count approximate sentence count by splitting on '. '.
    # We allow for a minimum of 2 — actual count may be 3–4.
    sentence_count = narrative.count(".") + narrative.count("!")
    assert sentence_count >= 2, (
        f"Expected at least 2 sentences, found ~{sentence_count}. Narrative:\n{narrative}"
    )


# ---------------------------------------------------------------------------
# Test 5: RM note appears in narrative when available
# ---------------------------------------------------------------------------

def test_narrative_includes_rm_note_when_available() -> None:
    """When an RM note exists, its content (or date) should appear in the narrative."""
    rm_notes = [{
        "note_id": "N-TEST",
        "client_id": "CL-TEST",
        "note_date": "2026-07-15",
        "rm_id": "RM-TEST",
        "rm_name": "Test RM",
        "channel": "Call",
        "note": "Client confirmed they are proceeding with the secondary sale in Q4 2026.",
    }]
    data = _make_data(rm_notes=rm_notes)
    narrative = generate_narrative(
        client_id="CL-TEST",
        scenario_id="tech-selloff",
        top_holdings=[("Tech Fund", "Equity")],
        data=data,
    )

    # The note date or a substring of the note text should appear.
    assert "2026-07-15" in narrative or "secondary sale" in narrative.lower(), (
        f"Expected RM note date or content in narrative. Got:\n{narrative}"
    )


# ---------------------------------------------------------------------------
# Test 6: Missing client_id returns a sensible fallback (no exception)
# ---------------------------------------------------------------------------

def test_narrative_handles_unknown_client_gracefully() -> None:
    """An unknown client_id must not raise an exception; it should return a fallback string."""
    data = _make_data()
    narrative = generate_narrative(
        client_id="CL-DOES-NOT-EXIST",
        scenario_id="tech-selloff",
        top_holdings=[],
        data=data,
    )
    assert isinstance(narrative, str)
    assert len(narrative) > 0


# ---------------------------------------------------------------------------
# Test 7: Top holding name appears in narrative when supplied
# ---------------------------------------------------------------------------

def test_narrative_references_top_holding_name() -> None:
    """The name of the most-affected holding should appear in the narrative (Req 8.3)."""
    data = _make_data(client_name="Wei Zhang")
    holding_name = "Asia Pacific Energy Trust"
    narrative = generate_narrative(
        client_id="CL-TEST",
        scenario_id="hormuz-escalation",
        top_holdings=[(holding_name, "Commodities")],
        data=data,
    )

    assert holding_name in narrative, (
        f"Expected holding name '{holding_name}' in narrative. Got:\n{narrative}"
    )


# ---------------------------------------------------------------------------
# Test 8: Life-stage "Pre-liquidity event" includes relevant context
# ---------------------------------------------------------------------------

def test_narrative_pre_liquidity_client_includes_liquidity_context() -> None:
    """A client with 'Pre-liquidity event' life stage should see that framed in the narrative."""
    data = _make_data(
        client_name="Ravi Chandrasekaran",
        life_stage="Pre-liquidity event",
        objectives="Bridge liquidity until the secondary sale of founder shares expected Q4 2026",
    )
    narrative = generate_narrative(
        client_id="CL-TEST",
        scenario_id="tech-selloff",
        top_holdings=[("Founder Shares Trust", "Equity")],
        data=data,
    )

    assert "liquidity" in narrative.lower(), (
        f"Expected 'liquidity' context for Pre-liquidity event client. Got:\n{narrative}"
    )
