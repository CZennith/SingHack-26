from __future__ import annotations

import copy
import json
from pathlib import Path

from src.pipeline.evidence_packet import build_evidence_packet
from src.pipeline.packet_serialization import dumps_packet, loads_packet
from src.pipeline.packet_validation import validate_packet


ROOT = Path(__file__).resolve().parents[2]
RESULT_FIXTURE = json.loads((ROOT / "tests" / "contracts" / "fixtures" / "exposure_changes_result_v1.json").read_text(encoding="utf-8"))


def test_valid_exposure_review_packet_preserves_context_provenance_and_governance(client_snapshot_0001):
    packet = build_evidence_packet(client_snapshot_0001, [RESULT_FIXTURE])
    validated = validate_packet(packet)

    assert packet["packet_metadata"]["packet_type"] == "exposure_change_review"
    assert packet["packet_metadata"]["client_id"] == "CL-0001"
    assert packet["packet_metadata"]["as_of_date"] == "2026-08-26"
    assert packet["packet_metadata"]["comparison_date"] == "2026-06-30"
    assert packet["packet_metadata"]["included_calculators"] == [{"name": "exposure_changes", "version": "1.0.0"}]
    assert packet["client_context"]["objectives"] == client_snapshot_0001["client"]["objectives"]
    assert packet["client_context"]["client_id"] == "CL-0001"
    assert packet["facts"][0]["fact_id"] == "exposure_changes:F-001"
    assert packet["facts"][0]["source_calculator_version"] == "1.0.0"
    assert packet["findings"][0]["finding_id"] == "exposure_changes:FIND-001"
    assert packet["evidence"][0]["evidence_id"] == "exposure_changes:E-001"
    assert len(packet["warnings"]) > len(RESULT_FIXTURE["warnings"])
    assert packet["governance"] == {
        "requires_rm_review": True,
        "recommendations_allowed": False,
        "llm_interpretation_allowed": True,
        "source_data_is_authoritative": True,
    }
    assert validated.to_dict() == packet


def test_packet_json_round_trip_is_equivalent_and_deterministic(client_snapshot_0001):
    first = build_evidence_packet(client_snapshot_0001, [RESULT_FIXTURE])
    second = build_evidence_packet(client_snapshot_0001, [RESULT_FIXTURE])
    assert dumps_packet(first) == dumps_packet(second)
    assert loads_packet(dumps_packet(first)).to_dict() == first


def test_evidence_is_deduplicated_only_when_all_source_fields_match(client_snapshot_0001):
    duplicate = copy.deepcopy(RESULT_FIXTURE)
    duplicate["facts"][0]["fact_id"] = "F-002"
    duplicate["findings"][0]["finding_id"] = "FIND-002"
    duplicate["findings"][0]["fact_ids"] = ["F-002"]
    packet = build_evidence_packet(client_snapshot_0001, [RESULT_FIXTURE, duplicate])
    assert len(packet["evidence"]) == 2
    assert packet["facts"][1]["evidence_ids"] == packet["facts"][0]["evidence_ids"]

    distinct = copy.deepcopy(duplicate)
    distinct["evidence"][0]["source_keys"]["instrument_id"] = "SYN-DISTINCT"
    packet = build_evidence_packet(client_snapshot_0001, [RESULT_FIXTURE, distinct])
    assert len(packet["evidence"]) == 3
    assert len({item["evidence_id"] for item in packet["evidence"]}) == 3


def test_snapshot_warnings_are_preserved_with_source_references(client_snapshot_0001):
    packet = build_evidence_packet(client_snapshot_0001, [RESULT_FIXTURE])
    snapshot_warning_ids = {item["warning_id"] for item in packet["warnings"] if item["source_calculator"] == "snapshot"}
    assert len(snapshot_warning_ids) == len(client_snapshot_0001["data_quality_flags"])
    assert all(item["source_reference"] for item in packet["warnings"] if item["source_calculator"] == "snapshot")
    result_warning = next(item for item in packet["warnings"] if item["source_calculator"] == "exposure_changes")
    assert result_warning["severity"] == RESULT_FIXTURE["warnings"][0]["severity"]
