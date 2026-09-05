from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.output_files import OutputExistsError, OutputWriteError, UnsafeOutputTarget, atomic_write_json


ROOT = Path(__file__).resolve().parents[2]


def test_existing_output_is_unchanged_without_overwrite(tmp_path):
    output_root = tmp_path / "outputs"
    target = output_root / "snapshots/CLIENT-X/snapshot.json"
    target.parent.mkdir(parents=True)
    target.write_text('{"version": "original"}\n', encoding="utf-8")

    with pytest.raises(OutputExistsError) as raised:
        atomic_write_json(
            target,
            '{"version": "replacement"}\n',
            output_root=output_root,
            artifact_description="snapshot for client CLIENT-X, dates 2026-06-30 to 2026-08-26",
        )

    assert target.read_text(encoding="utf-8") == '{"version": "original"}\n'
    message = str(raised.value)
    assert str(target.resolve()) in message
    assert "CLIENT-X" in message
    assert "2026-06-30" in message and "2026-08-26" in message
    assert "--overwrite" in message


def test_explicit_overwrite_atomically_replaces_valid_json(tmp_path):
    output_root = tmp_path / "outputs"
    target = output_root / "exposure_changes/CLIENT-X/result.json"
    target.parent.mkdir(parents=True)
    target.write_text('{"version": "original"}\n', encoding="utf-8")

    written = atomic_write_json(
        target,
        '{"version": "replacement"}\n',
        output_root=output_root,
        overwrite=True,
        artifact_description="exposure change for client CLIENT-X",
    )

    assert written == target.resolve()
    assert json.loads(target.read_text(encoding="utf-8")) == {"version": "replacement"}
    assert not list(target.parent.glob(".*.tmp"))


def test_replace_failure_leaves_existing_file_and_no_temporary_file(tmp_path, monkeypatch):
    output_root = tmp_path / "outputs"
    target = output_root / "snapshots/CLIENT-X/snapshot.json"
    target.parent.mkdir(parents=True)
    original = b'{"version": "original"}\n'
    target.write_bytes(original)

    def fail_replace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr("src.output_files.os.replace", fail_replace)
    with pytest.raises(OSError, match="simulated"):
        atomic_write_json(
            target,
            '{"version": "replacement"}\n',
            output_root=output_root,
            overwrite=True,
            artifact_description="snapshot for client CLIENT-X",
        )

    assert target.read_bytes() == original
    assert [path for path in target.parent.iterdir() if path != target] == []


def test_serialization_failure_leaves_existing_file_unchanged(tmp_path):
    output_root = tmp_path / "outputs"
    target = output_root / "snapshots/CLIENT-X/snapshot.json"
    target.parent.mkdir(parents=True)
    original = b'{"version": "original"}\n'
    target.write_bytes(original)

    with pytest.raises(OutputWriteError, match="invalid JSON"):
        atomic_write_json(
            target,
            "{not-json",
            output_root=output_root,
            overwrite=True,
            artifact_description="snapshot for client CLIENT-X",
        )

    assert target.read_bytes() == original
    assert [path for path in target.parent.iterdir() if path != target] == []


def test_targets_outside_output_root_and_protected_fixtures_are_rejected(tmp_path):
    output_root = tmp_path / "outputs"
    outside = tmp_path / "outside.json"
    with pytest.raises(UnsafeOutputTarget, match="outside"):
        atomic_write_json(
            outside, "{}", output_root=output_root, overwrite=True,
            artifact_description="outside test",
        )
    protected = ROOT / "tests/fixtures/snapshots/forbidden.json"
    with pytest.raises(UnsafeOutputTarget, match="protected"):
        atomic_write_json(
            protected, "{}", output_root=protected.parent, overwrite=True,
            artifact_description="protected fixture test",
        )
    assert not outside.exists()
    assert not protected.exists()


def test_repository_source_json_cannot_be_replaced_even_with_overwrite():
    source_file = ROOT / "package.json"
    original = source_file.read_bytes()
    with pytest.raises(UnsafeOutputTarget, match="repository"):
        atomic_write_json(
            source_file, '{"destroyed": true}', output_root=ROOT, overwrite=True,
            artifact_description="source overwrite probe",
        )
    assert source_file.read_bytes() == original


@pytest.mark.parametrize(("payload", "message"), [("[]", "non-object"), ('{"value": NaN}', "invalid JSON")])
def test_non_object_or_nonstandard_json_is_rejected_before_creating_a_file(tmp_path, payload, message):
    output_root = tmp_path / "outputs"
    target = output_root / "result.json"
    with pytest.raises(OutputWriteError, match=message):
        atomic_write_json(
            target, payload, output_root=output_root,
            artifact_description="invalid artifact envelope",
        )
    assert not target.exists()
