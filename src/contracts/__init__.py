"""Versioned contracts for future client-analysis calculator results."""

from .result_models import (
    EXPOSURE_CHANGE_STATUSES,
    AnalysisResult,
    Assumption,
    CalculatorResult,
    DataQualityWarning,
    Evidence,
    Fact,
    Finding,
    ResultMetadata,
    ResultWarning,
    Scope,
    SourceReference,
)
from .serialization import dumps_result, generate_json_schema, loads_result, write_json_schema
from .validation import (
    ResultContractError,
    UnsupportedResultSchemaVersion,
    result_metadata_from_snapshot,
    validate_result,
)

__all__ = [
    "AnalysisResult", "Assumption", "CalculatorResult", "DataQualityWarning", "EXPOSURE_CHANGE_STATUSES",
    "Evidence", "Fact", "Finding", "ResultMetadata", "ResultWarning", "Scope", "SourceReference",
    "ResultContractError", "UnsupportedResultSchemaVersion", "validate_result",
    "result_metadata_from_snapshot", "dumps_result", "loads_result",
    "generate_json_schema", "write_json_schema",
]
