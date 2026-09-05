"""Typed value objects for evidence packet v1.

The packet deliberately has its own envelope and version fields.  Calculator
result versions and snapshot versions remain input provenance and are never
reinterpreted as packet versions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


PACKET_SCHEMA_VERSION = "1.0.0"
PACKET_VERSION = "1.0.0"
PACKET_TYPE = "exposure_change_review"
SNAPSHOT_SCHEMA_VERSION = "1.0.0"
ALLOWED_PACKET_TYPES = (PACKET_TYPE,)
ALLOWED_PACKET_STATUSES = ("complete", "partial", "blocked")


@dataclass(frozen=True)
class PacketMetadata:
    packet_type: str
    schema_version: str
    packet_version: str
    client_id: str
    as_of_date: str
    comparison_date: str
    period_start: str
    period_end: str
    input_snapshot_schema_version: str
    input_snapshot_calculation_version: str
    included_calculators: tuple[dict[str, str], ...]
    status: str


@dataclass(frozen=True)
class PacketGovernance:
    requires_rm_review: bool
    recommendations_allowed: bool
    llm_interpretation_allowed: bool
    source_data_is_authoritative: bool


@dataclass(frozen=True)
class EvidencePacket:
    packet_metadata: PacketMetadata
    client_context: dict[str, Any]
    facts: tuple[dict[str, Any], ...]
    findings: tuple[dict[str, Any], ...]
    evidence: tuple[dict[str, Any], ...]
    warnings: tuple[dict[str, Any], ...]
    assumptions: tuple[dict[str, Any], ...]
    governance: PacketGovernance

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["packet_metadata"]["included_calculators"] = [
            dict(item) for item in self.packet_metadata.included_calculators
        ]
        for field in ("facts", "findings", "evidence", "warnings", "assumptions"):
            payload[field] = [dict(item) for item in getattr(self, field)]
        return payload

    def model_dump(self) -> dict[str, Any]:
        return self.to_dict()

    def __getitem__(self, key: str) -> Any:
        """Permit mapping-style access alongside the typed API."""
        return self.to_dict()[key]
