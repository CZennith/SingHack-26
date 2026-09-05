from __future__ import annotations

import copy
import json
from pathlib import Path

import duckdb

from src.calculators.exposure_base import build_exposure_base
from src.calculators.exposure_changes import calculate_exposure_changes, main as exposure_main
from src.client_snapshot import build_client_snapshot, main as snapshot_main, validate_snapshot
from src.contracts.validation import validate_result
from src.output_paths import evidence_packet_output_path, exposure_change_output_path, snapshot_output_path
from src.pipeline.evidence_packet import build_evidence_packet, main as packet_main
from src.pipeline.packet_validation import validate_packet


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "db" / "wealth.duckdb"


def _snapshot_args(output_root: Path | None = None) -> list[str]:
    args = [
        "--db-path", str(DB_PATH),
        "--client-id", "CL-0001",
        "--as-of-date", "2026-08-26",
        "--period-start", "2026-01-01",
        "--period-end", "2026-08-26",
    ]
    if output_root is not None:
        args.extend(("--output-root", str(output_root)))
    return args


def _previous_snapshot() -> dict:
    connection = duckdb.connect(str(DB_PATH.resolve()), read_only=True)
    try:
        return build_client_snapshot(connection, "CL-0001", "2026-06-30")
    finally:
        connection.close()


def test_snapshot_cli_stdout_is_valid_json_and_creates_no_files(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert snapshot_main(_snapshot_args()) == 0
    captured = capsys.readouterr()
    snapshot = validate_snapshot(json.loads(captured.out))
    assert snapshot["snapshot_metadata"]["client_id"] == "CL-0001"
    assert captured.err == ""
    assert list(tmp_path.iterdir()) == []


def test_snapshot_cli_uses_canonical_path_and_requires_explicit_overwrite(tmp_path, capsys):
    output_root = tmp_path / "generated"
    target = snapshot_output_path(
        output_root, "CL-0001", "2026-08-26", "2026-01-01", "2026-08-26"
    )
    target.parent.mkdir(parents=True)
    original = '{"legacy": true}\n'
    target.write_text(original, encoding="utf-8")

    assert snapshot_main(_snapshot_args(output_root)) == 1
    captured = capsys.readouterr()
    assert str(target.resolve()) in captured.err
    assert "CL-0001" in captured.err
    assert "2026-01-01" in captured.err and "2026-08-26" in captured.err
    assert "--overwrite" in captured.err
    assert target.read_text(encoding="utf-8") == original

    assert snapshot_main([*_snapshot_args(output_root), "--overwrite"]) == 0
    assert validate_snapshot(json.loads(target.read_text(encoding="utf-8")))["snapshot_metadata"]["client_id"] == "CL-0001"


def test_snapshot_cli_accepts_an_exact_output_path(tmp_path):
    target = tmp_path / "custom-name.json"
    assert snapshot_main([*_snapshot_args(), "--output", str(target)]) == 0
    assert validate_snapshot(json.loads(target.read_text(encoding="utf-8")))["snapshot_metadata"]["client_id"] == "CL-0001"


def test_snapshot_batch_cli_writes_one_unique_file_per_database_client(tmp_path):
    output_root = tmp_path / "generated"
    assert snapshot_main([
        "--db-path", str(DB_PATH),
        "--all-clients",
        "--as-of-date", "2026-08-26",
        "--period-start", "2026-06-30",
        "--period-end", "2026-08-26",
        "--output-root", str(output_root),
    ]) == 0
    connection = duckdb.connect(str(DB_PATH.resolve()), read_only=True)
    try:
        client_ids = [row[0] for row in connection.execute("SELECT client_id FROM clients ORDER BY client_id").fetchall()]
    finally:
        connection.close()
    files = sorted((output_root / "snapshots").glob("*/*.json"))
    assert len(files) == len(client_ids) == len(set(files))
    assert [json.loads(path.read_text(encoding="utf-8"))["snapshot_metadata"]["client_id"] for path in files] == client_ids


def test_exposure_and_packet_clis_use_their_canonical_paths(tmp_path, client_snapshot_0001):
    input_root = tmp_path / "inputs"
    input_root.mkdir()
    current_path = input_root / "current.json"
    previous_path = input_root / "previous.json"
    current_path.write_text(json.dumps(client_snapshot_0001), encoding="utf-8")
    previous_path.write_text(json.dumps(_previous_snapshot()), encoding="utf-8")
    output_root = tmp_path / "generated"

    assert exposure_main([
        "--current-snapshot", str(current_path),
        "--previous-snapshot", str(previous_path),
        "--output-root", str(output_root),
    ]) == 0
    result_path = exposure_change_output_path(
        output_root, "CL-0001", "2026-06-30", "2026-08-26"
    )
    result = validate_result(json.loads(result_path.read_text(encoding="utf-8"))).to_dict()

    assert packet_main([
        "--snapshot", str(current_path),
        "--calculator-result", str(result_path),
        "--output-root", str(output_root),
    ]) == 0
    packet_path = evidence_packet_output_path(
        output_root, "CL-0001", "exposure_change_review", "2026-06-30", "2026-08-26"
    )
    packet = validate_packet(json.loads(packet_path.read_text(encoding="utf-8"))).to_dict()
    assert packet["packet_metadata"]["client_id"] == result["result_metadata"]["client_id"] == "CL-0001"


def test_core_pipeline_functions_create_no_files(tmp_path, monkeypatch, client_snapshot_0001):
    monkeypatch.chdir(tmp_path)
    current = copy.deepcopy(client_snapshot_0001)
    previous = _previous_snapshot()
    current_exposure = build_exposure_base(current)
    previous_exposure = build_exposure_base(previous)
    result = calculate_exposure_changes(current_exposure, previous_exposure)
    packet = build_evidence_packet(current, [result])

    assert result["result_metadata"]["client_id"] == "CL-0001"
    assert packet["packet_metadata"]["client_id"] == "CL-0001"
    assert list(tmp_path.iterdir()) == []
