from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.pipeline.evidence_packet import build_evidence_packet
from src.pipeline.packet_validation import PacketValidationError, UnsupportedPacketType, validate_packet


ROOT = Path(__file__).resolve().parents[2]
RESULT = json.loads((ROOT / "tests" / "contracts" / "fixtures" / "exposure_changes_result_v1.json").read_text(encoding="utf-8"))


def test_client_mismatch_is_rejected(client_snapshot_0001):
    result = copy.deepcopy(RESULT)
    result["result_metadata"]["client_id"] = "CL-0002"
    with pytest.raises(PacketValidationError, match="client_id"):
        build_evidence_packet(client_snapshot_0001, [result])


@pytest.mark.parametrize(("field", "value"), [
    ("as_of_date", "2026-08-25"),
    ("period_start", "2026-02-01"),
    ("period_end", "2026-08-25"),
])
def test_incompatible_dates_are_rejected(client_snapshot_0001, field, value):
    result = copy.deepcopy(RESULT)
    result["result_metadata"][field] = value
    with pytest.raises(PacketValidationError, match="(date|period)"):
        build_evidence_packet(client_snapshot_0001, [result])


def test_missing_fact_or_evidence_references_are_rejected(client_snapshot_0001):
    packet = build_evidence_packet(client_snapshot_0001, [RESULT])
    packet["findings"][0]["fact_ids"] = ["missing-fact"]
    with pytest.raises(PacketValidationError, match="missing fact"):
        validate_packet(packet)

    packet = build_evidence_packet(client_snapshot_0001, [RESULT])
    packet["findings"][0]["evidence_ids"] = ["missing-evidence"]
    with pytest.raises(PacketValidationError, match="missing evidence"):
        validate_packet(packet)


def test_recommendation_fields_are_rejected(client_snapshot_0001):
    result = copy.deepcopy(RESULT)
    result["recommended_action"] = "rebalance"
    with pytest.raises(PacketValidationError, match="recommendation"):
        build_evidence_packet(client_snapshot_0001, [result])


@pytest.mark.parametrize("packet_type", ["liquidity_review", "market_event_review"])
def test_unsupported_packet_type_is_rejected(client_snapshot_0001, packet_type):
    with pytest.raises(UnsupportedPacketType, match="unsupported"):
        build_evidence_packet(client_snapshot_0001, [RESULT], packet_type)


def test_missing_calculator_result_is_explicitly_partial(client_snapshot_0001):
    packet = build_evidence_packet(client_snapshot_0001, [])
    assert packet["packet_metadata"]["status"] == "partial"
    assert packet["packet_metadata"]["included_calculators"] == []
    assert any(item["warning_type"] == "missing_calculator_result" for item in packet["warnings"])
    validate_packet(packet)


def test_privacy_filter_excludes_sensitive_client_fields(client_snapshot_0001):
    packet = build_evidence_packet(client_snapshot_0001, [RESULT])
    assert set(packet["client_context"]) == {
        "client_id", "base_currency", "risk_profile", "risk_tolerance_score",
        "investment_horizon_years", "liquidity_needs", "objectives", "life_stage",
    }
    serialized = json.dumps(packet)
    assert "client_name" not in serialized
    assert "source_of_wealth" not in serialized
    assert "pep_status" not in serialized


def test_invalid_packet_metadata_and_governance_are_rejected(client_snapshot_0001):
    packet = build_evidence_packet(client_snapshot_0001, [RESULT])
    packet["packet_metadata"]["status"] = "unknown"
    with pytest.raises(PacketValidationError, match="status"):
        validate_packet(packet)

    packet = build_evidence_packet(client_snapshot_0001, [RESULT])
    packet["governance"]["recommendations_allowed"] = True
    with pytest.raises(PacketValidationError, match="recommendations_allowed"):
        validate_packet(packet)
