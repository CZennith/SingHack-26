from __future__ import annotations

import duckdb
from pathlib import Path

from src.calculators.exposure_changes import calculate_exposure_changes_for_all_clients
from src.client_snapshot import build_client_snapshot


def test_all_clients_can_compare_latest_two_snapshots():
    db_path = Path(__file__).resolve().parents[2] / "db" / "wealth.duckdb"
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        snapshots = {}
        for client_id, in con.execute("SELECT client_id FROM clients ORDER BY client_id").fetchall():
            snapshots[client_id] = {
                "2026-06-30": build_client_snapshot(con, client_id, "2026-06-30"),
                "2026-08-26": build_client_snapshot(con, client_id, "2026-08-26"),
            }
        results = calculate_exposure_changes_for_all_clients(snapshots)
    finally:
        con.close()
    assert len(results) == 20
    assert [result["result_metadata"]["client_id"] for result in results] == sorted(snapshots)
    for result in results:
        assert result["result_metadata"]["as_of_date"] == "2026-08-26"
        assert result["result_metadata"]["comparison_date"] == "2026-06-30"
        assert all(fact["evidence_ids"] for fact in result["facts"])
