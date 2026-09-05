"""Strict validation for the evidence-packet envelope."""

from __future__ import annotations

import json
import math
import re
from datetime import date
from typing import Any

from ..contracts.validation import validate_result
from .packet_models import (
    ALLOWED_PACKET_STATUSES,
    ALLOWED_PACKET_TYPES,
    EvidencePacket,
    PacketGovernance,
    PacketMetadata,
    PACKET_SCHEMA_VERSION,
    PACKET_VERSION,
)


SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PACKET_KEYS = {"packet_metadata", "client_context", "facts", "findings", "evidence", "warnings", "assumptions", "governance"}
METADATA_KEYS = {"packet_type", "schema_version", "packet_version", "client_id", "as_of_date", "comparison_date", "period_start", "period_end", "input_snapshot_schema_version", "input_snapshot_calculation_version", "included_calculators", "status"}
CONTEXT_KEYS = {"client_id", "base_currency", "risk_profile", "risk_tolerance_score", "investment_horizon_years", "liquidity_needs", "objectives", "life_stage"}
GOVERNANCE_KEYS = {"requires_rm_review", "recommendations_allowed", "llm_interpretation_allowed", "source_data_is_authoritative"}
RECOMMENDATION_FIELDS = {"recommended_action", "recommended_trade", "buy_sell_signal", "portfolio_action"}


class PacketValidationError(ValueError):
    """One or more packet fields violate the packet contract."""


class UnsupportedPacketType(PacketValidationError):
    """No v1 packet builder or validator exists for the supplied type."""


def _error(path: str, message: str) -> PacketValidationError:
    return PacketValidationError(f"{path}: {message}")


def _object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _error(path, "must be an object")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise _error(path, "must be an array")
    return value


def _strict_keys(value: dict[str, Any], required: set[str], optional: set[str], path: str) -> None:
    missing = sorted(required - set(value))
    unknown = sorted(set(value) - required - optional)
    if missing:
        raise _error(path, f"missing required field(s): {', '.join(missing)}")
    if unknown:
        raise _error(path, f"unexpected field(s): {', '.join(unknown)}")


def _string(value: Any, path: str, *, non_empty: bool = False) -> str:
    if not isinstance(value, str) or (non_empty and not value.strip()):
        raise _error(path, "must be a string" + (" and must be non-empty" if non_empty else ""))
    return value


def _semver(value: Any, path: str) -> str:
    value = _string(value, path, non_empty=True)
    if not SEMVER.fullmatch(value):
        raise _error(path, "must use semantic version format MAJOR.MINOR.PATCH")
    return value


def _date(value: Any, path: str) -> str:
    value = _string(value, path)
    if not ISO_DATE.fullmatch(value):
        raise _error(path, "must be an ISO date in YYYY-MM-DD format")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise _error(path, "must be a real calendar date") from exc
    if parsed.isoformat() != value:
        raise _error(path, "must be an ISO date in YYYY-MM-DD format")
    return value


def _bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise _error(path, "must be a boolean")
    return value


def _json_compatible(value: Any, path: str) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise _error(path, "must not contain NaN or Infinity")
        return value
    if isinstance(value, list):
        return [_json_compatible(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if isinstance(value, dict):
        return {str(key): _json_compatible(item, f"{path}.{key}") for key, item in value.items()}
    raise _error(path, "must be JSON-compatible")


def _ids(items: list[Any], path: str) -> tuple[str, ...]:
    result = [_string(item, f"{path}[{index}]", non_empty=True) for index, item in enumerate(items)]
    duplicate_ids = sorted({item for item in result if result.count(item) > 1})
    if duplicate_ids:
        raise _error(path, f"IDs must be unique; duplicates: {', '.join(duplicate_ids)}")
    return tuple(result)


def _scan_for_recommendations(value: Any, path: str = "packet") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in RECOMMENDATION_FIELDS:
                raise _error(f"{path}.{key}", "recommendation fields are prohibited in packet v1.0.0")
            _scan_for_recommendations(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan_for_recommendations(item, f"{path}[{index}]")


def _validate_metadata(payload: Any) -> PacketMetadata:
    value = _object(payload, "packet_metadata")
    _strict_keys(value, METADATA_KEYS, set(), "packet_metadata")
    packet_type = _string(value["packet_type"], "packet_metadata.packet_type", non_empty=True)
    if packet_type not in ALLOWED_PACKET_TYPES:
        raise UnsupportedPacketType(f"packet_metadata.packet_type: unsupported packet type {packet_type!r}")
    if value["schema_version"] != PACKET_SCHEMA_VERSION:
        raise _error("packet_metadata.schema_version", f"unsupported version {value['schema_version']!r}")
    if value["packet_version"] != PACKET_VERSION:
        raise _error("packet_metadata.packet_version", f"unsupported version {value['packet_version']!r}")
    client_id = _string(value["client_id"], "packet_metadata.client_id", non_empty=True)
    as_of = _date(value["as_of_date"], "packet_metadata.as_of_date")
    comparison = _date(value["comparison_date"], "packet_metadata.comparison_date")
    period_start = _date(value["period_start"], "packet_metadata.period_start")
    period_end = _date(value["period_end"], "packet_metadata.period_end")
    if comparison > as_of:
        raise _error("packet_metadata.comparison_date", "must not be later than as_of_date")
    if period_start > period_end:
        raise _error("packet_metadata", "period_start must be on or before period_end")
    calculators = _list(value["included_calculators"], "packet_metadata.included_calculators")
    parsed_calculators: list[dict[str, str]] = []
    for index, calculator in enumerate(calculators):
        item = _object(calculator, f"packet_metadata.included_calculators[{index}]")
        _strict_keys(item, {"name", "version"}, set(), f"packet_metadata.included_calculators[{index}]")
        name = _string(item["name"], f"packet_metadata.included_calculators[{index}].name", non_empty=True)
        if name != "exposure_changes":
            raise _error(f"packet_metadata.included_calculators[{index}].name", "only 'exposure_changes' is supported by packet v1.0.0")
        parsed_calculators.append({
            "name": name,
            "version": _semver(item["version"], f"packet_metadata.included_calculators[{index}].version"),
        })
    if len({(item["name"], item["version"]) for item in parsed_calculators}) != len(parsed_calculators):
        raise _error("packet_metadata.included_calculators", "calculator entries must be unique")
    status = _string(value["status"], "packet_metadata.status")
    if status not in ALLOWED_PACKET_STATUSES:
        raise _error("packet_metadata.status", f"must be one of {', '.join(ALLOWED_PACKET_STATUSES)}")
    return PacketMetadata(
        packet_type, value["schema_version"], value["packet_version"], client_id,
        as_of, comparison, period_start, period_end,
        _semver(value["input_snapshot_schema_version"], "packet_metadata.input_snapshot_schema_version"),
        _semver(value["input_snapshot_calculation_version"], "packet_metadata.input_snapshot_calculation_version"),
        tuple(parsed_calculators), status,
    )


def _validate_context(payload: Any, metadata: PacketMetadata) -> dict[str, Any]:
    value = _object(payload, "client_context")
    _strict_keys(value, CONTEXT_KEYS, set(), "client_context")
    if value["client_id"] != metadata.client_id:
        raise _error("client_context.client_id", "must match packet_metadata.client_id")
    for key in ("client_id", "base_currency", "risk_profile", "liquidity_needs", "objectives", "life_stage"):
        if value[key] is not None and not isinstance(value[key], str):
            raise _error(f"client_context.{key}", "must be a string or null")
    for key in ("risk_tolerance_score", "investment_horizon_years"):
        if value[key] is not None and (isinstance(value[key], bool) or not isinstance(value[key], (int, float))):
            raise _error(f"client_context.{key}", "must be numeric or null")
    return _json_compatible(value, "client_context")


def _validate_governance(payload: Any) -> PacketGovernance:
    value = _object(payload, "governance")
    _strict_keys(value, GOVERNANCE_KEYS, set(), "governance")
    return PacketGovernance(
        _bool(value["requires_rm_review"], "governance.requires_rm_review"),
        _bool(value["recommendations_allowed"], "governance.recommendations_allowed"),
        _bool(value["llm_interpretation_allowed"], "governance.llm_interpretation_allowed"),
        _bool(value["source_data_is_authoritative"], "governance.source_data_is_authoritative"),
    )


def _validate_items(payload: dict[str, Any], metadata: PacketMetadata) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    facts = [_object(item, f"facts[{index}]") for index, item in enumerate(_list(payload["facts"], "facts"))]
    findings = [_object(item, f"findings[{index}]") for index, item in enumerate(_list(payload["findings"], "findings"))]
    evidence = [_object(item, f"evidence[{index}]") for index, item in enumerate(_list(payload["evidence"], "evidence"))]
    warnings = [_object(item, f"warnings[{index}]") for index, item in enumerate(_list(payload["warnings"], "warnings"))]
    assumptions = [_object(item, f"assumptions[{index}]") for index, item in enumerate(_list(payload["assumptions"], "assumptions"))]

    calculator_pairs = {(item["name"], item["version"]) for item in metadata.included_calculators}
    fact_ids: set[str] = set()
    fact_payloads: list[dict[str, Any]] = []
    for index, item in enumerate(facts):
        path = f"facts[{index}]"
        _strict_keys(item, {"fact_id", "source_calculator", "source_calculator_version", "metric", "scope", "current_value", "unit", "as_of_date"}, {"previous_value", "change", "currency", "comparison_date", "current_weight_pct", "previous_weight_pct", "change_weight_pp", "percentage_change", "status", "evidence_ids"}, path)
        fact_id = _string(item["fact_id"], f"{path}.fact_id", non_empty=True)
        if fact_id in fact_ids:
            raise _error("facts", f"IDs must be unique; duplicates: {fact_id}")
        fact_ids.add(fact_id)
        pair = (_string(item["source_calculator"], f"{path}.source_calculator", non_empty=True), _semver(item["source_calculator_version"], f"{path}.source_calculator_version"))
        if pair not in calculator_pairs:
            raise _error(f"{path}.source_calculator", "does not match an included calculator")
        fact_payload = {key: value for key, value in item.items() if key not in {"source_calculator", "source_calculator_version"}}
        fact_payloads.append(fact_payload)

    finding_ids: set[str] = set()
    finding_payloads: list[dict[str, Any]] = []
    for index, item in enumerate(findings):
        path = f"findings[{index}]"
        _strict_keys(item, {"finding_id", "source_calculator", "source_calculator_version", "finding_type", "severity", "title", "description", "fact_ids", "evidence_ids", "requires_rm_review"}, set(), path)
        finding_id = _string(item["finding_id"], f"{path}.finding_id", non_empty=True)
        if finding_id in finding_ids:
            raise _error("findings", f"IDs must be unique; duplicates: {finding_id}")
        finding_ids.add(finding_id)
        pair = (_string(item["source_calculator"], f"{path}.source_calculator", non_empty=True), _semver(item["source_calculator_version"], f"{path}.source_calculator_version"))
        if pair not in calculator_pairs:
            raise _error(f"{path}.source_calculator", "does not match an included calculator")
        finding_payloads.append({key: value for key, value in item.items() if key not in {"source_calculator", "source_calculator_version"}})

    evidence_ids: set[str] = set()
    evidence_payloads: list[dict[str, Any]] = []
    for index, item in enumerate(evidence):
        path = f"evidence[{index}]"
        _strict_keys(item, {"evidence_id", "source_calculator", "source_calculator_version", "source_table", "source_keys", "value"}, {"field", "source_date", "description"}, path)
        evidence_id = _string(item["evidence_id"], f"{path}.evidence_id", non_empty=True)
        if evidence_id in evidence_ids:
            raise _error("evidence", f"IDs must be unique; duplicates: {evidence_id}")
        evidence_ids.add(evidence_id)
        pair = (_string(item["source_calculator"], f"{path}.source_calculator", non_empty=True), _semver(item["source_calculator_version"], f"{path}.source_calculator_version"))
        if pair not in calculator_pairs:
            raise _error(f"{path}.source_calculator", "does not match an included calculator")
        source_keys = _object(item["source_keys"], f"{path}.source_keys")
        if not source_keys:
            raise _error(f"{path}.source_keys", "must contain at least one locating key")
        if source_keys.get("client_id") != metadata.client_id:
            raise _error(f"{path}.source_keys.client_id", "evidence is not traceable to the packet client")
        evidence_payloads.append({key: value for key, value in item.items() if key not in {"source_calculator", "source_calculator_version"}})

    warning_ids: set[str] = set()
    warning_payloads: list[dict[str, Any]] = []
    for index, item in enumerate(warnings):
        path = f"warnings[{index}]"
        _strict_keys(item, {"warning_id", "warning_type", "severity", "message"}, {"evidence_ids", "source_reference", "source_calculator", "source_calculator_version"}, path)
        warning_id = _string(item["warning_id"], f"{path}.warning_id", non_empty=True)
        if warning_id in warning_ids:
            raise _error("warnings", f"IDs must be unique; duplicates: {warning_id}")
        warning_ids.add(warning_id)
        if "source_calculator" in item or "source_calculator_version" in item:
            if "source_calculator" not in item or "source_calculator_version" not in item:
                raise _error(path, "source_calculator and source_calculator_version must be supplied together")
            pair = (_string(item["source_calculator"], f"{path}.source_calculator", non_empty=True), _semver(item["source_calculator_version"], f"{path}.source_calculator_version"))
            if pair not in calculator_pairs and pair not in {("snapshot", "1.0.0"), ("packet", "1.0.0")}:
                raise _error(f"{path}.source_calculator", "does not match an included calculator")
        warning_payloads.append(dict(item))

    assumption_ids: set[str] = set()
    assumption_payloads: list[dict[str, Any]] = []
    for index, item in enumerate(assumptions):
        path = f"assumptions[{index}]"
        _strict_keys(item, {"assumption_id", "description", "impact", "accepted"}, {"source_calculator", "source_calculator_version"}, path)
        assumption_id = _string(item["assumption_id"], f"{path}.assumption_id", non_empty=True)
        if assumption_id in assumption_ids:
            raise _error("assumptions", f"IDs must be unique; duplicates: {assumption_id}")
        assumption_ids.add(assumption_id)
        if "source_calculator" in item or "source_calculator_version" in item:
            if "source_calculator" not in item or "source_calculator_version" not in item:
                raise _error(path, "source_calculator and source_calculator_version must be supplied together")
            pair = (_string(item["source_calculator"], f"{path}.source_calculator", non_empty=True), _semver(item["source_calculator_version"], f"{path}.source_calculator_version"))
            if pair not in calculator_pairs and pair != ("packet", "1.0.0"):
                raise _error(f"{path}.source_calculator", "does not match an included calculator")
        assumption_payloads.append(dict(item))

    # Delegate the common fact/finding/evidence/warning contract checks to the
    # established result validator after removing packet-only provenance fields.
    calculator_name, calculator_version = next(iter(calculator_pairs), ("packet", "1.0.0"))
    result_payload = {
        "result_metadata": {
            "result_type": "calculator_result", "schema_version": "1.0.0",
            "calculator_name": calculator_name, "calculator_version": calculator_version,
            "client_id": metadata.client_id, "as_of_date": metadata.as_of_date,
            "comparison_date": metadata.comparison_date, "period_start": metadata.period_start,
            "period_end": metadata.period_end,
            "input_snapshot_schema_version": metadata.input_snapshot_schema_version,
            "input_snapshot_calculation_version": metadata.input_snapshot_calculation_version,
            "status": metadata.status,
        },
        "facts": fact_payloads,
        "findings": finding_payloads,
        "evidence": evidence_payloads,
        "warnings": [{key: value for key, value in item.items() if key not in {"source_calculator", "source_calculator_version"}} for item in warning_payloads],
        "assumptions": [{key: value for key, value in item.items() if key not in {"source_calculator", "source_calculator_version"}} for item in assumption_payloads],
        "requires_rm_review": True,
    }
    try:
        validate_result(result_payload)
    except ValueError as exc:
        raise PacketValidationError(f"packet result components: {exc}") from exc

    return facts, findings, evidence, warnings, assumptions


def validate_packet(payload: dict[str, Any]) -> EvidencePacket:
    """Validate a v1 evidence packet and return its typed envelope."""
    if not isinstance(payload, dict):
        raise _error("packet", "must be an object")
    try:
        json.dumps(payload, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise _error("packet", f"must be JSON-serializable: {exc}") from exc
    _strict_keys(payload, PACKET_KEYS, set(), "packet")
    _scan_for_recommendations(payload)
    metadata = _validate_metadata(payload["packet_metadata"])
    context = _validate_context(payload["client_context"], metadata)
    facts, findings, evidence, warnings, assumptions = _validate_items(payload, metadata)
    governance = _validate_governance(payload["governance"])
    if governance.recommendations_allowed:
        raise _error("governance.recommendations_allowed", "must be false in packet v1.0.0")
    if not governance.requires_rm_review:
        raise _error("governance.requires_rm_review", "must be true in packet v1.0.0")
    if not governance.llm_interpretation_allowed:
        raise _error("governance.llm_interpretation_allowed", "must be true in packet v1.0.0")
    if not governance.source_data_is_authoritative:
        raise _error("governance.source_data_is_authoritative", "must be true in packet v1.0.0")
    if metadata.status == "complete" and not metadata.included_calculators:
        raise _error("packet_metadata.included_calculators", "complete packets must include a calculator result")
    if metadata.status == "blocked" and not warnings:
        raise _error("warnings", "blocked packets must contain at least one warning")
    return EvidencePacket(metadata, context, tuple(facts), tuple(findings), tuple(evidence), tuple(warnings), tuple(assumptions), governance)
