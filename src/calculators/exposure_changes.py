"""Compare two direct exposure bases and return an evidence-backed result."""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from ..client_snapshot import validate_snapshot
from ..contracts.serialization import dumps_result
from ..contracts.validation import validate_result
from ..output_files import OutputWriteError, atomic_write_json
from ..output_paths import OutputPathError, exposure_change_output_path
from .exposure_base import EXPOSURE_VERSION, TOLERANCE, build_exposure_base


CHANGE_VERSION = "1.0.0"
DIMENSION_TABLES = ("by_portfolio", "by_asset_class", "by_sub_asset_class", "by_sector", "by_region", "by_currency", "by_instrument")
DIMENSION_NAMES = {table: table[3:] for table in DIMENSION_TABLES}


class ExposureChangeError(ValueError):
    """The exposure bases cannot be compared safely."""


def _decimal(value: Any, path: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ExposureChangeError(f"{path}: malformed numeric value {value!r}") from exc
    if not parsed.is_finite():
        raise ExposureChangeError(f"{path}: numeric value must be finite")
    return parsed


def _number(value: Decimal) -> float:
    return float(value)


def _validate_exposure_base(exposure: dict, label: str) -> dict:
    if not isinstance(exposure, dict):
        raise ExposureChangeError(f"{label}: exposure base must be an object")
    required = {"exposure_metadata", "client_total", *DIMENSION_TABLES, "warnings", "source_references"}
    missing = sorted(required - set(exposure))
    if missing:
        raise ExposureChangeError(f"{label}: missing required field(s): {', '.join(missing)}")
    metadata = exposure["exposure_metadata"]
    if not isinstance(metadata, dict):
        raise ExposureChangeError(f"{label}.exposure_metadata: must be an object")
    if metadata.get("exposure_type") != "direct" or metadata.get("currency_basis") != "USD" or metadata.get("look_through_included") is not False:
        raise ExposureChangeError(f"{label}.exposure_metadata: only direct USD exposure bases with look_through_included=false are supported")
    for key in ("client_id", "as_of_date", "calculator_name", "calculator_version"):
        if not metadata.get(key):
            raise ExposureChangeError(f"{label}.exposure_metadata.{key}: is required")
    if metadata["calculator_name"] != "exposure_base" or metadata["calculator_version"] != EXPOSURE_VERSION:
        raise ExposureChangeError(f"{label}: unsupported exposure base version")
    for table in DIMENSION_TABLES:
        if not isinstance(exposure[table], list):
            raise ExposureChangeError(f"{label}.{table}: must be an array")
    if not isinstance(exposure["warnings"], list) or not isinstance(exposure["source_references"], list):
        raise ExposureChangeError(f"{label}: warnings and source_references must be arrays")
    return exposure


def _matching_key(group: dict[str, Any]) -> tuple[Any, ...]:
    return (group.get("scope_level"), group.get("portfolio_id"), group.get("dimension"), group.get("key"), group.get("instrument_id"))


def _sort_key(key: tuple[Any, ...]) -> tuple[str, ...]:
    return tuple("" if value is None else str(value) for value in key)


def _scope(group: dict[str, Any], client_id: str) -> dict[str, Any]:
    dimension = group.get("dimension")
    key = group.get("key")
    return {
        "level": group.get("scope_level"),
        "client_id": client_id,
        "portfolio_id": group.get("portfolio_id"),
        "instrument_id": group.get("instrument_id"),
        "asset_class": key if dimension == "asset_class" else None,
        "sub_asset_class": key if dimension == "sub_asset_class" else None,
        "sector": key if dimension == "sector" else None,
        "region": key if dimension == "region" else None,
        "currency": key if dimension == "currency" else None,
        "dimension": dimension,
        "key": key,
    }


def _evidence(client_id: str, as_of: str, group: dict[str, Any], value: float, role: str, evidence_number: int) -> dict[str, Any]:
    dimension = group.get("dimension")
    table = "by_portfolio" if dimension == "portfolio" else f"by_{dimension}"
    return {
        "evidence_id": f"E-{evidence_number:04d}",
        "source_table": f"exposure_base.{table}",
        "source_keys": {
            "client_id": client_id,
            "snapshot_date": as_of,
            "dimension": dimension,
            "scope_level": group.get("scope_level"),
            "key": group.get("key"),
            "portfolio_id": group.get("portfolio_id"),
            "instrument_id": group.get("instrument_id"),
        },
        "field": "market_value_usd",
        "value": value,
        "source_date": as_of,
        "description": f"{role} exposure-base value: sum of direct market_value_usd values grouped by {dimension}.",
    }


def _warning_from_base(warning: dict[str, Any], prefix: str, number: int) -> dict[str, Any]:
    severity = warning.get("severity", "info")
    if severity == "warning":
        severity = "medium"
    if severity not in {"info", "low", "medium", "high"}:
        severity = "info"
    return {
        "warning_id": f"W-{prefix}-{number:03d}",
        "warning_type": warning.get("warning_type", "exposure_base_warning"),
        "severity": severity,
        "message": warning.get("message", "The input exposure base contains a data-quality warning."),
        "source_reference": warning.get("source_reference"),
    }


def calculate_exposure_changes(current_exposure: dict, previous_exposure: dict) -> dict:
    """Compare two direct exposure bases; no materiality policy is applied."""
    current = _validate_exposure_base(current_exposure, "current_exposure")
    previous = _validate_exposure_base(previous_exposure, "previous_exposure")
    current_meta = current["exposure_metadata"]
    previous_meta = previous["exposure_metadata"]
    if current_meta["client_id"] != previous_meta["client_id"]:
        raise ExposureChangeError("current_exposure and previous_exposure must have the same client_id")
    if current_meta["as_of_date"] == previous_meta["as_of_date"]:
        raise ExposureChangeError("current_exposure and previous_exposure must have different as_of_date values")
    client_id = current_meta["client_id"]
    evidence = []
    facts = []
    evidence_number = 1
    fact_number = 1
    for table in DIMENSION_TABLES:
        current_groups = {_matching_key(group): group for group in current[table]}
        previous_groups = {_matching_key(group): group for group in previous[table]}
        for matching_key in sorted(set(current_groups) | set(previous_groups), key=_sort_key):
            current_group = current_groups.get(matching_key, {"dimension": DIMENSION_NAMES[table], "scope_level": matching_key[0], "portfolio_id": matching_key[1], "key": matching_key[3], "instrument_id": matching_key[4], "instrument_name": None})
            previous_group = previous_groups.get(matching_key, {"dimension": DIMENSION_NAMES[table], "scope_level": matching_key[0], "portfolio_id": matching_key[1], "key": matching_key[3], "instrument_id": matching_key[4], "instrument_name": None})
            current_value = _decimal(current_group.get("market_value_usd", 0), f"current_exposure.{table}")
            previous_value = _decimal(previous_group.get("market_value_usd", 0), f"previous_exposure.{table}")
            change = current_value - previous_value
            if abs(previous_value) <= TOLERANCE and abs(current_value) <= TOLERANCE:
                status = "unchanged"
            elif abs(previous_value) <= TOLERANCE:
                status = "added"
            elif abs(current_value) <= TOLERANCE:
                status = "exited"
            elif abs(change) <= TOLERANCE:
                status = "unchanged"
            else:
                status = "changed"
            current_weight = _decimal(current_group.get("weight_pct", 0), f"current_exposure.{table}.weight_pct")
            previous_weight = _decimal(previous_group.get("weight_pct", 0), f"previous_exposure.{table}.weight_pct")
            percentage_change = None if abs(previous_value) <= TOLERANCE else _number(change / previous_value * Decimal(100))
            current_evidence = _evidence(client_id, current_meta["as_of_date"], current_group, _number(current_value), "Current", evidence_number)
            evidence_number += 1
            previous_evidence = _evidence(client_id, previous_meta["as_of_date"], previous_group, _number(previous_value), "Previous", evidence_number)
            evidence_number += 1
            evidence.extend((current_evidence, previous_evidence))
            facts.append({
                "fact_id": f"F-{fact_number:04d}",
                "metric": "exposure_change",
                "scope": _scope(current_group, client_id),
                "current_value": _number(current_value),
                "previous_value": _number(previous_value),
                "change": _number(change),
                "unit": "USD",
                "currency": "USD",
                "as_of_date": current_meta["as_of_date"],
                "comparison_date": previous_meta["as_of_date"],
                "current_weight_pct": _number(current_weight),
                "previous_weight_pct": _number(previous_weight),
                "change_weight_pp": _number(current_weight - previous_weight),
                "percentage_change": percentage_change,
                "status": status,
                "evidence_ids": [current_evidence["evidence_id"], previous_evidence["evidence_id"]],
            })
            fact_number += 1

    warnings = []
    for prefix, exposure in (("CURRENT", current), ("PREVIOUS", previous)):
        for number, warning in enumerate(exposure["warnings"], start=1):
            warnings.append(_warning_from_base(warning, prefix, number))
    payload = {
        "result_metadata": {
            "result_type": "calculator_result",
            "schema_version": "1.0.0",
            "calculator_name": "exposure_changes",
            "calculator_version": CHANGE_VERSION,
            "client_id": client_id,
            "as_of_date": current_meta["as_of_date"],
            "comparison_date": previous_meta["as_of_date"],
            "period_start": None,
            "period_end": None,
            "input_snapshot_schema_version": current_meta.get("snapshot_schema_version", "1.0.0"),
            "input_snapshot_calculation_version": current_meta.get("snapshot_calculation_version", "1.0.0"),
            "status": "complete",
            "input_current_exposure_version": current_meta["calculator_version"],
            "input_previous_exposure_version": previous_meta["calculator_version"],
        },
        "facts": facts,
        "findings": [],
        "evidence": evidence,
        "warnings": warnings,
        "assumptions": [
            {"assumption_id": "A-001", "description": "Exposure is aggregated from direct holdings only.", "impact": "Underlying references are preserved as metadata and are not added to totals.", "accepted": True},
            {"assumption_id": "A-002", "description": "A missing matching group is represented with a zero value for comparison.", "impact": "Added and exited statuses describe presence across the two supplied bases.", "accepted": True},
        ],
        "requires_rm_review": False,
    }
    return validate_result(payload).to_dict()


def calculate_exposure_changes_for_all_clients(snapshots_by_client_and_date: dict) -> list[dict]:
    """Compare the latest two supplied snapshots for every client, fail-fast."""
    grouped: dict[str, dict[str, dict]] = {}
    for key, value in snapshots_by_client_and_date.items():
        if isinstance(key, tuple) and len(key) == 2:
            client_id, snapshot_date = key
            grouped.setdefault(str(client_id), {})[str(snapshot_date)] = value
        elif isinstance(value, dict):
            grouped[str(key)] = {str(snapshot_date): snapshot for snapshot_date, snapshot in value.items()}
        elif isinstance(value, list):
            grouped[str(key)] = {snapshot["snapshot_metadata"]["as_of_date"]: snapshot for snapshot in value}
        else:
            raise ExposureChangeError(f"client {key!r}: expected a date mapping or snapshot list")
    results = []
    for client_id in sorted(grouped):
        dates = sorted(grouped[client_id])
        if len(dates) < 2:
            raise ExposureChangeError(f"client {client_id}: at least two snapshot dates are required")
        try:
            current = build_exposure_base(grouped[client_id][dates[-1]])
            previous = build_exposure_base(grouped[client_id][dates[-2]])
            result = calculate_exposure_changes(current, previous)
        except Exception as exc:
            raise ExposureChangeError(f"client {client_id}: {exc}") from exc
        results.append(result)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare direct exposure in two client snapshots")
    parser.add_argument("--current-snapshot", required=True)
    parser.add_argument("--previous-snapshot", required=True)
    destination = parser.add_mutually_exclusive_group()
    destination.add_argument("--output", help="Exact output JSON path")
    destination.add_argument("--output-root", help="Root under which the canonical output path is created")
    parser.add_argument("--overwrite", action="store_true", help="Intentionally replace an existing generated output")
    args = parser.parse_args(argv)
    if args.overwrite and not (args.output or args.output_root):
        print("Exposure-change calculation failed: --overwrite requires --output or --output-root", file=sys.stderr)
        return 1
    try:
        current_path, previous_path = Path(args.current_snapshot), Path(args.previous_snapshot)
        current = validate_snapshot(json.loads(current_path.read_text(encoding="utf-8")))
        previous = validate_snapshot(json.loads(previous_path.read_text(encoding="utf-8")))
        result = calculate_exposure_changes(build_exposure_base(current), build_exposure_base(previous))
        rendered = dumps_result(result)
        if args.output_root:
            output_root = Path(args.output_root)
            metadata = result["result_metadata"]
            output = exposure_change_output_path(
                output_root, metadata["client_id"], metadata["comparison_date"], metadata["as_of_date"]
            )
        elif args.output:
            output = Path(args.output)
            output_root = output.parent
        else:
            print(rendered, end="")
            return 0
        metadata = result["result_metadata"]
        atomic_write_json(
            output, rendered, output_root=output_root, overwrite=args.overwrite,
            artifact_description=(
                f"exposure change for client {metadata['client_id']}, "
                f"dates {metadata['comparison_date']} to {metadata['as_of_date']}"
            ),
        )
    except (OSError, json.JSONDecodeError, ExposureChangeError, OutputPathError, OutputWriteError, ValueError) as exc:
        print(f"Exposure-change calculation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
