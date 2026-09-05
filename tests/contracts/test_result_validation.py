from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.contracts.validation import ResultContractError, validate_result


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "contracts" / "fixtures" / "exposure_changes_result_v1.json"


def payload():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_finding_must_have_supporting_evidence():
    item = payload()
    item["findings"][0]["evidence_ids"] = []
    with pytest.raises(ResultContractError, match="supporting evidence"):
        validate_result(item)


def test_finding_must_reference_existing_fact():
    item = payload()
    item["findings"][0]["fact_ids"] = ["F-MISSING"]
    with pytest.raises(ResultContractError, match="missing fact"):
        validate_result(item)


def test_non_json_values_reject():
    item = payload()
    item["facts"][0]["current_value"] = float("nan")
    with pytest.raises(ResultContractError, match="JSON-serializable"):
        validate_result(item)
