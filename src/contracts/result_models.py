"""Typed value objects and the canonical field definitions for result v1."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


RESULT_SCHEMA_VERSION = "1.0.0"
SNAPSHOT_SCHEMA_VERSION = "1.0.0"
ALLOWED_SEVERITIES = ("info", "low", "medium", "high")
ALLOWED_STATUSES = ("complete", "partial", "blocked")
EXPOSURE_CHANGE_STATUSES = ("added", "exited", "changed", "unchanged")


@dataclass(frozen=True)
class ResultMetadata:
    result_type: str
    schema_version: str
    calculator_name: str
    calculator_version: str
    client_id: str
    as_of_date: str
    comparison_date: str | None
    period_start: str | None
    period_end: str | None
    input_snapshot_schema_version: str
    input_snapshot_calculation_version: str
    status: str
    input_current_exposure_version: str | None = None
    input_previous_exposure_version: str | None = None


@dataclass(frozen=True)
class Scope:
    level: str
    client_id: str | None
    portfolio_id: str | None
    instrument_id: str | None
    asset_class: str | None
    sector: str | None
    region: str | None
    currency: str | None
    dimension: str | None = None
    key: Any = None
    sub_asset_class: str | None = None


@dataclass(frozen=True)
class Fact:
    fact_id: str
    metric: str
    scope: Scope
    current_value: Any
    unit: str
    as_of_date: str
    previous_value: Any = None
    change: Any = None
    currency: str | None = None
    comparison_date: str | None = None
    current_weight_pct: Any = None
    previous_weight_pct: Any = None
    change_weight_pp: Any = None
    percentage_change: Any = None
    status: str | None = None
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Finding:
    finding_id: str
    finding_type: str
    severity: str
    title: str
    description: str
    fact_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    requires_rm_review: bool


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    source_table: str
    source_keys: dict[str, Any]
    value: Any
    field: str | None = None
    source_date: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class DataQualityWarning:
    warning_id: str
    warning_type: str
    severity: str
    message: str
    evidence_ids: tuple[str, ...] = ()
    source_reference: dict[str, Any] | None = None


@dataclass(frozen=True)
class Assumption:
    assumption_id: str
    description: str
    impact: str
    accepted: bool


@dataclass(frozen=True)
class CalculatorResult:
    result_metadata: ResultMetadata
    facts: tuple[Fact, ...]
    findings: tuple[Finding, ...]
    evidence: tuple[Evidence, ...]
    warnings: tuple[DataQualityWarning, ...]
    assumptions: tuple[Assumption, ...]
    requires_rm_review: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_metadata": asdict(self.result_metadata),
            "facts": [
                {**asdict(item), "scope": asdict(item.scope), "evidence_ids": list(item.evidence_ids)} for item in self.facts
            ],
            "findings": [{**asdict(item), "fact_ids": list(item.fact_ids), "evidence_ids": list(item.evidence_ids)} for item in self.findings],
            "evidence": [asdict(item) for item in self.evidence],
            "warnings": [{**asdict(item), "evidence_ids": list(item.evidence_ids)} for item in self.warnings],
            "assumptions": [asdict(item) for item in self.assumptions],
            "requires_rm_review": self.requires_rm_review,
        }

    # Familiar names make the dataclass convenient for callers accustomed to
    # validation libraries without adding a runtime dependency on one.
    def model_dump(self) -> dict[str, Any]:
        return self.to_dict()


AnalysisResult = CalculatorResult

# Kept as a distinct name for callers that want to make provenance objects.
SourceReference = dict[str, Any]
ResultWarning = DataQualityWarning
Warning = DataQualityWarning
