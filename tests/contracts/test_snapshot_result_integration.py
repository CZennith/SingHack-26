from __future__ import annotations

import copy
import json
from pathlib import Path

import duckdb
import pytest

from src.client_snapshot import SnapshotInputError, validate_snapshot
from src.contracts.result_models import RESULT_SCHEMA_VERSION, SNAPSHOT_SCHEMA_VERSION
from src.contracts.serialization import dumps_result, loads_result
from src.contracts.validation import ResultContractError, result_metadata_from_snapshot, validate_result


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "db" / "wealth.duckdb"


def test_snapshot_to_result_contract_round_trip_without_database_writes(client_snapshot_0001):
    snapshot = client_snapshot_0001
    before_mtime = DB_PATH.stat().st_mtime_ns
    con = duckdb.connect(str(DB_PATH.resolve()), read_only=True)
    try:
        before_tables = con.execute("SELECT table_name, table_type FROM information_schema.tables WHERE table_schema = 'main' ORDER BY table_name").fetchall()
        before_counts = {row[0]: row[1] for row in con.execute("SELECT table_name, estimated_size FROM duckdb_tables() ORDER BY table_name").fetchall()}

        validated_snapshot = validate_snapshot(snapshot)
        metadata = validated_snapshot["snapshot_metadata"]
        client_id = metadata["client_id"]
        as_of_date = metadata["as_of_date"]
        period_start = metadata["period_start"]
        period_end = metadata["period_end"]
        snapshot_calculation_version = metadata["calculation_version"]

        result_payload = {
            "result_metadata": result_metadata_from_snapshot(
                validated_snapshot,
                "contract_integration_test",
                "0.0.0",
                status="complete",
            ),
            "facts": [],
            "findings": [],
            "evidence": [],
            "warnings": [],
            "assumptions": [],
            "requires_rm_review": False,
        }
        first_result = validate_result(result_payload)
        serialized = dumps_result(first_result)
        round_tripped = loads_result(serialized)
        second_result = validate_result(round_tripped.to_dict())

        assert first_result == round_tripped == second_result
        output_metadata = second_result.result_metadata
        assert output_metadata.client_id == client_id
        assert output_metadata.as_of_date == as_of_date
        assert output_metadata.period_start == period_start
        assert output_metadata.period_end == period_end
        assert output_metadata.input_snapshot_calculation_version == snapshot_calculation_version
        assert output_metadata.input_snapshot_schema_version == SNAPSHOT_SCHEMA_VERSION
        assert output_metadata.schema_version == RESULT_SCHEMA_VERSION
        assert "input_snapshot_schema_version" in result_payload["result_metadata"]
        assert "schema_version" in result_payload["result_metadata"]
        assert json.loads(serialized)["result_metadata"]["calculator_name"] == "contract_integration_test"
        assert json.loads(serialized)["result_metadata"]["calculator_version"] == "0.0.0"
    finally:
        con.close()
    assert DB_PATH.stat().st_mtime_ns == before_mtime

    reopened = duckdb.connect(str(DB_PATH.resolve()), read_only=True)
    try:
        assert reopened.execute("SELECT table_name, table_type FROM information_schema.tables WHERE table_schema = 'main' ORDER BY table_name").fetchall() == before_tables
        assert {row[0]: row[1] for row in reopened.execute("SELECT table_name, estimated_size FROM duckdb_tables() ORDER BY table_name").fetchall()} == before_counts
    finally:
        reopened.close()


@pytest.mark.parametrize("field,value", [
    ("as_of_date", "2026-02-30"),
    ("period_start", "not-a-date"),
    ("period_end", "2026-13-01"),
])
def test_invalid_snapshot_dates_are_rejected(client_snapshot_0001, field, value):
    invalid = copy.deepcopy(client_snapshot_0001)
    invalid["snapshot_metadata"][field] = value
    with pytest.raises(SnapshotInputError):
        validate_snapshot(invalid)


def test_missing_snapshot_client_id_is_rejected(client_snapshot_0001):
    invalid = copy.deepcopy(client_snapshot_0001)
    del invalid["snapshot_metadata"]["client_id"]
    with pytest.raises(SnapshotInputError, match="client_id"):
        validate_snapshot(invalid)


def test_malformed_result_metadata_is_rejected(client_snapshot_0001):
    metadata = result_metadata_from_snapshot(client_snapshot_0001, "contract_integration_test", "0.0.0")
    payload = {
        "result_metadata": metadata,
        "facts": [], "findings": [], "evidence": [], "warnings": [],
        "assumptions": [], "requires_rm_review": False,
    }
    payload["result_metadata"]["calculator_name"] = ""
    with pytest.raises(ResultContractError, match="calculator_name"):
        validate_result(payload)
