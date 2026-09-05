from __future__ import annotations

import json
from pathlib import Path

import duckdb

from src.calculators.exposure_base import build_exposure_base
from src.calculators.exposure_changes import calculate_exposure_changes
from src.client_snapshot import build_client_snapshot
from src.pipeline.evidence_packet import build_evidence_packets_for_all_clients
from src.pipeline.packet_validation import validate_packet


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "db" / "wealth.duckdb"


def test_packet_construction_preserves_separation_for_every_database_client():
    before_db_mtime = DB_PATH.stat().st_mtime_ns
    con = duckdb.connect(str(DB_PATH.resolve()), read_only=True)
    try:
        before_schema = con.execute("SELECT table_name, table_type FROM information_schema.tables WHERE table_schema = 'main' ORDER BY table_name").fetchall()
        client_ids = [row[0] for row in con.execute("SELECT client_id FROM clients ORDER BY client_id").fetchall()]
        snapshots = {}
        results = {}
        for client_id in client_ids:
            previous = build_client_snapshot(con, client_id, "2026-06-30")
            current = build_client_snapshot(con, client_id, "2026-08-26")
            snapshots[client_id] = current
            results[client_id] = [calculate_exposure_changes(build_exposure_base(current), build_exposure_base(previous))]
        packets = build_evidence_packets_for_all_clients(snapshots, results)
    finally:
        con.close()

    assert [packet["packet_metadata"]["client_id"] for packet in packets] == client_ids
    for client_id, packet in zip(client_ids, packets):
        validate_packet(packet)
        assert packet["packet_metadata"]["as_of_date"] == "2026-08-26"
        text = json.dumps(packet, sort_keys=True)
        assert not any(other_id in text for other_id in set(client_ids) - {client_id})

    assert DB_PATH.stat().st_mtime_ns == before_db_mtime
    reopened = duckdb.connect(str(DB_PATH.resolve()), read_only=True)
    try:
        assert reopened.execute("SELECT table_name, table_type FROM information_schema.tables WHERE table_schema = 'main' ORDER BY table_name").fetchall() == before_schema
    finally:
        reopened.close()
