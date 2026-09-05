"""Small typed value objects used by :mod:`src.client_snapshot`."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SourceReference:
    table: str
    keys: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DataQualityFlag:
    flag_type: str
    severity: str
    message: str
    source_reference: SourceReference

    def to_dict(self) -> dict[str, Any]:
        return {
            "flag_type": self.flag_type,
            "severity": self.severity,
            "message": self.message,
            "source_reference": self.source_reference.to_dict(),
        }
