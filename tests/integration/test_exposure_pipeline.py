from __future__ import annotations

import json
from pathlib import Path

import duckdb

from src.calculators.exposure_base import build_exposure_base
from src.calculators.exposure_changes import calculate_exposure_changes
from src.client_snapshot import build_client_snapshot, validate_snapshot
from src.contracts.serialization import dumps_result, loads_result
from src.contracts.validation import validate_result


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "db" / "wealth.duckdb"


def test_real_database_exposure_pipeline_for_every_client():
    before_mtime = DB_PATH.stat().st_mtime_ns
    con = duckdb.connect(str(DB_PATH.resolve()), read_only=True)
    try:
        before_schema = con.execute("SELECT table_name, table_type FROM information_schema.tables WHERE table_schema = 'main' ORDER BY table_name").fetchall()
        before_sizes = con.execute("SELECT table_name, estimated_size FROM duckdb_tables() ORDER BY table_name").fetchall()
        client_ids = [row[0] for row in con.execute("SELECT client_id FROM clients ORDER BY client_id").fetchall()]
        assert client_ids

        # A write against the main database must fail because this connection
        # was explicitly opened read-only.
        try:
            con.execute("CREATE TABLE main.integration_read_only_probe (probe INTEGER)")
        except duckdb.Error:
            pass
        else:
            raise AssertionError("The integration connection was not read-only")

        for client_id in client_ids:
            previous_snapshot = validate_snapshot(build_client_snapshot(con, client_id, "2026-06-30"))
            current_snapshot = validate_snapshot(build_client_snapshot(con, client_id, "2026-08-26"))
            previous_exposure = build_exposure_base(previous_snapshot)
            current_exposure = build_exposure_base(current_snapshot)
            result = calculate_exposure_changes(current_exposure, previous_exposure)
            validated_result = validate_result(result)
            round_tripped = loads_result(dumps_result(validated_result))
            final_result = validate_result(round_tripped.to_dict())

            assert final_result.result_metadata.client_id == client_id
            assert final_result.result_metadata.as_of_date == "2026-08-26"
            assert final_result.result_metadata.comparison_date == "2026-06-30"
            assert all(ref["keys"].get("client_id") == client_id for ref in current_exposure["source_references"])
            assert all(evidence.source_keys.get("client_id") == client_id for evidence in final_result.evidence)
            assert all(fact.scope.client_id == client_id for fact in final_result.facts)

            # No other database client identifier may appear in the client's
            # direct exposure evidence or result payload.
            other_client_ids = set(client_ids) - {client_id}
            current_text = json.dumps(current_exposure, sort_keys=True)
            result_text = json.dumps(final_result.to_dict(), sort_keys=True)
            assert not any(other_id in current_text for other_id in other_client_ids)
            assert not any(other_id in result_text for other_id in other_client_ids)

    finally:
        con.close()

    assert DB_PATH.stat().st_mtime_ns == before_mtime
    reopened = duckdb.connect(str(DB_PATH.resolve()), read_only=True)
    try:
        assert reopened.execute("SELECT table_name, table_type FROM information_schema.tables WHERE table_schema = 'main' ORDER BY table_name").fetchall() == before_schema
        assert reopened.execute("SELECT table_name, estimated_size FROM duckdb_tables() ORDER BY table_name").fetchall() == before_sizes
    finally:
        reopened.close()
