from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.contracts.serialization import generate_json_schema, loads_result
from src.contracts.validation import ResultContractError, UnsupportedResultSchemaVersion, validate_result


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "contracts" / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_fully_populated_result_accepts():
    result = validate_result(load_fixture("exposure_changes_result_v1.json"))
    assert result.result_metadata.schema_version == "1.0.0"
    assert result.facts[0].fact_id == "F-001"
    assert result.findings[0].evidence_ids == ("E-001", "E-002")


def test_partial_result_accepts():
    result = validate_result(load_fixture("partial_result_v1.json"))
    assert result.result_metadata.status == "partial"
    assert len(result.warnings) == 1


@pytest.mark.parametrize("field", ["result_metadata", "facts", "evidence", "findings"])
def test_required_top_level_fields_reject(field):
    payload = load_fixture("exposure_changes_result_v1.json")
    del payload[field]
    with pytest.raises(ResultContractError, match="missing required field"):
        validate_result(payload)


def test_invalid_fixture_missing_evidence_rejects():
    with pytest.raises(ResultContractError, match="missing evidence ID"):
        validate_result(load_fixture("invalid_result_missing_evidence.json"))


def test_invalid_enums_reject():
    payload = load_fixture("partial_result_v1.json")
    payload["result_metadata"]["status"] = "unknown"
    with pytest.raises(ResultContractError, match="status"):
        validate_result(payload)
    payload = load_fixture("exposure_changes_result_v1.json")
    payload["findings"][0]["severity"] = "critical"
    with pytest.raises(ResultContractError, match="severity"):
        validate_result(payload)


def test_invalid_dates_and_ranges_reject():
    payload = load_fixture("exposure_changes_result_v1.json")
    payload["result_metadata"]["as_of_date"] = "2026-02-30"
    with pytest.raises(ResultContractError, match="real calendar date"):
        validate_result(payload)
    payload = load_fixture("exposure_changes_result_v1.json")
    payload["result_metadata"]["period_start"] = "2026-09-01"
    with pytest.raises(ResultContractError, match="period_start"):
        validate_result(payload)
    payload = load_fixture("exposure_changes_result_v1.json")
    payload["result_metadata"]["comparison_date"] = "2026-09-01"
    with pytest.raises(ResultContractError, match="later than as_of_date"):
        validate_result(payload)


@pytest.mark.parametrize("section,item,id_field", [
    ("facts", {"fact_id": "F-001"}, "fact_id"),
    ("findings", {"finding_id": "FIND-001"}, "finding_id"),
    ("evidence", {"evidence_id": "E-001"}, "evidence_id"),
    ("warnings", {"warning_id": "W-001"}, "warning_id"),
    ("assumptions", {"assumption_id": "A-001", "description": "x", "impact": "y", "accepted": True}, "assumption_id"),
])
def test_duplicate_ids_reject(section, item, id_field):
    payload = load_fixture("exposure_changes_result_v1.json")
    if section == "assumptions":
        payload[section] = [item, dict(item)]
    else:
        payload[section].append(copy.deepcopy(payload[section][0]))
    with pytest.raises(ResultContractError, match="unique"):
        validate_result(payload)


def test_monetary_fact_requires_currency():
    payload = load_fixture("exposure_changes_result_v1.json")
    payload["facts"][0]["unit"] = "amount"
    payload["facts"][0]["currency"] = None
    with pytest.raises(ResultContractError, match="monetary"):
        validate_result(payload)


def test_blocked_result_requires_warning_and_unknown_fields_reject():
    payload = load_fixture("partial_result_v1.json")
    payload["result_metadata"]["status"] = "blocked"
    payload["warnings"] = []
    with pytest.raises(ResultContractError, match="blocked"):
        validate_result(payload)
    payload = load_fixture("partial_result_v1.json")
    payload["recommendation"] = "do something"
    with pytest.raises(ResultContractError, match="unexpected"):
        validate_result(payload)


def test_generated_schema_validates_example_and_matches_file():
    jsonschema = pytest.importorskip("jsonschema")
    schema = generate_json_schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(load_fixture("exposure_changes_result_v1.json"))
    schema_file = ROOT / "docs" / "contracts" / "analysis_result.schema.json"
    assert json.loads(schema_file.read_text(encoding="utf-8")) == schema


def test_json_round_trip_is_equivalent():
    payload = load_fixture("exposure_changes_result_v1.json")
    first = validate_result(payload)
    encoded = json.dumps(first.to_dict(), allow_nan=False)
    second = loads_result(encoded)
    assert first == second
