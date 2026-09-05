from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.pipeline.evidence_packet import build_evidence_packet


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def block_network_in_offline_interpreter_tests(monkeypatch, request):
    if request.node.get_closest_marker("live_openai") is not None:
        return

    def fail_network(*args, **kwargs):
        raise AssertionError("offline interpreter tests must not make network calls")

    monkeypatch.setattr("httpx.Client.send", fail_network)


@pytest.fixture
def packet_with_finding(client_snapshot_0001):
    result = json.loads(
        (ROOT / "tests/contracts/fixtures/exposure_changes_result_v1.json").read_text(encoding="utf-8")
    )
    return build_evidence_packet(client_snapshot_0001, [result])


@pytest.fixture
def valid_output_factory():
    def build(packet: dict, *, model: str = "fake-model") -> dict:
        metadata = packet["packet_metadata"]
        observations = []
        questions = []
        if packet["findings"]:
            finding = packet["findings"][0]
            fact_ids = list(finding["fact_ids"])
            evidence_ids = list(finding["evidence_ids"])
            confidence = "high" if metadata["status"] == "complete" else "medium"
            observations = [{
                "observation_id": "OBS-001",
                "title": "Recorded exposure changed",
                "explanation": "The cited packet records an exposure change that warrants RM review.",
                "fact_ids": fact_ids,
                "evidence_ids": evidence_ids,
                "confidence": confidence,
                "uncertainty": None if confidence == "high" else "The packet is incomplete.",
            }]
            questions = [{
                "question_id": "Q-001",
                "question": "Was the recorded change intentional?",
                "observation_ids": ["OBS-001"],
            }]
            summary = "The packet contains one evidence-backed observation for RM review."
        else:
            summary = "No evidence-backed observation was available from the packet findings."
        return {
            "interpretation_metadata": {
                "result_type": "exposure_interpretation",
                "schema_version": "1.0.0",
                "prompt_name": "exposure_interpreter",
                "prompt_version": "1.0.0",
                "packet_type": metadata["packet_type"],
                "packet_schema_version": metadata["schema_version"],
                "client_id": metadata["client_id"],
                "as_of_date": metadata["as_of_date"],
                "comparison_date": metadata["comparison_date"],
                "model": model,
                "status": "complete",
            },
            "executive_summary": summary,
            "observations": observations,
            "questions_for_rm": questions,
            "limitations": ["Interpretation is limited to the supplied direct-exposure packet."],
            "warnings": ["Packet warnings require RM review."] if packet["warnings"] else [],
            "requires_rm_review": True,
        }

    return build


class SequenceInterpreterClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls: list[tuple[dict, str | None]] = []

    def interpret(self, packet: dict, validation_feedback: str | None = None) -> dict:
        self.calls.append((packet, validation_feedback))
        return self.responses.pop(0)


@pytest.fixture
def sequence_client_class():
    return SequenceInterpreterClient
