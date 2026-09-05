from __future__ import annotations

import json
from pathlib import Path

import duckdb

from src.calculators.exposure_base import build_exposure_base
from src.calculators.exposure_changes import calculate_exposure_changes
from src.client_snapshot import build_client_snapshot
from src.interpreter.interpreter import interpret_exposure_packet
from src.pipeline.evidence_packet import build_evidence_packet


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "db/wealth.duckdb"


class OneResponseClient:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def interpret(self, packet):
        self.calls += 1
        return self.response


def test_interpreter_preserves_identity_and_separation_for_every_database_client(valid_output_factory):
    connection = duckdb.connect(str(DB_PATH.resolve()), read_only=True)
    try:
        client_ids = [row[0] for row in connection.execute("SELECT client_id FROM clients ORDER BY client_id").fetchall()]
        packets = []
        for client_id in client_ids:
            previous = build_client_snapshot(connection, client_id, "2026-06-30")
            current = build_client_snapshot(connection, client_id, "2026-08-26")
            result = calculate_exposure_changes(build_exposure_base(current), build_exposure_base(previous))
            packets.append(build_evidence_packet(current, [result]))
    finally:
        connection.close()

    assert client_ids
    for client_id, packet in zip(client_ids, packets):
        client = OneResponseClient(valid_output_factory(packet))
        output = interpret_exposure_packet(packet, client)
        metadata = output["interpretation_metadata"]
        assert metadata["client_id"] == client_id
        assert metadata["as_of_date"] == packet["packet_metadata"]["as_of_date"]
        assert metadata["comparison_date"] == packet["packet_metadata"]["comparison_date"]
        rendered = json.dumps(output, sort_keys=True)
        assert not any(other in rendered for other in set(client_ids) - {client_id})
        assert client.calls == 1

