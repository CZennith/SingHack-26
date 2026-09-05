"""Validated, deterministic evidence-packet assembly.

The builder exports are lazy so running ``python -m src.pipeline.evidence_packet``
does not import the module once during package initialization and again as the
requested module.
"""

from .packet_serialization import dumps_packet, loads_packet
from .packet_validation import PacketValidationError, validate_packet

__all__ = [
    "PacketValidationError",
    "build_evidence_packet",
    "build_evidence_packets_for_all_clients",
    "dumps_packet",
    "loads_packet",
    "validate_packet",
]


def __getattr__(name: str):
    if name in {"build_evidence_packet", "build_evidence_packets_for_all_clients"}:
        from .evidence_packet import build_evidence_packet, build_evidence_packets_for_all_clients

        return {
            "build_evidence_packet": build_evidence_packet,
            "build_evidence_packets_for_all_clients": build_evidence_packets_for_all_clients,
        }[name]
    raise AttributeError(name)
