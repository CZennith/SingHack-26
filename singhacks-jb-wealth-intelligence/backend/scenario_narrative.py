"""Deterministic template-based scenario narrative engine.

Generates a 2–4 sentence client-specific narrative for each named scenario.
No LLM is used — the output is produced by pure Python f-string template
interpolation, drawing from:

  - clients.csv    (objectives, life_stage, client_name, risk_profile)
  - rm_notes.json  (most-recent note for the active client, if any)
  - event_log.csv  (description, primary_transmission, severity)
  - The scenario's own label and asset-class/sector shocks

Public API
----------
generate_narrative(client_id, scenario_id, top_holdings, data) -> str
    Returns a 2–4 sentence plain-English narrative suitable for the RM to
    read before a client call.  Never returns an empty string or a string
    containing "[placeholder]"-style text.

Requirements: 8.1, 8.2, 8.3, 8.4
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from .stress_types import NAMED_SCENARIOS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Life-stage keywords mapped to a short contextual phrase used in templates.
# The key is a substring match (lower-cased); the value is a human-readable
# label inserted into the narrative sentence.
_LIFE_STAGE_CONTEXT: dict[str, str] = {
    "pre-liquidity event": "upcoming liquidity event",
    "succession": "succession and estate planning horizon",
    "business sale": "planned business sale",
    "retirement": "retirement transition",
    "pre-retirement": "near-term retirement plans",
    "charitable foundation": "charitable foundation objectives",
    "property purchase": "planned property purchase",
    "family office formation": "family office formation timeline",
    "inherited": "recently inherited portfolio",
    "accumulation": "long-term wealth accumulation goals",
    "multi-generational": "multi-generational wealth transfer objectives",
}

# Scenario-specific opening phrases that reference the macro event clearly.
_SCENARIO_OPENER: dict[str, str] = {
    "hormuz-escalation": (
        "A military escalation in the Strait of Hormuz would send energy prices sharply higher "
        "while weighing on airline stocks and emerging-market credit."
    ),
    "hormuz-de-escalation": (
        "A de-escalation in the Strait of Hormuz and resumption of normal shipping flows "
        "would likely reverse recent energy gains and support airline valuations."
    ),
    "tech-selloff": (
        "A broad technology sector selloff — driven by stretched valuations and megacap "
        "earnings disappointments — would hit growth-oriented equity portfolios hardest."
    ),
    "rate-shock": (
        "A surprise Federal Reserve rate hike would reprice long-duration fixed income "
        "and weigh on rate-sensitive equities across the board."
    ),
    "gold-consolidation": (
        "After an extraordinary run to above USD 5,000 per ounce, a gold price correction "
        "would reduce the value of precious metals and commodity allocations."
    ),
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _text(value: Any) -> str:
    return "" if pd.isna(value) else str(value).strip()


def _life_stage_phrase(life_stage: str) -> str:
    """Return a short contextual phrase based on the client's life_stage string."""
    ls = (life_stage or "").lower()
    for keyword, phrase in _LIFE_STAGE_CONTEXT.items():
        if keyword in ls:
            return phrase
    # Fallback: use the life_stage field itself, lower-cased.
    return life_stage.lower() if life_stage else "investment objectives"


def _rm_note_sentence(rm_notes: list[dict[str, Any]], scenario_id: str) -> str:
    """Return a single sentence drawn from the most recent RM note, or '' if none."""
    if not rm_notes:
        return ""
    most_recent = rm_notes[0]
    note_text = (most_recent.get("note") or "").strip()
    note_date = (most_recent.get("note_date") or "").strip()
    if not note_text:
        return ""
    # Truncate to 120 chars and append ellipsis if needed.
    excerpt = note_text[:120] + ("..." if len(note_text) > 120 else "")
    return f"Your most recent note ({note_date}): \"{excerpt}\""


def _extract_key_objective(objectives: str) -> str:
    """Pull the first clause of the objectives field (up to the first semicolon)."""
    if not objectives:
        return "their stated objectives"
    first_clause = objectives.split(";")[0].strip()
    # Capitalise first letter.
    return first_clause[:1].lower() + first_clause[1:] if first_clause else objectives


def _load_rm_notes(data: Mapping[str, Any], client_id: str) -> list[dict[str, Any]]:
    """Return RM notes for *client_id* sorted by note_date descending.

    The data dict may contain a 'rm_notes' key already parsed as a list of
    dicts (loaded by data_loader), or it may not include rm_notes at all
    (unit-test data dicts typically omit it).
    """
    raw_notes = data.get("rm_notes", [])
    if isinstance(raw_notes, pd.DataFrame):
        # data_loader.load_all() loads only CSVs; rm_notes is JSON so it will
        # not appear as a DataFrame — this branch is a safety net.
        notes = raw_notes.to_dict("records")
    elif isinstance(raw_notes, list):
        notes = raw_notes
    else:
        notes = []

    client_notes = [n for n in notes if n.get("client_id") == client_id]
    # Sort descending by note_date (ISO string sort works correctly).
    client_notes.sort(key=lambda n: n.get("note_date", ""), reverse=True)
    return client_notes


def _get_event_description(
    data: Mapping[str, Any],
    scenario_id: str,
) -> str:
    """Pull the event description from event_log.csv matching the scenario's event_log_ref date."""
    scenario = NAMED_SCENARIOS.get(scenario_id, {})
    event_log_ref = scenario.get("event_log_ref")
    if not event_log_ref:
        return ""

    event_log = data.get("event_log")
    if event_log is None or (isinstance(event_log, pd.DataFrame) and event_log.empty):
        return ""

    if isinstance(event_log, pd.DataFrame):
        matching = event_log[
            event_log["event_date"].astype(str).str.startswith(str(event_log_ref))
        ]
        if not matching.empty:
            return _text(matching.iloc[0].get("description", ""))

    return ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_narrative(
    client_id: str,
    scenario_id: str,
    top_holdings: list[tuple[str, str]],
    data: Mapping[str, Any],
) -> str:
    """Generate a 2–4 sentence plain-English scenario narrative for the RM.

    Parameters
    ----------
    client_id:
        The active client's ID string (e.g. "CL-0002").
    scenario_id:
        One of the NAMED_SCENARIOS keys (e.g. "tech-selloff") or "custom".
    top_holdings:
        List of (instrument_name, asset_class) tuples for the top 1–3 most
        affected holdings from the macro shock result.  Pass an empty list
        when no shock has been run yet.
    data:
        The data dict returned by data_loader.load_all() — must contain at
        least 'clients' and optionally 'event_log'.  'rm_notes' may be
        pre-populated as a list of dicts by the router.

    Returns
    -------
    A non-empty string of 2–4 sentences in plain English.
    """
    # -----------------------------------------------------------------
    # 1. Load client row.
    # -----------------------------------------------------------------
    clients_df = data.get("clients")
    if clients_df is None or (isinstance(clients_df, pd.DataFrame) and clients_df.empty):
        return (
            f"Scenario '{NAMED_SCENARIOS.get(scenario_id, {}).get('label', scenario_id)}' "
            "has been run. Please review the stress test results below."
        )

    client_rows = clients_df[clients_df["client_id"].eq(client_id)]
    if client_rows.empty:
        return (
            f"Scenario '{NAMED_SCENARIOS.get(scenario_id, {}).get('label', scenario_id)}' "
            "has been run. Please review the stress test results below."
        )

    client = client_rows.iloc[0]
    client_name = _text(client.get("client_name", "The client"))
    life_stage = _text(client.get("life_stage", ""))
    objectives = _text(client.get("objectives", ""))
    risk_profile = _text(client.get("risk_profile", ""))

    # -----------------------------------------------------------------
    # 2. Scenario metadata.
    # -----------------------------------------------------------------
    scenario = NAMED_SCENARIOS.get(scenario_id, {})
    scenario_label = scenario.get("label", scenario_id)

    # -----------------------------------------------------------------
    # 3. Context phrase from life_stage.
    # -----------------------------------------------------------------
    life_phrase = _life_stage_phrase(life_stage)

    # -----------------------------------------------------------------
    # 4. Opener sentence — macro event framing.
    # -----------------------------------------------------------------
    opener = _SCENARIO_OPENER.get(
        scenario_id,
        f"The {scenario_label} scenario introduces significant market uncertainty "
        "relevant to your client's portfolio.",
    )

    # -----------------------------------------------------------------
    # 5. Client-relevance sentence — ties the macro event to the client.
    # -----------------------------------------------------------------
    key_objective = _extract_key_objective(objectives)
    relevance_sentence = (
        f"This scenario is particularly relevant for {client_name} given their "
        f"{life_phrase} — {key_objective}."
    )

    # -----------------------------------------------------------------
    # 6. Holding-specific sentence — name the most affected holding.
    # -----------------------------------------------------------------
    holding_sentence = ""
    if top_holdings:
        top_name, top_ac = top_holdings[0][0], top_holdings[0][1]
        holding_sentence = (
            f"Your largest affected position, {top_name} "
            f"({top_ac}), would bear the highest dollar impact under this scenario."
        )

    # -----------------------------------------------------------------
    # 7. RM note sentence (if available) — or objectives fallback (Req 8.4).
    # -----------------------------------------------------------------
    rm_notes = _load_rm_notes(data, client_id)
    note_sentence = _rm_note_sentence(rm_notes, scenario_id)

    if not note_sentence:
        # No RM notes: fall back to objectives sentence (Req 8.4 — no placeholder text).
        note_sentence = (
            f"{client_name}'s goal to {key_objective} "
            f"makes this scenario worth reviewing carefully."
        )

    # -----------------------------------------------------------------
    # 8. Assemble narrative (2–4 sentences).
    # -----------------------------------------------------------------
    parts = [opener, relevance_sentence]
    if holding_sentence:
        parts.append(holding_sentence)
    parts.append(note_sentence)

    return " ".join(parts)
