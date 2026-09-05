from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.pipeline.evidence_packet import build_evidence_packet
from src.pipeline.packet_serialization import dumps_packet, loads_packet
from src.pipeline.packet_validation import PacketValidationError


ROOT = Path(__file__).resolve().parents[2]
RESULT = json.loads((ROOT / "tests" / "contracts" / "fixtures" / "exposure_changes_result_v1.json").read_text(encoding="utf-8"))


def test_multiple_results_with_incompatible_dates_are_rejected(client_snapshot_0001):
    second = copy.deepcopy(RESULT)
    second["result_metadata"]["period_end"] = "2026-08-25"
    with pytest.raises(PacketValidationError, match="incompatible"):
        build_evidence_packet(client_snapshot_0001, [RESULT, second])


def test_malformed_evidence_cannot_become_untraceable(client_snapshot_0001):
    result = copy.deepcopy(RESULT)
    del result["evidence"][0]["source_keys"]["client_id"]
    with pytest.raises(PacketValidationError, match="traceable"):
        build_evidence_packet(client_snapshot_0001, [result])


def test_packet_round_trip_rejects_invalid_json():
    with pytest.raises(ValueError, match="Invalid evidence packet JSON"):
        loads_packet("not json")


def test_blocked_packet_requires_a_warning(client_snapshot_0001):
    packet = build_evidence_packet(client_snapshot_0001, [RESULT])
    packet["packet_metadata"]["status"] = "blocked"
    packet["warnings"] = []
    with pytest.raises(PacketValidationError, match="blocked"):
        dumps_packet(packet)
