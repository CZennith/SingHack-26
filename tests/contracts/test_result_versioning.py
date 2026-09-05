from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.contracts.validation import UnsupportedResultSchemaVersion, result_metadata_from_snapshot, validate_result


ROOT = Path(__file__).resolve().parents[2]


def test_version_dispatch_accepts_v1():
    payload = json.loads((ROOT / "tests/contracts/fixtures/exposure_changes_result_v1.json").read_text(encoding="utf-8"))
    assert validate_result(payload).result_metadata.schema_version == "1.0.0"


def test_unsupported_version_is_explicitly_rejected():
    payload = json.loads((ROOT / "tests/contracts/fixtures/exposure_changes_result_v1.json").read_text(encoding="utf-8"))
    payload["result_metadata"]["schema_version"] = "2.0.0"
    with pytest.raises(UnsupportedResultSchemaVersion, match="unsupported version"):
        validate_result(payload)


def test_existing_snapshot_metadata_maps_without_converting_snapshot(client_snapshot_0001):
    snapshot = client_snapshot_0001
    original = copy.deepcopy(snapshot)
    metadata = result_metadata_from_snapshot(snapshot, "exposure_changes", "1.0.0", comparison_date="2026-06-30")
    assert metadata["schema_version"] == "1.0.0"
    assert metadata["input_snapshot_schema_version"] == "1.0.0"
    assert metadata["input_snapshot_calculation_version"] == "1.0.0"
    assert metadata["client_id"] == "CL-0001"
    assert metadata["as_of_date"] == "2026-08-26"
    assert metadata["period_start"] == "2026-01-01"
    assert metadata["period_end"] == "2026-08-26"
    assert snapshot == original
