from __future__ import annotations

import copy
import json

import pytest

from src.interpreter.interpreter import interpret_exposure_packet, main
from src.interpreter.openai_client import OpenAIStructuredOutputError
from src.interpreter.validation import (
    InterpreterInputError,
    InterpretationRetryExhausted,
    validate_interpretation,
)
from src.output_paths import interpretation_output_path
from src.pipeline.evidence_packet import build_evidence_packet


def test_valid_interpretation_is_validated_and_requires_rm_review(
    packet_with_finding, valid_output_factory, sequence_client_class
):
    client = sequence_client_class(valid_output_factory(packet_with_finding))
    result = interpret_exposure_packet(packet_with_finding, client)
    assert result["interpretation_metadata"]["client_id"] == "CL-0001"
    assert result["observations"][0]["fact_ids"] == ["exposure_changes:F-001"]
    assert result["requires_rm_review"] is True
    assert len(client.calls) == 1


def test_invalid_packet_blocks_client_call(packet_with_finding, valid_output_factory, sequence_client_class):
    invalid = copy.deepcopy(packet_with_finding)
    invalid["governance"]["requires_rm_review"] = False
    client = sequence_client_class(valid_output_factory(packet_with_finding))
    with pytest.raises(InterpreterInputError):
        interpret_exposure_packet(invalid, client)
    assert client.calls == []


def test_raw_snapshot_and_calculator_result_are_rejected_before_call(
    client_snapshot_0001, sequence_client_class
):
    client = sequence_client_class({})
    with pytest.raises(InterpreterInputError):
        interpret_exposure_packet(client_snapshot_0001, client)
    assert client.calls == []


def test_packet_without_findings_has_no_fabricated_observations(
    client_snapshot_0001, valid_output_factory, sequence_client_class
):
    packet = build_evidence_packet(client_snapshot_0001, [])
    client = sequence_client_class(valid_output_factory(packet))
    result = interpret_exposure_packet(packet, client)
    assert result["observations"] == []
    assert result["questions_for_rm"] == []
    assert "No evidence-backed observation" in result["executive_summary"]


def test_partial_packet_requires_limitations_and_caps_confidence(
    packet_with_finding, valid_output_factory, sequence_client_class
):
    packet = copy.deepcopy(packet_with_finding)
    packet["packet_metadata"]["status"] = "partial"
    valid = valid_output_factory(packet)
    result = interpret_exposure_packet(packet, sequence_client_class(valid))
    assert result["limitations"]
    assert result["observations"][0]["confidence"] == "medium"
    assert result["observations"][0]["uncertainty"]


def test_one_invalid_response_is_retried_once_with_feedback(
    packet_with_finding, valid_output_factory, sequence_client_class
):
    invalid = valid_output_factory(packet_with_finding)
    invalid["interpretation_metadata"]["client_id"] = "WRONG"
    valid = valid_output_factory(packet_with_finding)
    client = sequence_client_class(invalid, valid)
    result = interpret_exposure_packet(packet_with_finding, client)
    assert result["interpretation_metadata"]["client_id"] == "CL-0001"
    assert len(client.calls) == 2
    assert client.calls[0][1] is None
    assert "client_id" in client.calls[1][1]


def test_two_invalid_responses_fail_after_one_retry(
    packet_with_finding, valid_output_factory, sequence_client_class
):
    invalid = valid_output_factory(packet_with_finding)
    invalid["interpretation_metadata"]["client_id"] = "WRONG"
    client = sequence_client_class(copy.deepcopy(invalid), copy.deepcopy(invalid))
    with pytest.raises(InterpretationRetryExhausted, match="one retry"):
        interpret_exposure_packet(packet_with_finding, client)
    assert len(client.calls) == 2


def test_invalid_structured_output_is_retried_but_transport_errors_are_not(
    packet_with_finding, valid_output_factory
):
    class StructuredRetryClient:
        def __init__(self):
            self.calls = 0

        def interpret(self, packet, validation_feedback=None):
            self.calls += 1
            if self.calls == 1:
                raise OpenAIStructuredOutputError("structured output did not parse")
            assert validation_feedback
            return valid_output_factory(packet)

    client = StructuredRetryClient()
    result = interpret_exposure_packet(packet_with_finding, client)
    assert result["interpretation_metadata"]["client_id"] == "CL-0001"
    assert client.calls == 2


def test_valid_interpretation_json_round_trip(
    packet_with_finding, valid_output_factory, sequence_client_class
):
    first = interpret_exposure_packet(
        packet_with_finding, sequence_client_class(valid_output_factory(packet_with_finding))
    )
    second = json.loads(json.dumps(first, allow_nan=False))
    assert validate_interpretation(second, packet_with_finding).model_dump(mode="json") == first


def test_cli_writes_canonical_atomic_output_under_tmp_path(
    tmp_path, monkeypatch, capsys, packet_with_finding, valid_output_factory, sequence_client_class
):
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet_with_finding), encoding="utf-8")
    fake = sequence_client_class(valid_output_factory(packet_with_finding))
    monkeypatch.setattr(
        "src.interpreter.interpreter.OpenAIInterpreterClient.from_environment",
        lambda: fake,
    )
    output_root = tmp_path / "generated"
    assert main(["--packet", str(packet_path), "--output-root", str(output_root)]) == 0
    output = interpretation_output_path(
        output_root, "CL-0001", "exposure_change_review", "2026-06-30", "2026-08-26"
    )
    assert output.is_file()
    assert str(output.resolve()) in capsys.readouterr().out
    validate_interpretation(json.loads(output.read_text(encoding="utf-8")), packet_with_finding)
