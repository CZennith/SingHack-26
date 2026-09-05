"""Strict, versioned output contract for exposure packet interpretation."""

from __future__ import annotations

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


INTERPRETATION_SCHEMA_VERSION = "1.0.0"
PROMPT_NAME = "exposure_interpreter"
PROMPT_VERSION = "1.0.0"

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class InterpretationMetadata(StrictModel):
    result_type: Literal["exposure_interpretation"]
    schema_version: Literal["1.0.0"]
    prompt_name: Literal["exposure_interpreter"]
    prompt_version: Literal["1.0.0"]
    packet_type: Literal["exposure_change_review"]
    packet_schema_version: Literal["1.0.0"]
    client_id: str = Field(min_length=1)
    as_of_date: str
    comparison_date: str
    model: str = Field(min_length=1)
    status: Literal["complete"]
    openai_response_id: str | None = Field(default=None, description="Populated by the provider adapter; return null.")
    input_token_count: int | None = Field(default=None, ge=0, description="Populated by the provider adapter; return null.")
    output_token_count: int | None = Field(default=None, ge=0, description="Populated by the provider adapter; return null.")
    total_token_count: int | None = Field(default=None, ge=0, description="Populated by the provider adapter; return null.")

    @field_validator("as_of_date", "comparison_date")
    @classmethod
    def validate_iso_date(cls, value: str) -> str:
        if not _ISO_DATE.fullmatch(value):
            raise ValueError("must be an ISO date in YYYY-MM-DD format")
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("must be a real calendar date") from exc
        if parsed.isoformat() != value:
            raise ValueError("must be an ISO date in YYYY-MM-DD format")
        return value

    @field_validator("client_id", "model")
    @classmethod
    def require_non_blank_metadata(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be non-empty")
        return value


class Observation(StrictModel):
    observation_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=240)
    explanation: str = Field(min_length=1, max_length=2000)
    fact_ids: list[str] = Field(min_length=1, max_length=50)
    evidence_ids: list[str] = Field(min_length=1, max_length=100)
    confidence: Literal["low", "medium", "high"]
    uncertainty: str | None = Field(max_length=1000)

    @field_validator("observation_id", "title", "explanation")
    @classmethod
    def require_non_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be non-empty")
        return value

    @model_validator(mode="after")
    def require_unique_references_and_uncertainty(self) -> "Observation":
        if any(not item.strip() for item in self.fact_ids + self.evidence_ids):
            raise ValueError("fact_ids and evidence_ids must be non-empty strings")
        if len(self.fact_ids) != len(set(self.fact_ids)):
            raise ValueError("fact_ids must be unique within an observation")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("evidence_ids must be unique within an observation")
        if self.confidence != "high" and (self.uncertainty is None or not self.uncertainty.strip()):
            raise ValueError("low- and medium-confidence observations must state uncertainty")
        return self


class RMQuestion(StrictModel):
    question_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=1000)
    observation_ids: list[str] = Field(max_length=50)

    @field_validator("question_id", "question")
    @classmethod
    def require_non_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be non-empty")
        return value

    @model_validator(mode="after")
    def require_unique_observation_references(self) -> "RMQuestion":
        if any(not item.strip() for item in self.observation_ids):
            raise ValueError("observation_ids must be non-empty strings")
        if len(self.observation_ids) != len(set(self.observation_ids)):
            raise ValueError("observation_ids must be unique within a question")
        return self


class ExposureInterpretation(StrictModel):
    interpretation_metadata: InterpretationMetadata
    executive_summary: str = Field(min_length=1, max_length=3000)
    observations: list[Observation] = Field(max_length=20)
    questions_for_rm: list[RMQuestion] = Field(max_length=20)
    limitations: list[str] = Field(max_length=100)
    warnings: list[str] = Field(max_length=100)
    requires_rm_review: Literal[True]

    @model_validator(mode="after")
    def require_unique_ids(self) -> "ExposureInterpretation":
        if not self.executive_summary.strip():
            raise ValueError("executive_summary must be non-empty")
        if any(not item.strip() for item in self.limitations + self.warnings):
            raise ValueError("limitations and warnings must contain non-empty strings")
        observation_ids = [item.observation_id for item in self.observations]
        if len(observation_ids) != len(set(observation_ids)):
            raise ValueError("observation IDs must be unique")
        question_ids = [item.question_id for item in self.questions_for_rm]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("question IDs must be unique")
        return self
