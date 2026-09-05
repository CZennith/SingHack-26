"""Canonical, side-effect-free paths for generated JSON artifacts."""

from __future__ import annotations

import re
from collections import Counter
from datetime import date
from pathlib import Path


_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class OutputPathError(ValueError):
    """An output path component is unsafe or malformed."""


def _component(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise OutputPathError(f"{field} must be a non-empty string")
    if value in {".", ".."} or ".." in value or "/" in value or "\\" in value:
        raise OutputPathError(f"{field} contains path traversal or a path separator")
    if not _SAFE_COMPONENT.fullmatch(value):
        raise OutputPathError(f"{field} contains invalid filename characters")
    return value


def _date_component(value: str, field: str) -> str:
    value = _component(value, field)
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise OutputPathError(f"{field} must be a real ISO date in YYYY-MM-DD format") from exc
    if parsed.isoformat() != value:
        raise OutputPathError(f"{field} must be an ISO date in YYYY-MM-DD format")
    return value


def snapshot_output_path(
    output_root: Path,
    client_id: str,
    as_of_date: str,
    period_start: str,
    period_end: str,
) -> Path:
    """Return the canonical snapshot path without touching the filesystem."""
    client = _component(client_id, "client_id")
    as_of = _date_component(as_of_date, "as_of_date")
    start = _date_component(period_start, "period_start")
    end = _date_component(period_end, "period_end")
    if start > end:
        raise OutputPathError("period_start must be on or before period_end")
    return Path(output_root) / "snapshots" / client / f"as_of_{as_of}__period_{start}_to_{end}.json"


def exposure_change_output_path(
    output_root: Path,
    client_id: str,
    comparison_date: str,
    as_of_date: str,
) -> Path:
    """Return the canonical exposure-change path without filesystem access."""
    client = _component(client_id, "client_id")
    comparison = _date_component(comparison_date, "comparison_date")
    as_of = _date_component(as_of_date, "as_of_date")
    if comparison > as_of:
        raise OutputPathError("comparison_date must be on or before as_of_date")
    return Path(output_root) / "exposure_changes" / client / f"{comparison}_to_{as_of}.json"


def evidence_packet_output_path(
    output_root: Path,
    client_id: str,
    packet_type: str,
    comparison_date: str,
    as_of_date: str,
) -> Path:
    """Return the canonical evidence-packet path without filesystem access."""
    client = _component(client_id, "client_id")
    kind = _component(packet_type, "packet_type")
    comparison = _date_component(comparison_date, "comparison_date")
    as_of = _date_component(as_of_date, "as_of_date")
    if comparison > as_of:
        raise OutputPathError("comparison_date must be on or before as_of_date")
    return Path(output_root) / "evidence_packets" / client / f"{kind}__{comparison}_to_{as_of}.json"


def interpretation_output_path(
    output_root: Path,
    client_id: str,
    packet_type: str,
    comparison_date: str,
    as_of_date: str,
) -> Path:
    """Return the canonical interpretation path without filesystem access."""
    client = _component(client_id, "client_id")
    kind = _component(packet_type, "packet_type")
    comparison = _date_component(comparison_date, "comparison_date")
    as_of = _date_component(as_of_date, "as_of_date")
    if comparison > as_of:
        raise OutputPathError("comparison_date must be on or before as_of_date")
    return Path(output_root) / "interpretations" / client / f"{kind}__{comparison}_to_{as_of}.json"


def require_unique_output_paths(paths: list[Path]) -> None:
    """Reject a batch containing duplicate intended output paths."""
    rendered = [str(path) for path in paths]
    duplicates = sorted(path for path, count in Counter(rendered).items() if count > 1)
    if duplicates:
        raise OutputPathError(f"batch output paths must be unique; collisions: {', '.join(duplicates)}")
