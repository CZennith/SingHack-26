"""Strict runtime validation and v1 result construction."""

from __future__ import annotations

import json
import math
import re
from datetime import date
from typing import Any, Iterable

from .result_models import (
    ALLOWED_SEVERITIES,
    ALLOWED_STATUSES,
    EXPOSURE_CHANGE_STATUSES,
    RESULT_SCHEMA_VERSION,
    SNAPSHOT_SCHEMA_VERSION,
    Assumption,
    CalculatorResult,
    DataQualityWarning,
    Evidence,
    Fact,
    Finding,
    ResultMetadata,
    Scope,
)


SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TOP_LEVEL_KEYS = {"result_metadata", "facts", "findings", "evidence", "warnings", "assumptions", "requires_rm_review"}
METADATA_KEYS = {"result_type", "schema_version", "calculator_name", "calculator_version", "client_id", "as_of_date", "comparison_date", "period_start", "period_end", "input_snapshot_schema_version", "input_snapshot_calculation_version", "status", "input_current_exposure_version", "input_previous_exposure_version"}
SCOPE_KEYS = {"level", "client_id", "portfolio_id", "instrument_id", "asset_class", "sector", "region", "currency", "dimension", "key", "sub_asset_class"}
FACT_KEYS = {"fact_id", "metric", "scope", "current_value", "unit", "as_of_date", "previous_value", "change", "currency", "comparison_date", "current_weight_pct", "previous_weight_pct", "change_weight_pp", "percentage_change", "status", "evidence_ids"}
FINDING_KEYS = {"finding_id", "finding_type", "severity", "title", "description", "fact_ids", "evidence_ids", "requires_rm_review"}
EVIDENCE_KEYS = {"evidence_id", "source_table", "source_keys", "value", "field", "source_date", "description"}
WARNING_KEYS = {"warning_id", "warning_type", "severity", "message", "evidence_ids", "source_reference"}
ASSUMPTION_KEYS = {"assumption_id", "description", "impact", "accepted"}


class ResultContractError(ValueError):
    """One or more payload fields violate the result contract."""


class UnsupportedResultSchemaVersion(ResultContractError):
    """The version dispatcher has no validator for the supplied version."""


def _error(path: str, message: str) -> ResultContractError:
    return ResultContractError(f"{path}: {message}")


def _object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _error(path, "must be an object")
    return value


def _strict_keys(value: dict[str, Any], required: set[str], optional: set[str], path: str) -> None:
    keys = set(value)
    missing = sorted(required - keys)
    unknown = sorted(keys - required - optional)
    if missing:
        raise _error(path, f"missing required field(s): {', '.join(missing)}")
    if unknown:
        raise _error(path, f"unexpected field(s): {', '.join(unknown)}")


def _string(value: Any, path: str, *, non_empty: bool = False) -> str:
    if not isinstance(value, str) or (non_empty and not value.strip()):
        suffix = " and must be non-empty" if non_empty else ""
        raise _error(path, f"must be a string{suffix}")
    return value


def _optional_string(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _string(value, path)


def _date(value: Any, path: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not ISO_DATE.fullmatch(value):
        raise _error(path, "must be an ISO date in YYYY-MM-DD format")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise _error(path, "must be a real calendar date") from exc
    if parsed.isoformat() != value:
        raise _error(path, "must be an ISO date in YYYY-MM-DD format")
    return value


def _semver(value: Any, path: str) -> str:
    value = _string(value, path, non_empty=True)
    if not SEMVER.fullmatch(value):
        raise _error(path, "must use semantic version format MAJOR.MINOR.PATCH")
    return value


def _bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise _error(path, "must be a boolean")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise _error(path, "must be an array")
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


def _ids(items: Iterable[str], path: str) -> tuple[str, ...]:
    result = []
    for index, value in enumerate(items):
        result.append(_string(value, f"{path}[{index}]", non_empty=True))
    duplicates = sorted({item for item in result if result.count(item) > 1})
    if duplicates:
        raise _error(path, f"IDs must be unique; duplicates: {', '.join(duplicates)}")
    return tuple(result)


def _parse_metadata(payload: Any) -> ResultMetadata:
    value = _object(payload, "result_metadata")
    required = METADATA_KEYS - {"comparison_date", "period_start", "period_end"}
    required -= {"input_current_exposure_version", "input_previous_exposure_version"}
    _strict_keys(value, required, {"comparison_date", "period_start", "period_end", "input_current_exposure_version", "input_previous_exposure_version"}, "result_metadata")
    if value["result_type"] != "calculator_result":
        raise _error("result_metadata.result_type", "must equal 'calculator_result'")
    if value["schema_version"] != RESULT_SCHEMA_VERSION:
        raise UnsupportedResultSchemaVersion(f"result_metadata.schema_version: unsupported version {value['schema_version']!r}; supported versions: {RESULT_SCHEMA_VERSION}")
    as_of = _date(value["as_of_date"], "result_metadata.as_of_date")
    comparison = _date(value.get("comparison_date"), "result_metadata.comparison_date", optional=True)
    start = _date(value.get("period_start"), "result_metadata.period_start", optional=True)
    end = _date(value.get("period_end"), "result_metadata.period_end", optional=True)
    if start and end and start > end:
        raise _error("result_metadata", "period_start must be on or before period_end")
    if comparison and comparison > as_of:
        raise _error("result_metadata.comparison_date", "must not be later than as_of_date")
    status = _string(value["status"], "result_metadata.status")
    if status not in ALLOWED_STATUSES:
        raise _error("result_metadata.status", f"must be one of {', '.join(ALLOWED_STATUSES)}")
    current_exposure_version = value.get("input_current_exposure_version")
    previous_exposure_version = value.get("input_previous_exposure_version")
    if current_exposure_version is not None:
        _semver(current_exposure_version, "result_metadata.input_current_exposure_version")
    if previous_exposure_version is not None:
        _semver(previous_exposure_version, "result_metadata.input_previous_exposure_version")
    return ResultMetadata(
        result_type=_string(value["result_type"], "result_metadata.result_type"),
        schema_version=value["schema_version"],
        calculator_name=_string(value["calculator_name"], "result_metadata.calculator_name", non_empty=True),
        calculator_version=_semver(value["calculator_version"], "result_metadata.calculator_version"),
        client_id=_string(value["client_id"], "result_metadata.client_id", non_empty=True),
        as_of_date=as_of,
        comparison_date=comparison,
        period_start=start,
        period_end=end,
        input_snapshot_schema_version=_semver(value["input_snapshot_schema_version"], "result_metadata.input_snapshot_schema_version"),
        input_snapshot_calculation_version=_semver(value["input_snapshot_calculation_version"], "result_metadata.input_snapshot_calculation_version"),
        status=status,
        input_current_exposure_version=_optional_string(current_exposure_version, "result_metadata.input_current_exposure_version"),
        input_previous_exposure_version=_optional_string(previous_exposure_version, "result_metadata.input_previous_exposure_version"),
    )


def _parse_scope(payload: Any, path: str) -> Scope:
    value = _object(payload, path)
    _strict_keys(value, {"level"}, SCOPE_KEYS - {"level"}, path)
    return Scope(
        level=_string(value["level"], f"{path}.level", non_empty=True),
        client_id=_optional_string(value.get("client_id"), f"{path}.client_id"),
        portfolio_id=_optional_string(value.get("portfolio_id"), f"{path}.portfolio_id"),
        instrument_id=_optional_string(value.get("instrument_id"), f"{path}.instrument_id"),
        asset_class=_optional_string(value.get("asset_class"), f"{path}.asset_class"),
        sector=_optional_string(value.get("sector"), f"{path}.sector"),
        region=_optional_string(value.get("region"), f"{path}.region"),
        currency=_optional_string(value.get("currency"), f"{path}.currency"),
        dimension=_optional_string(value.get("dimension"), f"{path}.dimension"),
        key=_json_compatible(value.get("key"), f"{path}.key") if "key" in value else None,
        sub_asset_class=_optional_string(value.get("sub_asset_class"), f"{path}.sub_asset_class"),
    )


def _parse_facts(payload: Any) -> tuple[Fact, ...]:
    facts = _list(payload, "facts")
    parsed = []
    for index, item in enumerate(facts):
        path = f"facts[{index}]"
        value = _object(item, path)
        _strict_keys(value, {"fact_id", "metric", "scope", "current_value", "unit", "as_of_date"}, {"previous_value", "change", "currency", "comparison_date", "current_weight_pct", "previous_weight_pct", "change_weight_pp", "percentage_change", "status", "evidence_ids"}, path)
        unit = _string(value["unit"], f"{path}.unit", non_empty=True)
        currency = _optional_string(value.get("currency"), f"{path}.currency")
        monetary_units = {"amount", "currency", "currency_amount", "monetary", "monetary_amount", "money"}
        looks_like_currency = bool(re.fullmatch(r"[A-Z]{3}", unit))
        if unit.lower() in monetary_units or unit.lower().endswith("_amount") or looks_like_currency:
            if not currency:
                raise _error(f"{path}.currency", "is required for monetary facts")
        current = _json_compatible(value["current_value"], f"{path}.current_value")
        previous = _json_compatible(value.get("previous_value"), f"{path}.previous_value") if "previous_value" in value else None
        change = _json_compatible(value.get("change"), f"{path}.change") if "change" in value else None
        comparison = _date(value.get("comparison_date"), f"{path}.comparison_date", optional=True)
        status = _optional_string(value.get("status"), f"{path}.status")
        if status is not None and status not in EXPOSURE_CHANGE_STATUSES:
            raise _error(f"{path}.status", f"must be one of {', '.join(EXPOSURE_CHANGE_STATUSES)}")
        evidence_ids = _ids(_list(value.get("evidence_ids", []), f"{path}.evidence_ids"), f"{path}.evidence_ids")
        optional_values = {field: _json_compatible(value[field], f"{path}.{field}") for field in ("current_weight_pct", "previous_weight_pct", "change_weight_pp", "percentage_change") if field in value}
        parsed.append(Fact(
            fact_id=_string(value["fact_id"], f"{path}.fact_id", non_empty=True),
            metric=_string(value["metric"], f"{path}.metric", non_empty=True),
            scope=_parse_scope(value["scope"], f"{path}.scope"),
            current_value=current, previous_value=previous, change=change,
            unit=unit, currency=currency,
            as_of_date=_date(value["as_of_date"], f"{path}.as_of_date"),
            comparison_date=comparison,
            current_weight_pct=optional_values.get("current_weight_pct"),
            previous_weight_pct=optional_values.get("previous_weight_pct"),
            change_weight_pp=optional_values.get("change_weight_pp"),
            percentage_change=optional_values.get("percentage_change"),
            status=status,
            evidence_ids=evidence_ids,
        ))
    _unique_model_ids(parsed, "fact_id", "facts")
    return tuple(parsed)


def _parse_findings(payload: Any) -> tuple[Finding, ...]:
    findings = _list(payload, "findings")
    parsed = []
    for index, item in enumerate(findings):
        path = f"findings[{index}]"
        value = _object(item, path)
        _strict_keys(value, FINDING_KEYS, set(), path)
        severity = _string(value["severity"], f"{path}.severity")
        if severity not in ALLOWED_SEVERITIES:
            raise _error(f"{path}.severity", f"must be one of {', '.join(ALLOWED_SEVERITIES)}")
        fact_ids = _ids(_list(value["fact_ids"], f"{path}.fact_ids"), f"{path}.fact_ids")
        evidence_ids = _ids(_list(value["evidence_ids"], f"{path}.evidence_ids"), f"{path}.evidence_ids")
        if not evidence_ids:
            raise _error(f"{path}.evidence_ids", "must contain at least one supporting evidence ID")
        parsed.append(Finding(
            finding_id=_string(value["finding_id"], f"{path}.finding_id", non_empty=True),
            finding_type=_string(value["finding_type"], f"{path}.finding_type", non_empty=True),
            severity=severity,
            title=_string(value["title"], f"{path}.title", non_empty=True),
            description=_string(value["description"], f"{path}.description", non_empty=True),
            fact_ids=fact_ids, evidence_ids=evidence_ids,
            requires_rm_review=_bool(value["requires_rm_review"], f"{path}.requires_rm_review"),
        ))
    _unique_model_ids(parsed, "finding_id", "findings")
    return tuple(parsed)


def _parse_evidence(payload: Any) -> tuple[Evidence, ...]:
    evidence = _list(payload, "evidence")
    parsed = []
    for index, item in enumerate(evidence):
        path = f"evidence[{index}]"
        value = _object(item, path)
        _strict_keys(value, {"evidence_id", "source_table", "source_keys", "value"}, {"field", "source_date", "description"}, path)
        keys = _object(value["source_keys"], f"{path}.source_keys")
        if not keys:
            raise _error(f"{path}.source_keys", "must contain at least one locating key")
        parsed.append(Evidence(
            evidence_id=_string(value["evidence_id"], f"{path}.evidence_id", non_empty=True),
            source_table=_string(value["source_table"], f"{path}.source_table", non_empty=True),
            source_keys=_json_compatible(keys, f"{path}.source_keys"),
            value=_json_compatible(value["value"], f"{path}.value"),
            field=_optional_string(value.get("field"), f"{path}.field"),
            source_date=_date(value.get("source_date"), f"{path}.source_date", optional=True),
            description=_optional_string(value.get("description"), f"{path}.description"),
        ))
    _unique_model_ids(parsed, "evidence_id", "evidence")
    return tuple(parsed)


def _parse_warnings(payload: Any) -> tuple[DataQualityWarning, ...]:
    warnings = _list(payload, "warnings")
    parsed = []
    for index, item in enumerate(warnings):
        path = f"warnings[{index}]"
        value = _object(item, path)
        _strict_keys(value, {"warning_id", "warning_type", "severity", "message"}, {"evidence_ids", "source_reference"}, path)
        severity = _string(value["severity"], f"{path}.severity")
        if severity not in ALLOWED_SEVERITIES:
            raise _error(f"{path}.severity", f"must be one of {', '.join(ALLOWED_SEVERITIES)}")
        evidence_ids = _ids(_list(value.get("evidence_ids", []), f"{path}.evidence_ids"), f"{path}.evidence_ids")
        source_reference = value.get("source_reference")
        if source_reference is not None:
            source_reference = _json_compatible(_object(source_reference, f"{path}.source_reference"), f"{path}.source_reference")
        parsed.append(DataQualityWarning(
            warning_id=_string(value["warning_id"], f"{path}.warning_id", non_empty=True),
            warning_type=_string(value["warning_type"], f"{path}.warning_type", non_empty=True),
            severity=severity,
            message=_string(value["message"], f"{path}.message", non_empty=True),
            evidence_ids=evidence_ids, source_reference=source_reference,
        ))
    _unique_model_ids(parsed, "warning_id", "warnings")
    return tuple(parsed)


def _parse_assumptions(payload: Any) -> tuple[Assumption, ...]:
    assumptions = _list(payload, "assumptions")
    parsed = []
    for index, item in enumerate(assumptions):
        path = f"assumptions[{index}]"
        value = _object(item, path)
        _strict_keys(value, ASSUMPTION_KEYS, set(), path)
        parsed.append(Assumption(
            assumption_id=_string(value["assumption_id"], f"{path}.assumption_id", non_empty=True),
            description=_string(value["description"], f"{path}.description", non_empty=True),
            impact=_string(value["impact"], f"{path}.impact", non_empty=True),
            accepted=_bool(value["accepted"], f"{path}.accepted"),
        ))
    _unique_model_ids(parsed, "assumption_id", "assumptions")
    return tuple(parsed)


def _unique_model_ids(items: Iterable[Any], attribute: str, path: str) -> None:
    ids = [getattr(item, attribute) for item in items]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        raise _error(path, f"IDs must be unique; duplicates: {', '.join(duplicates)}")


def validate_result(payload: dict[str, Any]) -> CalculatorResult:
    """Validate a v1 result payload and return its typed contract object."""
    if not isinstance(payload, dict):
        raise _error("result", "must be an object")
    try:
        json.dumps(payload, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise _error("result", f"must be JSON-serializable: {exc}") from exc
    _strict_keys(payload, TOP_LEVEL_KEYS, set(), "result")
    metadata = _parse_metadata(payload["result_metadata"])
    facts = _parse_facts(payload["facts"])
    findings = _parse_findings(payload["findings"])
    evidence = _parse_evidence(payload["evidence"])
    warnings = _parse_warnings(payload["warnings"])
    assumptions = _parse_assumptions(payload["assumptions"])
    requires_review = _bool(payload["requires_rm_review"], "requires_rm_review")
    fact_ids = {item.fact_id for item in facts}
    evidence_ids = {item.evidence_id for item in evidence}
    for finding in findings:
        missing_facts = sorted(set(finding.fact_ids) - fact_ids)
        if missing_facts:
            raise _error(f"findings[{finding.finding_id}].fact_ids", f"references missing fact ID(s): {', '.join(missing_facts)}")
        missing_evidence = sorted(set(finding.evidence_ids) - evidence_ids)
        if missing_evidence:
            raise _error(f"findings[{finding.finding_id}].evidence_ids", f"references missing evidence ID(s): {', '.join(missing_evidence)}")
    for warning in warnings:
        missing_evidence = sorted(set(warning.evidence_ids) - evidence_ids)
        if missing_evidence:
            raise _error(f"warnings[{warning.warning_id}].evidence_ids", f"references missing evidence ID(s): {', '.join(missing_evidence)}")
    if metadata.status == "blocked" and not warnings:
        raise _error("warnings", "blocked results must contain at least one warning")
    return CalculatorResult(metadata, facts, findings, evidence, warnings, assumptions, requires_review)


def result_metadata_from_snapshot(
    snapshot: dict[str, Any],
    calculator_name: str,
    calculator_version: str,
    *,
    status: str = "complete",
    comparison_date: str | None = None,
    snapshot_schema_version: str = SNAPSHOT_SCHEMA_VERSION,
) -> dict[str, Any]:
    """Explicitly adapt existing snapshot metadata into result metadata.

    The current snapshot stores ``calculation_version`` but not a separate
    snapshot schema version, so the adapter requires/documentarily defaults
    that missing schema value to ``1.0.0``. The snapshot itself is unchanged.
    """
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("snapshot_metadata"), dict):
        raise ResultContractError("snapshot.snapshot_metadata: required object is missing")
    metadata = snapshot["snapshot_metadata"]
    required = ("client_id", "as_of_date", "calculation_version")
    missing = [key for key in required if key not in metadata]
    if missing:
        raise ResultContractError(f"snapshot.snapshot_metadata: missing field(s): {', '.join(missing)}")
    result_metadata = {
        "result_type": "calculator_result",
        "schema_version": RESULT_SCHEMA_VERSION,
        "calculator_name": calculator_name,
        "calculator_version": calculator_version,
        "client_id": metadata["client_id"],
        "as_of_date": metadata["as_of_date"],
        "comparison_date": comparison_date,
        "period_start": metadata.get("period_start"),
        "period_end": metadata.get("period_end"),
        "input_snapshot_schema_version": snapshot_schema_version,
        "input_snapshot_calculation_version": metadata["calculation_version"],
        "status": status,
    }
    # Validate the adapted metadata using the same strict field rules.
    _parse_metadata(result_metadata)
    return result_metadata
