from __future__ import annotations

import pytest

from src.interpreter.validation import InterpretationValidationError, validate_interpretation


def test_nonexistent_fact_reference_is_rejected(packet_with_finding, valid_output_factory):
    output = valid_output_factory(packet_with_finding)
    output["observations"][0]["fact_ids"] = ["exposure_changes:F-NOT-REAL"]
    with pytest.raises(InterpretationValidationError, match="unsupported IDs"):
        validate_interpretation(output, packet_with_finding)


def test_nonexistent_evidence_reference_is_rejected(packet_with_finding, valid_output_factory):
    output = valid_output_factory(packet_with_finding)
    output["observations"][0]["evidence_ids"] = ["exposure_changes:E-NOT-REAL"]
    with pytest.raises(InterpretationValidationError, match="unsupported IDs"):
        validate_interpretation(output, packet_with_finding)


def test_observation_requires_fact_and_evidence_references(packet_with_finding, valid_output_factory):
    output = valid_output_factory(packet_with_finding)
    output["observations"][0]["fact_ids"] = []
    with pytest.raises(InterpretationValidationError, match="at least 1"):
        validate_interpretation(output, packet_with_finding)

