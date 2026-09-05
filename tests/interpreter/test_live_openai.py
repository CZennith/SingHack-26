from __future__ import annotations

import copy
import os

import pytest

from src.interpreter.openai_client import OpenAIInterpreterClient
from src.interpreter.validation import validate_interpretation, validate_interpreter_packet


@pytest.mark.live_openai
@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_OPENAI") != "1" or not os.environ.get("OPENAI_API_KEY"),
    reason="requires explicit RUN_LIVE_OPENAI=1 and OPENAI_API_KEY",
)
def test_one_sanitized_live_openai_response(packet_with_finding):
    packet = copy.deepcopy(packet_with_finding)
    old_client = packet["packet_metadata"]["client_id"]
    new_client = "SANITIZED-CLIENT"
    packet["packet_metadata"]["client_id"] = new_client
    packet["client_context"] = {
        "client_id": new_client,
        "base_currency": "USD",
        "risk_profile": None,
        "risk_tolerance_score": None,
        "investment_horizon_years": None,
        "liquidity_needs": None,
        "objectives": None,
        "life_stage": None,
    }
    for fact in packet["facts"]:
        fact["scope"]["client_id"] = new_client
    for evidence in packet["evidence"]:
        if evidence["source_keys"].get("client_id") == old_client:
            evidence["source_keys"]["client_id"] = new_client
    packet["warnings"] = []
    packet = validate_interpreter_packet(packet)

    # Deliberately call the adapter once rather than the retrying orchestrator.
    output = OpenAIInterpreterClient.from_environment().interpret(packet)
    validate_interpretation(output, packet)
