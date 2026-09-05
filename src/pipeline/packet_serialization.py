"""JSON serialization for evidence packet v1."""

from __future__ import annotations

import json
from typing import Any

from .packet_validation import validate_packet


def dumps_packet(packet: Any, *, indent: int = 2) -> str:
    """Validate and serialize a packet or typed EvidencePacket."""
    payload = packet.to_dict() if hasattr(packet, "to_dict") else packet
    validate_packet(payload)
    return json.dumps(payload, ensure_ascii=False, indent=indent, allow_nan=False) + "\n"


def loads_packet(text: str):
    """Deserialize and validate packet JSON."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid evidence packet JSON: {exc}") from exc
    return validate_packet(payload)
