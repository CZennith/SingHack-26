from __future__ import annotations

import copy

import pytest
from jsonschema import Draft202012Validator

from src.interpreter.models import ExposureInterpretation
from src.interpreter.validation import InterpretationValidationError, validate_interpretation


@pytest.mark.parametrize("field", ["client_id", "as_of_date", "comparison_date", "packet_type", "packet_schema_version"])
def test_packet_metadata_mismatch_is_rejected(packet_with_finding, valid_output_factory, field):
    output = valid_output_factory(packet_with_finding)
    output["interpretation_metadata"][field] = "wrong"
    with pytest.raises(InterpretationValidationError, match=field):
        validate_interpretation(output, packet_with_finding)


def test_unexpected_fields_and_duplicate_ids_are_rejected(packet_with_finding, valid_output_factory):
    output = valid_output_factory(packet_with_finding)
    output["recommended_action"] = "none"
    with pytest.raises(InterpretationValidationError, match="recommendation fields"):
        validate_interpretation(output, packet_with_finding)

    output = valid_output_factory(packet_with_finding)
    output["observations"].append(copy.deepcopy(output["observations"][0]))
    with pytest.raises(InterpretationValidationError, match="unique"):
        validate_interpretation(output, packet_with_finding)


def test_pydantic_contract_emits_a_valid_strict_json_schema():
    schema = ExposureInterpretation.model_json_schema()
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False


@pytest.mark.parametrize(
    "statement",
    [
        "The RM should buy this asset.",
        "Sell the position.",
        "The client could switch holdings.",
        "Rebalance the allocation.",
        "Hedge the exposure.",
        "Increase the position.",
        "Reduce the position.",
        "This portfolio is unsuitable.",
    ],
)
def test_recommendation_and_trade_language_is_rejected(packet_with_finding, valid_output_factory, statement):
    output = valid_output_factory(packet_with_finding)
    output["observations"][0]["explanation"] = statement
    with pytest.raises(InterpretationValidationError, match="prohibited"):
        validate_interpretation(output, packet_with_finding)


def test_disguised_advice_in_rm_question_is_rejected(packet_with_finding, valid_output_factory):
    output = valid_output_factory(packet_with_finding)
    output["questions_for_rm"][0]["question"] = "Should the client rebalance immediately?"
    with pytest.raises(InterpretationValidationError, match="prohibited"):
        validate_interpretation(output, packet_with_finding)


def test_unsupported_numerical_claim_is_rejected(packet_with_finding, valid_output_factory):
    output = valid_output_factory(packet_with_finding)
    output["observations"][0]["explanation"] = "The cited exposure changed by 987654 percent."
    with pytest.raises(InterpretationValidationError, match="numerical claims"):
        validate_interpretation(output, packet_with_finding)


def test_supported_exact_numerical_claim_is_accepted(packet_with_finding, valid_output_factory):
    output = valid_output_factory(packet_with_finding)
    fact = packet_with_finding["facts"][0]
    output["observations"][0]["explanation"] = f"The cited change was {fact['change_weight_pp']} percentage points."
    assert validate_interpretation(output, packet_with_finding).observations


def test_unsupported_causal_claim_is_rejected(packet_with_finding, valid_output_factory):
    output = valid_output_factory(packet_with_finding)
    output["observations"][0]["explanation"] = "The change was caused by a market event."
    with pytest.raises(InterpretationValidationError, match="causal"):
        validate_interpretation(output, packet_with_finding)


def test_expected_private_market_valuation_lag_is_not_called_a_data_error(
    packet_with_finding, valid_output_factory
):
    output = valid_output_factory(packet_with_finding)
    output["limitations"][0] = "Private-market valuation lag is a data error."
    with pytest.raises(InterpretationValidationError, match="valuation lag"):
        validate_interpretation(output, packet_with_finding)


def test_question_must_reference_existing_observation(packet_with_finding, valid_output_factory):
    output = valid_output_factory(packet_with_finding)
    output["questions_for_rm"][0]["observation_ids"] = ["OBS-MISSING"]
    with pytest.raises(InterpretationValidationError, match="unsupported IDs"):
        validate_interpretation(output, packet_with_finding)
