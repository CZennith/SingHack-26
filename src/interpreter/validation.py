"""Independent input and post-response validation for LLM interpretation."""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, ValidationError

from ..pipeline.packet_models import PACKET_SCHEMA_VERSION, PACKET_TYPE
from ..pipeline.packet_validation import PacketValidationError, validate_packet
from .models import ExposureInterpretation


RECOMMENDATION_FIELDS = {
    "recommended_action", "recommended_trade", "recommendation", "trade_instruction",
    "buy_sell_signal", "portfolio_action",
}
_TRADE_LANGUAGE = re.compile(
    r"\b(?:buy|buying|sell|selling|hold|switch|switching|rebalance|rebalancing|hedge|hedging|borrow|borrowing|purchase|liquidate)\b|"
    r"\b(?:increase|reduce|decrease|adjust|add|remove)\s+(?:the\s+)?(?:position|holding|allocation|exposure)\b|"
    r"\bchange\s+(?:the\s+)?mandate\b|"
    r"\b(?:suitable|unsuitable|recommend|recommends|recommended|recommending|recommendation)\b",
    re.IGNORECASE,
)
_CAUSAL_LANGUAGE = re.compile(
    r"\b(?:caused|because of|due to|resulted from|driven by|led to|attribut(?:e|ed|able) to)\b",
    re.IGNORECASE,
)
_VALUATION_LAG_ERROR = re.compile(
    r"(?:private[- ]market|valuation)\s+(?:valuation\s+)?lag.{0,80}\b(?:data\s+)?error\b|"
    r"\b(?:data\s+)?error\b.{0,80}(?:private[- ]market|valuation)\s+(?:valuation\s+)?lag",
    re.IGNORECASE,
)
_ISO_DATE_IN_TEXT = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_NUMBER = re.compile(r"(?<![A-Za-z0-9_.])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:\s*%)?")


class InterpreterError(Exception):
    """Base error for the evidence-bound interpretation layer."""


class InterpreterInputError(InterpreterError, ValueError):
    """The supplied object is not a supported evidence packet."""


class InterpretationValidationError(InterpreterError, ValueError):
    """A model response violates the interpretation contract or evidence boundary."""


class InterpretationRetryExhausted(InterpretationValidationError):
    """Both the initial response and one corrective retry were invalid."""


def validate_interpreter_packet(packet: dict) -> dict:
    """Validate and normalize the only supported interpreter input."""
    try:
        validated = validate_packet(packet)
    except (PacketValidationError, TypeError, ValueError) as exc:
        raise InterpreterInputError(f"invalid exposure-change evidence packet: {exc}") from exc
    normalized = validated.to_dict()
    metadata = normalized["packet_metadata"]
    governance = normalized["governance"]
    if metadata["packet_type"] != PACKET_TYPE:
        raise InterpreterInputError(f"unsupported packet type {metadata['packet_type']!r}")
    if not metadata["client_id"]:
        raise InterpreterInputError("packet client_id is required")
    if not governance["requires_rm_review"]:
        raise InterpreterInputError("packet must require RM review")
    if governance["recommendations_allowed"]:
        raise InterpreterInputError("packet must prohibit recommendations")
    if not governance["llm_interpretation_allowed"]:
        raise InterpreterInputError("packet does not allow LLM interpretation")
    return normalized


def _scan_recommendation_fields(value: Any, path: str = "interpretation") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in RECOMMENDATION_FIELDS:
                raise InterpretationValidationError(f"{path}.{key}: recommendation fields are prohibited")
            _scan_recommendation_fields(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan_recommendation_fields(item, f"{path}[{index}]")


def _authored_text(output: ExposureInterpretation) -> list[tuple[str, str]]:
    texts = [("executive_summary", output.executive_summary)]
    for index, observation in enumerate(output.observations):
        texts.extend((
            (f"observations[{index}].title", observation.title),
            (f"observations[{index}].explanation", observation.explanation),
        ))
    for index, question in enumerate(output.questions_for_rm):
        texts.append((f"questions_for_rm[{index}].question", question.question))
    texts.extend((f"limitations[{index}]", text) for index, text in enumerate(output.limitations))
    texts.extend((f"warnings[{index}]", text) for index, text in enumerate(output.warnings))
    return texts


def _numeric_claims(text: str) -> set[Decimal]:
    without_dates = _ISO_DATE_IN_TEXT.sub("", text)
    claims: set[Decimal] = set()
    for match in _NUMBER.finditer(without_dates):
        token = match.group(0).strip().removesuffix("%").replace(",", "")
        try:
            claims.add(Decimal(token))
        except InvalidOperation:
            continue
    return claims


def _collect_numbers(value: Any, supported: set[Decimal]) -> None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        supported.add(Decimal(str(value)))
    elif isinstance(value, dict):
        for item in value.values():
            _collect_numbers(item, supported)
    elif isinstance(value, list):
        for item in value:
            _collect_numbers(item, supported)


def _supported_numbers(observation, facts: dict[str, dict], evidence: dict[str, dict]) -> set[Decimal]:
    supported: set[Decimal] = set()
    for fact_id in observation.fact_ids:
        _collect_numbers(facts[fact_id], supported)
    for evidence_id in observation.evidence_ids:
        _collect_numbers(evidence[evidence_id], supported)
    return supported


def validate_interpretation(payload: dict | BaseModel, packet: dict) -> ExposureInterpretation:
    """Post-validate structured output against its exact source packet."""
    normalized_packet = validate_interpreter_packet(packet)
    raw = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    if not isinstance(raw, dict):
        raise InterpretationValidationError("interpretation must be an object")
    _scan_recommendation_fields(raw)
    try:
        output = ExposureInterpretation.model_validate(raw)
    except ValidationError as exc:
        raise InterpretationValidationError(f"invalid interpretation output: {exc}") from exc

    metadata = output.interpretation_metadata
    packet_metadata = normalized_packet["packet_metadata"]
    expected = {
        "client_id": packet_metadata["client_id"],
        "as_of_date": packet_metadata["as_of_date"],
        "comparison_date": packet_metadata["comparison_date"],
        "packet_type": packet_metadata["packet_type"],
        "packet_schema_version": packet_metadata["schema_version"],
    }
    for field, expected_value in expected.items():
        if getattr(metadata, field) != expected_value:
            raise InterpretationValidationError(
                f"interpretation_metadata.{field} must match packet value {expected_value!r}"
            )
    if metadata.packet_schema_version != PACKET_SCHEMA_VERSION:
        raise InterpretationValidationError("unsupported packet schema version")

    facts = {item["fact_id"]: item for item in normalized_packet["facts"]}
    evidence = {item["evidence_id"]: item for item in normalized_packet["evidence"]}
    observation_ids = {item.observation_id for item in output.observations}
    if not normalized_packet["findings"] and output.observations:
        raise InterpretationValidationError("packets without findings cannot produce observations")

    for index, observation in enumerate(output.observations):
        unknown_facts = sorted(set(observation.fact_ids) - set(facts))
        if unknown_facts:
            raise InterpretationValidationError(
                f"observations[{index}].fact_ids contain unsupported IDs: {', '.join(unknown_facts)}"
            )
        unknown_evidence = sorted(set(observation.evidence_ids) - set(evidence))
        if unknown_evidence:
            raise InterpretationValidationError(
                f"observations[{index}].evidence_ids contain unsupported IDs: {', '.join(unknown_evidence)}"
            )
        linked_evidence = {
            evidence_id
            for fact_id in observation.fact_ids
            for evidence_id in facts[fact_id].get("evidence_ids", [])
        }
        linked_evidence.update(
            evidence_id
            for finding in normalized_packet["findings"]
            if set(observation.fact_ids).intersection(finding["fact_ids"])
            for evidence_id in finding["evidence_ids"]
        )
        if linked_evidence and not set(observation.evidence_ids).issubset(linked_evidence):
            raise InterpretationValidationError(
                f"observations[{index}].evidence_ids are not linked to the cited facts"
            )
        claims = _numeric_claims(observation.title + " " + observation.explanation)
        unsupported = claims - _supported_numbers(observation, facts, evidence)
        if unsupported:
            rendered = ", ".join(str(value) for value in sorted(unsupported))
            raise InterpretationValidationError(
                f"observations[{index}] contains numerical claims unsupported by cited facts: {rendered}"
            )
        if _CAUSAL_LANGUAGE.search(observation.title + " " + observation.explanation):
            raise InterpretationValidationError(
                f"observations[{index}] contains an unsupported causal claim"
            )

    for index, question in enumerate(output.questions_for_rm):
        unknown = sorted(set(question.observation_ids) - observation_ids)
        if unknown:
            raise InterpretationValidationError(
                f"questions_for_rm[{index}].observation_ids contain unsupported IDs: {', '.join(unknown)}"
            )

    for path, text in _authored_text(output):
        if _TRADE_LANGUAGE.search(text):
            raise InterpretationValidationError(f"{path} contains prohibited recommendation or trade language")
        if not path.startswith("questions_for_rm") and _CAUSAL_LANGUAGE.search(text):
            raise InterpretationValidationError(f"{path} contains an unsupported causal claim")
        if _VALUATION_LAG_ERROR.search(text):
            packet_classifies_lag_as_error = any(
                "error" in str(warning.get("warning_type", "")).lower()
                and "lag" in json.dumps(warning, sort_keys=True).lower()
                for warning in normalized_packet["warnings"]
            )
            if not packet_classifies_lag_as_error:
                raise InterpretationValidationError(
                    f"{path} incorrectly classifies expected valuation lag as a data error"
                )

    if packet_metadata["status"] != "complete":
        if not output.limitations:
            raise InterpretationValidationError("partial or blocked packets require an explicit limitation")
        if any(item.confidence == "high" for item in output.observations):
            raise InterpretationValidationError("partial or blocked packets cannot produce high-confidence observations")
    if (normalized_packet["warnings"] or normalized_packet["assumptions"]) and not (output.warnings or output.limitations):
        raise InterpretationValidationError("packet warnings and assumptions require an output warning or limitation")

    try:
        json.loads(output.model_dump_json())
    except (TypeError, ValueError) as exc:
        raise InterpretationValidationError(f"interpretation is not JSON-serializable: {exc}") from exc
    return output
