"""Assemble deterministic, reviewable evidence packets from existing inputs."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from ..client_snapshot import validate_snapshot
from ..contracts.validation import validate_result
from ..output_files import OutputWriteError, atomic_write_json
from ..output_paths import OutputPathError, evidence_packet_output_path
from .packet_models import PACKET_TYPE, PACKET_VERSION, SNAPSHOT_SCHEMA_VERSION
from .packet_serialization import dumps_packet
from .packet_validation import PacketValidationError, UnsupportedPacketType, validate_packet


RECOMMENDATION_FIELDS = {"recommended_action", "recommended_trade", "buy_sell_signal", "portfolio_action"}
CONTEXT_FIELDS = ("client_id", "base_currency", "risk_profile", "risk_tolerance_score", "investment_horizon_years", "liquidity_needs", "objectives", "life_stage")


def _scan_for_recommendations(value: Any, path: str = "calculator_result") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in RECOMMENDATION_FIELDS:
                raise PacketValidationError(f"{path}.{key}: recommendation fields are prohibited in packet v1.0.0")
            _scan_for_recommendations(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan_for_recommendations(item, f"{path}[{index}]")


def _severity(value: Any) -> str:
    # Snapshot flags predate the result contract and use "warning" in some
    # datasets. Map that level to the contract's equivalent without reducing
    # severity; the synthetic database currently uses info/low/medium/high.
    if value == "warning":
        return "medium"
    if value == "critical":
        return "high"
    return value if value in {"info", "low", "medium", "high"} else "info"


def _snapshot_warnings(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    warnings = []
    for number, flag in enumerate(snapshot.get("data_quality_flags", []), start=1):
        warnings.append({
            "warning_id": f"snapshot:W-{number:04d}",
            "warning_type": flag.get("flag_type", "snapshot_data_quality"),
            "severity": _severity(flag.get("severity")),
            "message": flag.get("message", "The client snapshot contains a data-quality flag."),
            "evidence_ids": [],
            "source_reference": copy.deepcopy(flag.get("source_reference")),
            "source_calculator": "snapshot",
            "source_calculator_version": SNAPSHOT_SCHEMA_VERSION,
        })
    return warnings


def _context(snapshot: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    client = snapshot["client"]
    context = {field: copy.deepcopy(client.get(field)) for field in CONTEXT_FIELDS}
    missing = [field for field in CONTEXT_FIELDS if context[field] is None]
    return context, missing


def _namespace_id(calculator_name: str, original_id: str, used: dict[str, Any], fingerprint: str) -> str:
    base = f"{calculator_name}:{original_id}"
    if base not in used:
        used[base] = fingerprint
        return base
    if used[base] == fingerprint:
        return base
    suffix = 2
    while f"{base}#{suffix}" in used:
        suffix += 1
    namespaced = f"{base}#{suffix}"
    used[namespaced] = fingerprint
    return namespaced


def _unique_namespace_id(calculator_name: str, original_id: str, used: dict[str, Any], fingerprint: str) -> str:
    """Namespace every non-evidence item, retaining duplicate result items."""
    base = f"{calculator_name}:{original_id}"
    if base not in used:
        used[base] = fingerprint
        return base
    suffix = 2
    while f"{base}#{suffix}" in used:
        suffix += 1
    namespaced = f"{base}#{suffix}"
    used[namespaced] = fingerprint
    return namespaced


def _stable_fingerprint(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _compatible_result(result: Any, snapshot_metadata: dict[str, Any], client_id: str) -> None:
    metadata = result.result_metadata
    if metadata.calculator_name != "exposure_changes":
        raise PacketValidationError(f"calculator result {metadata.calculator_name!r}: only 'exposure_changes' is supported")
    if metadata.client_id != client_id:
        raise PacketValidationError(f"calculator result client_id {metadata.client_id!r} does not match snapshot client_id {client_id!r}")
    if metadata.as_of_date != snapshot_metadata["as_of_date"]:
        raise PacketValidationError(f"calculator result as_of_date {metadata.as_of_date!r} does not match snapshot {snapshot_metadata['as_of_date']!r}")
    if metadata.comparison_date is None:
        raise PacketValidationError("calculator result comparison_date is required for exposure_change_review")
    if metadata.input_snapshot_schema_version != SNAPSHOT_SCHEMA_VERSION:
        raise PacketValidationError("calculator result input_snapshot_schema_version does not match snapshot schema version")
    if metadata.input_snapshot_calculation_version != snapshot_metadata["calculation_version"]:
        raise PacketValidationError("calculator result input_snapshot_calculation_version does not match snapshot calculation version")
    if metadata.period_start is not None and metadata.period_start != snapshot_metadata["period_start"]:
        raise PacketValidationError("calculator result period_start does not match snapshot period_start")
    if metadata.period_end is not None and metadata.period_end != snapshot_metadata["period_end"]:
        raise PacketValidationError("calculator result period_end does not match snapshot period_end")


def _result_items(results: list[Any], snapshot: dict[str, Any], client_id: str) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict], list[dict]]:
    facts: list[dict] = []
    findings: list[dict] = []
    evidence: list[dict] = []
    warnings: list[dict] = []
    assumptions: list[dict] = []
    calculators: list[dict] = []
    used_fact_ids: dict[str, Any] = {}
    used_finding_ids: dict[str, Any] = {}
    used_evidence_ids: dict[str, Any] = {}
    evidence_dedup: dict[str, str] = {}
    used_warning_ids: dict[str, Any] = {}
    used_assumption_ids: dict[str, Any] = {}
    for result_index, result in enumerate(results):
        result_payload = result.to_dict()
        result_name = result.result_metadata.calculator_name
        result_version = result.result_metadata.calculator_version
        calculators.append({"name": result_name, "version": result_version})
        _compatible_result(result, snapshot["snapshot_metadata"], client_id)
        evidence_map: dict[str, str] = {}
        for item in result_payload["evidence"]:
            original = item["evidence_id"]
            packet_item = copy.deepcopy(item)
            packet_item["source_calculator"] = result_name
            packet_item["source_calculator_version"] = result_version
            fingerprint = _stable_fingerprint({key: packet_item.get(key) for key in ("source_calculator", "source_table", "source_keys", "field", "value", "source_date")})
            packet_id = evidence_dedup.get(fingerprint)
            if packet_id is None:
                packet_id = _namespace_id(result_name, original, used_evidence_ids, fingerprint)
                evidence_dedup[fingerprint] = packet_id
            evidence_map[original] = packet_id
            packet_item["evidence_id"] = packet_id
            if not any(existing["evidence_id"] == packet_id for existing in evidence):
                evidence.append(packet_item)
        fact_map: dict[str, str] = {}
        for item in result_payload["facts"]:
            original = item["fact_id"]
            packet_item = copy.deepcopy(item)
            packet_item["fact_id"] = _unique_namespace_id(result_name, original, used_fact_ids, _stable_fingerprint(packet_item))
            packet_item["source_calculator"] = result_name
            packet_item["source_calculator_version"] = result_version
            packet_item["evidence_ids"] = [evidence_map[item_id] for item_id in item.get("evidence_ids", [])]
            fact_map[original] = packet_item["fact_id"]
            facts.append(packet_item)
        for item in result_payload["findings"]:
            packet_item = copy.deepcopy(item)
            packet_item["finding_id"] = _unique_namespace_id(result_name, item["finding_id"], used_finding_ids, _stable_fingerprint(item))
            packet_item["source_calculator"] = result_name
            packet_item["source_calculator_version"] = result_version
            packet_item["fact_ids"] = [fact_map[item_id] for item_id in item["fact_ids"]]
            packet_item["evidence_ids"] = [evidence_map[item_id] for item_id in item["evidence_ids"]]
            findings.append(packet_item)
        for item in result_payload["warnings"]:
            packet_item = copy.deepcopy(item)
            packet_item["warning_id"] = _unique_namespace_id(result_name, item["warning_id"], used_warning_ids, _stable_fingerprint(item))
            packet_item["evidence_ids"] = [evidence_map[item_id] for item_id in item.get("evidence_ids", [])]
            packet_item["source_calculator"] = result_name
            packet_item["source_calculator_version"] = result_version
            warnings.append(packet_item)
        for item in result_payload["assumptions"]:
            packet_item = copy.deepcopy(item)
            packet_item["assumption_id"] = _unique_namespace_id(result_name, item["assumption_id"], used_assumption_ids, _stable_fingerprint(item))
            packet_item["source_calculator"] = result_name
            packet_item["source_calculator_version"] = result_version
            assumptions.append(packet_item)
    unique_calculators = sorted({(item["name"], item["version"]) for item in calculators})
    return facts, findings, evidence, warnings, assumptions, [{"name": name, "version": version} for name, version in unique_calculators]


def build_evidence_packet(snapshot: dict, calculator_results: list[dict], packet_type: str = PACKET_TYPE) -> dict:
    """Build and validate one deterministic evidence packet."""
    if packet_type != PACKET_TYPE:
        raise UnsupportedPacketType(f"unsupported packet type {packet_type!r}; supported types: {PACKET_TYPE}")
    snapshot = validate_snapshot(snapshot)
    if not isinstance(calculator_results, list):
        raise PacketValidationError("calculator_results must be a list")
    client_id = snapshot["snapshot_metadata"]["client_id"]
    validated_results = []
    for index, result_payload in enumerate(calculator_results):
        raw_result = result_payload.to_dict() if hasattr(result_payload, "to_dict") else result_payload
        _scan_for_recommendations(raw_result, f"calculator_results[{index}]")
        try:
            validated_results.append(validate_result(raw_result))
        except ValueError as exc:
            raise PacketValidationError(f"calculator_results[{index}]: invalid calculator result: {exc}") from exc
    if validated_results:
        first_metadata = validated_results[0].result_metadata
        first_dates = (first_metadata.as_of_date, first_metadata.comparison_date, first_metadata.period_start, first_metadata.period_end)
        for index, result in enumerate(validated_results[1:], start=1):
            result_metadata = result.result_metadata
            dates = (result_metadata.as_of_date, result_metadata.comparison_date, result_metadata.period_start, result_metadata.period_end)
            if dates != first_dates:
                raise PacketValidationError(f"calculator_results[{index}]: dates are incompatible with the first calculator result")
    context, missing_context = _context(snapshot)
    facts, findings, evidence, warnings, assumptions, included_calculators = _result_items(validated_results, snapshot, client_id)
    warnings = _snapshot_warnings(snapshot) + warnings
    if not validated_results:
        warnings.append({
            "warning_id": "packet:W-0001", "warning_type": "missing_calculator_result", "severity": "high",
            "message": "No exposure_changes calculator result was supplied; this packet contains client context and snapshot quality flags only.",
            "evidence_ids": [], "source_reference": {"table": "packet_inputs", "keys": {"client_id": client_id}},
            "source_calculator": "packet", "source_calculator_version": PACKET_VERSION,
        })
    if missing_context:
        warnings.append({
            "warning_id": "packet:W-0002", "warning_type": "omitted_optional_context", "severity": "info",
            "message": f"Optional client context field(s) were unavailable and are represented as null: {', '.join(missing_context)}.",
            "evidence_ids": [], "source_reference": {"table": "clients", "keys": {"client_id": client_id}},
            "source_calculator": "packet", "source_calculator_version": PACKET_VERSION,
        })
    assumptions.append({
        "assumption_id": "packet:A-0001", "description": "Only exposure-change results are included because other calculators are not implemented.",
        "impact": "This packet does not provide liquidity, event, suitability, performance, or recommendation analysis.", "accepted": True,
        "source_calculator": "packet", "source_calculator_version": PACKET_VERSION,
    })
    statuses = [result.result_metadata.status for result in validated_results]
    status = "blocked" if "blocked" in statuses else ("partial" if not validated_results or "partial" in statuses else "complete")
    metadata = snapshot["snapshot_metadata"]
    packet = {
        "packet_metadata": {
            "packet_type": packet_type, "schema_version": PACKET_VERSION, "packet_version": PACKET_VERSION,
            "client_id": client_id, "as_of_date": metadata["as_of_date"],
            "comparison_date": next((result.result_metadata.comparison_date for result in validated_results if result.result_metadata.comparison_date), metadata["period_start"]),
            "period_start": metadata["period_start"], "period_end": metadata["period_end"],
            "input_snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
            "input_snapshot_calculation_version": metadata["calculation_version"],
            "included_calculators": included_calculators, "status": status,
        },
        "client_context": context, "facts": facts, "findings": findings, "evidence": evidence,
        "warnings": warnings, "assumptions": assumptions,
        "governance": {"requires_rm_review": True, "recommendations_allowed": False, "llm_interpretation_allowed": True, "source_data_is_authoritative": True},
    }
    return validate_packet(packet).to_dict()


def build_evidence_packets_for_all_clients(snapshots_by_client: dict[str, dict], results_by_client: dict[str, list[dict]], packet_type: str = PACKET_TYPE) -> list[dict]:
    """Build one packet per supplied client in deterministic order."""
    if not isinstance(snapshots_by_client, dict) or not isinstance(results_by_client, dict):
        raise PacketValidationError("snapshots_by_client and results_by_client must be mappings")
    extra_clients = sorted(set(results_by_client) - set(snapshots_by_client))
    if extra_clients:
        raise PacketValidationError(f"results supplied for clients without snapshots: {', '.join(extra_clients)}")
    packets = []
    for client_id in sorted(snapshots_by_client):
        snapshot = snapshots_by_client[client_id]
        actual_client_id = snapshot.get("snapshot_metadata", {}).get("client_id") if isinstance(snapshot, dict) else None
        if actual_client_id != client_id:
            raise PacketValidationError(f"client {client_id}: snapshot client_id {actual_client_id!r} does not match mapping key")
        try:
            packets.append(build_evidence_packet(snapshot, results_by_client.get(client_id, []), packet_type))
        except Exception as exc:
            if isinstance(exc, PacketValidationError):
                raise PacketValidationError(f"client {client_id}: {exc}") from exc
            raise PacketValidationError(f"client {client_id}: {exc}") from exc
    return packets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a validated exposure-change evidence packet")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--calculator-result", required=True)
    parser.add_argument("--packet-type", default=PACKET_TYPE)
    destination = parser.add_mutually_exclusive_group()
    destination.add_argument("--output", help="Exact output JSON path")
    destination.add_argument("--output-root", help="Root under which the canonical output path is created")
    parser.add_argument("--overwrite", action="store_true", help="Intentionally replace an existing generated output")
    args = parser.parse_args(argv)
    if args.overwrite and not (args.output or args.output_root):
        print("Evidence packet build failed: --overwrite requires --output or --output-root", file=sys.stderr)
        return 1
    try:
        snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
        calculator_result = json.loads(Path(args.calculator_result).read_text(encoding="utf-8"))
        packet = build_evidence_packet(snapshot, [calculator_result], args.packet_type)
        rendered = dumps_packet(packet)
        if args.output_root:
            output_root = Path(args.output_root)
            metadata = packet["packet_metadata"]
            output = evidence_packet_output_path(
                output_root, metadata["client_id"], metadata["packet_type"],
                metadata["comparison_date"], metadata["as_of_date"],
            )
        elif args.output:
            output = Path(args.output)
            output_root = output.parent
        else:
            print(rendered, end="")
            return 0
        metadata = packet["packet_metadata"]
        atomic_write_json(
            output, rendered, output_root=output_root, overwrite=args.overwrite,
            artifact_description=(
                f"{metadata['packet_type']} packet for client {metadata['client_id']}, "
                f"dates {metadata['comparison_date']} to {metadata['as_of_date']}"
            ),
        )
    except (OSError, json.JSONDecodeError, PacketValidationError, OutputPathError, OutputWriteError, ValueError) as exc:
        print(f"Evidence packet build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
