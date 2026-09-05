"""JSON serialization and generated JSON Schema for result contract v1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .result_models import ALLOWED_SEVERITIES, ALLOWED_STATUSES, RESULT_SCHEMA_VERSION
from .validation import validate_result


def _string(description: str, *, nullable: bool = False) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "string", "description": description}
    if nullable:
        schema["type"] = ["string", "null"]
    return schema


def _date(description: str, *, nullable: bool = False) -> dict[str, Any]:
    schema = _string(description, nullable=nullable)
    schema["format"] = "date"
    schema["pattern"] = r"^\d{4}-\d{2}-\d{2}$"
    return schema


def _semver(description: str) -> dict[str, Any]:
    return {"type": "string", "description": description, "pattern": r"^\d+\.\d+\.\d+$", "minLength": 5}


def _object(properties: dict[str, Any], required: list[str], description: str) -> dict[str, Any]:
    return {"type": "object", "description": description, "additionalProperties": False, "properties": properties, "required": required}


def generate_json_schema() -> dict[str, Any]:
    """Generate the canonical schema from the v1 contract definitions."""
    scope = _object(
        {
            "level": _string("Scope level, such as client or portfolio."),
            "client_id": _string("Client identifier.", nullable=True),
            "portfolio_id": _string("Portfolio identifier.", nullable=True),
            "instrument_id": _string("Instrument identifier.", nullable=True),
            "asset_class": _string("Asset class.", nullable=True),
            "sector": _string("Sector.", nullable=True),
            "region": _string("Region.", nullable=True),
            "currency": _string("Currency for the scoped value.", nullable=True),
            "dimension": _string("Optional aggregation dimension.", nullable=True),
            "key": {"description": "Optional JSON-compatible aggregation key."},
            "sub_asset_class": _string("Optional sub-asset-class dimension.", nullable=True),
        },
        ["level"],
        "The dimensions to which a fact applies.",
    )
    metadata = _object(
        {
            "result_type": {"const": "calculator_result", "description": "Discriminator for this result envelope."},
            "schema_version": {"const": RESULT_SCHEMA_VERSION, "description": "Version of this result contract."},
            "calculator_name": {**_string("Stable calculator name."), "minLength": 1},
            "calculator_version": _semver("Semantic version of the calculator implementation."),
            "client_id": {**_string("Client identifier."), "minLength": 1},
            "as_of_date": _date("Required ISO valuation date."),
            "comparison_date": _date("Optional comparison ISO date.", nullable=True),
            "period_start": _date("Inclusive period start.", nullable=True),
            "period_end": _date("Inclusive period end.", nullable=True),
            "input_snapshot_schema_version": _semver("Version of the input client snapshot contract."),
            "input_snapshot_calculation_version": _semver("Calculation version recorded by the input snapshot."),
            "status": {"type": "string", "enum": list(ALLOWED_STATUSES), "description": "Completion state."},
            "input_current_exposure_version": {"type": ["string", "null"], "description": "Semantic version of the current exposure-base input.", "pattern": r"^\d+\.\d+\.\d+$"},
            "input_previous_exposure_version": {"type": ["string", "null"], "description": "Semantic version of the previous exposure-base input.", "pattern": r"^\d+\.\d+\.\d+$"},
        },
        ["result_type", "schema_version", "calculator_name", "calculator_version", "client_id", "as_of_date", "input_snapshot_schema_version", "input_snapshot_calculation_version", "status"],
        "Metadata identifying the result and its input snapshot.",
    )
    fact = _object(
        {
            "fact_id": {**_string("Unique fact identifier."), "minLength": 1}, "metric": {**_string("Fact metric name."), "minLength": 1}, "scope": {"$ref": "#/$defs/Scope"},
            "current_value": {"description": "JSON-compatible current fact value."}, "previous_value": {"description": "Optional JSON-compatible previous value."},
            "change": {"description": "Optional JSON-compatible change value."}, "unit": {**_string("Unit identifying the value type."), "minLength": 1},
            "currency": _string("Currency for monetary values.", nullable=True), "as_of_date": _date("ISO date of current value."),
            "comparison_date": _date("Optional ISO date of previous value.", nullable=True),
            "current_weight_pct": {"description": "Optional current weight percentage."}, "previous_weight_pct": {"description": "Optional previous weight percentage."},
            "change_weight_pp": {"description": "Optional weight change in percentage points."}, "percentage_change": {"description": "Optional percentage change; null when previous value is zero."},
            "status": {"type": ["string", "null"], "enum": ["added", "exited", "changed", "unchanged", None], "description": "Optional change status."},
            "evidence_ids": {"type": "array", "items": _string("Evidence identifier."), "description": "Optional supporting evidence IDs."},
        },
        ["fact_id", "metric", "scope", "current_value", "unit", "as_of_date"],
        "A calculated or retrieved value without interpretation.",
    )
    finding = _object(
        {
            "finding_id": {**_string("Unique finding identifier."), "minLength": 1}, "finding_type": {**_string("Rule-triggered observation type."), "minLength": 1},
            "severity": {"type": "string", "enum": list(ALLOWED_SEVERITIES), "description": "Observation severity."},
            "title": {**_string("Human-readable observation title."), "minLength": 1}, "description": {**_string("Human-readable observation description."), "minLength": 1},
            "fact_ids": {"type": "array", "items": _string("Fact identifier."), "description": "Supporting fact IDs."},
            "evidence_ids": {"type": "array", "items": _string("Evidence identifier."), "minItems": 1, "description": "Supporting evidence IDs."},
            "requires_rm_review": {"type": "boolean", "description": "Whether RM review is required."},
        },
        ["finding_id", "finding_type", "severity", "title", "description", "fact_ids", "evidence_ids", "requires_rm_review"],
        "An evidence-backed observation derived from facts; not a recommendation.",
    )
    evidence = _object(
        {
            "evidence_id": {**_string("Unique evidence identifier."), "minLength": 1}, "source_table": {**_string("Database table or snapshot section."), "minLength": 1},
            "source_keys": {"type": "object", "minProperties": 1, "additionalProperties": True, "description": "Keys locating the source record."},
            "value": {"description": "JSON-compatible source value."}, "field": _string("Optional source field.", nullable=True),
            "source_date": _date("Optional ISO source date.", nullable=True), "description": _string("Optional evidence description.", nullable=True),
        },
        ["evidence_id", "source_table", "source_keys", "value"],
        "Traceability to a database record or snapshot field.",
    )
    warning = _object(
        {
            "warning_id": {**_string("Unique warning identifier."), "minLength": 1}, "warning_type": {**_string("Warning category."), "minLength": 1},
            "severity": {"type": "string", "enum": list(ALLOWED_SEVERITIES), "description": "Warning severity."},
            "message": {**_string("Human-readable limitation or uncertainty."), "minLength": 1},
            "evidence_ids": {"type": "array", "items": _string("Evidence identifier."), "description": "Optional supporting evidence IDs."},
            "source_reference": {"type": ["object", "null"], "additionalProperties": True, "description": "Optional source reference."},
        },
        ["warning_id", "warning_type", "severity", "message"],
        "A limitation, missing-data condition, or uncertainty.",
    )
    assumption = _object(
        {"assumption_id": {**_string("Unique assumption identifier."), "minLength": 1}, "description": {**_string("Explicit assumption."), "minLength": 1}, "impact": {**_string("Impact of the assumption."), "minLength": 1}, "accepted": {"type": "boolean", "description": "Whether the assumption was accepted."}},
        ["assumption_id", "description", "impact", "accepted"],
        "Explanatory metadata about an assumption.",
    )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://singhacks.local/contracts/analysis-result-1.0.0.schema.json",
        "title": "Calculator Analysis Result",
        "description": "Versioned, evidence-backed result envelope for future client-analysis calculators.",
        "type": "object",
        "additionalProperties": False,
        "required": ["result_metadata", "facts", "findings", "evidence", "warnings", "assumptions", "requires_rm_review"],
        "properties": {
            "result_metadata": {"$ref": "#/$defs/ResultMetadata"}, "facts": {"type": "array", "items": {"$ref": "#/$defs/Fact"}},
            "findings": {"type": "array", "items": {"$ref": "#/$defs/Finding"}}, "evidence": {"type": "array", "items": {"$ref": "#/$defs/Evidence"}},
            "warnings": {"type": "array", "items": {"$ref": "#/$defs/Warning"}}, "assumptions": {"type": "array", "items": {"$ref": "#/$defs/Assumption"}},
            "requires_rm_review": {"type": "boolean", "description": "Whether the result requires RM review."},
        },
        "$defs": {"ResultMetadata": metadata, "Scope": scope, "Fact": fact, "Finding": finding, "Evidence": evidence, "Warning": warning, "Assumption": assumption},
    }


def dumps_result(result: Any, *, indent: int = 2) -> str:
    """Validate and serialize a result or CalculatorResult as UTF-8-ready JSON."""
    payload = result.to_dict() if hasattr(result, "to_dict") else result
    validate_result(payload)
    return json.dumps(payload, ensure_ascii=False, indent=indent, allow_nan=False) + "\n"


def loads_result(text: str):
    """Deserialize JSON and validate it through the version dispatcher."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid result JSON: {exc}") from exc
    return validate_result(payload)


def write_json_schema(path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(generate_json_schema(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output
