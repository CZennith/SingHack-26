from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from src.output_paths import (
    OutputPathError,
    evidence_packet_output_path,
    exposure_change_output_path,
    interpretation_output_path,
    require_unique_output_paths,
    snapshot_output_path,
)


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "db" / "wealth.duckdb"


def test_canonical_paths_are_deterministic_for_any_client(tmp_path):
    output_root = tmp_path / "not-created"
    assert snapshot_output_path(
        output_root, "CLIENT-42", "2026-08-26", "2026-01-01", "2026-08-26"
    ) == output_root / "snapshots/CLIENT-42/as_of_2026-08-26__period_2026-01-01_to_2026-08-26.json"
    assert exposure_change_output_path(
        output_root, "CLIENT-42", "2026-06-30", "2026-08-26"
    ) == output_root / "exposure_changes/CLIENT-42/2026-06-30_to_2026-08-26.json"
    assert evidence_packet_output_path(
        output_root, "CLIENT-42", "exposure_change_review", "2026-06-30", "2026-08-26"
    ) == output_root / "evidence_packets/CLIENT-42/exposure_change_review__2026-06-30_to_2026-08-26.json"
    assert interpretation_output_path(
        output_root, "CLIENT-42", "exposure_change_review", "2026-06-30", "2026-08-26"
    ) == output_root / "interpretations/CLIENT-42/exposure_change_review__2026-06-30_to_2026-08-26.json"
    assert not output_root.exists(), "pure path construction must not access the filesystem"


def test_every_database_client_gets_one_unique_client_specific_path(tmp_path):
    connection = duckdb.connect(str(DB_PATH.resolve()), read_only=True)
    try:
        client_ids = [row[0] for row in connection.execute("SELECT client_id FROM clients ORDER BY client_id").fetchall()]
    finally:
        connection.close()
    paths = [
        snapshot_output_path(tmp_path, client_id, "2026-08-26", "2026-06-30", "2026-08-26")
        for client_id in client_ids
    ]
    require_unique_output_paths(paths)
    assert len(paths) == len(client_ids) == len(set(paths))
    assert all(client_id in path.parts for client_id, path in zip(client_ids, paths))


def test_multiple_snapshot_dates_and_periods_never_collide(tmp_path):
    dates = ("2026-01-31", "2026-04-30", "2026-06-30", "2026-07-31", "2026-08-26")
    date_paths = [snapshot_output_path(tmp_path, "CLIENT-X", value, value, value) for value in dates]
    period_paths = [
        snapshot_output_path(tmp_path, "CLIENT-X", "2026-08-26", start, "2026-08-26")
        for start in ("2026-01-01", "2026-04-30", "2026-06-30")
    ]
    require_unique_output_paths(date_paths)
    require_unique_output_paths(period_paths)
    assert len(set(date_paths)) == len(dates)
    assert len(set(period_paths)) == 3


def test_duplicate_batch_paths_are_rejected(tmp_path):
    path = snapshot_output_path(tmp_path, "CLIENT-X", "2026-08-26", "2026-06-30", "2026-08-26")
    with pytest.raises(OutputPathError, match="collisions"):
        require_unique_output_paths([path, path])


@pytest.mark.parametrize("unsafe", ["../CLIENT", "CLIENT/OTHER", r"CLIENT\\OTHER", "CLIENT X", ".."])
def test_unsafe_client_path_components_are_rejected(tmp_path, unsafe):
    with pytest.raises(OutputPathError):
        snapshot_output_path(tmp_path, unsafe, "2026-08-26", "2026-01-01", "2026-08-26")


@pytest.mark.parametrize("unsafe", ["../review", "review/packet", r"review\\packet", "review packet", ".."])
def test_unsafe_packet_type_components_are_rejected(tmp_path, unsafe):
    with pytest.raises(OutputPathError):
        evidence_packet_output_path(tmp_path, "CLIENT-X", unsafe, "2026-06-30", "2026-08-26")


@pytest.mark.parametrize("invalid_date", ["2026-02-30", "2026/08/26", "26-08-2026", "2026-8-26"])
def test_invalid_date_components_are_rejected(tmp_path, invalid_date):
    with pytest.raises(OutputPathError):
        snapshot_output_path(tmp_path, "CLIENT-X", invalid_date, "2026-01-01", "2026-08-26")
