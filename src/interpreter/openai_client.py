"""OpenAI Responses API adapter for the evidence-bound interpreter."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping, NoReturn

from pydantic import BaseModel, ValidationError

from .models import ExposureInterpretation
from .prompts import developer_prompt, packet_input
from .validation import InterpretationValidationError, InterpreterError


DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_REASONING_EFFORT = "low"
DEFAULT_TIMEOUT_SECONDS = 30.0
ALLOWED_REASONING_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh"}


class OpenAIConfigurationError(InterpreterError):
    """Required OpenAI server-side configuration is missing or malformed."""


class OpenAIAuthenticationError(InterpreterError):
    """OpenAI rejected the configured API credentials."""


class OpenAIPermissionError(InterpreterError):
    """The OpenAI project lacks permission for the requested operation."""


class OpenAIModelUnavailableError(InterpreterError):
    """The configured model is unavailable; no fallback was attempted."""


class OpenAITimeoutError(InterpreterError):
    """The OpenAI request exceeded its configured timeout."""


class OpenAIRateLimitError(InterpreterError):
    """OpenAI rejected the request because of a rate or quota limit."""


class OpenAIConnectionError(InterpreterError):
    """The backend could not connect to OpenAI."""


class OpenAIRequestError(InterpreterError):
    """OpenAI rejected or failed the request."""


class OpenAIIncompleteResponseError(InterpreterError):
    """OpenAI did not complete the structured response."""


class OpenAIRefusalError(InterpreterError):
    """The model refused the interpretation request."""


class OpenAIStructuredOutputError(InterpretationValidationError):
    """The response contained no parseable structured output."""


@dataclass(frozen=True)
class OpenAIInterpreterConfig:
    api_key: str
    model: str = DEFAULT_MODEL
    reasoning_effort: str = DEFAULT_REASONING_EFFORT
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> "OpenAIInterpreterConfig":
        values = os.environ if environment is None else environment
        api_key = values.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise OpenAIConfigurationError("OPENAI_API_KEY is required in the backend environment")
        model = values.get("OPENAI_MODEL", DEFAULT_MODEL).strip()
        if not model:
            raise OpenAIConfigurationError("OPENAI_MODEL must be non-empty")
        effort = values.get("OPENAI_REASONING_EFFORT", DEFAULT_REASONING_EFFORT).strip().lower()
        if effort not in ALLOWED_REASONING_EFFORTS:
            raise OpenAIConfigurationError(
                "OPENAI_REASONING_EFFORT must be one of " + ", ".join(sorted(ALLOWED_REASONING_EFFORTS))
            )
        raw_timeout = values.get("OPENAI_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)).strip()
        try:
            timeout = float(raw_timeout)
        except ValueError as exc:
            raise OpenAIConfigurationError("OPENAI_TIMEOUT_SECONDS must be a positive number") from exc
        if timeout <= 0:
            raise OpenAIConfigurationError("OPENAI_TIMEOUT_SECONDS must be a positive number")
        return cls(api_key=api_key, model=model, reasoning_effort=effort, timeout_seconds=timeout)


def _content_type(value: Any) -> str | None:
    return value.get("type") if isinstance(value, dict) else getattr(value, "type", None)


def _contains_refusal(response: Any) -> bool:
    for item in getattr(response, "output", []) or []:
        content_items = item.get("content", []) if isinstance(item, dict) else getattr(item, "content", [])
        for content in content_items or []:
            if _content_type(content) in {"refusal", "output_refusal"}:
                return True
    return False


def _usage_value(usage: Any, name: str) -> int | None:
    value = usage.get(name) if isinstance(usage, dict) else getattr(usage, name, None)
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


class OpenAIInterpreterClient:
    """Small adapter that makes one tool-free, non-stored Responses API call."""

    def __init__(self, config: OpenAIInterpreterConfig, client: Any | None = None):
        self.config = config
        if client is None:
            from openai import OpenAI

            client = OpenAI(
                api_key=config.api_key,
                timeout=config.timeout_seconds,
                max_retries=0,
            )
        self._client = client

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
        *,
        client: Any | None = None,
    ) -> "OpenAIInterpreterClient":
        return cls(OpenAIInterpreterConfig.from_environment(environment), client=client)

    def interpret(self, packet: dict, validation_feedback: str | None = None) -> dict:
        try:
            response = self._client.responses.parse(
                model=self.config.model,
                instructions=developer_prompt(validation_feedback),
                input=packet_input(packet),
                text_format=ExposureInterpretation,
                reasoning={"effort": self.config.reasoning_effort},
                tools=[],
                parallel_tool_calls=False,
                store=False,
                max_output_tokens=4000,
                timeout=self.config.timeout_seconds,
            )
        except Exception as exc:
            self._raise_safe_api_error(exc)

        status = getattr(response, "status", None)
        if status != "completed":
            raise OpenAIIncompleteResponseError("OpenAI returned an incomplete response")
        if _contains_refusal(response):
            raise OpenAIRefusalError("OpenAI refused the interpretation request")
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise OpenAIStructuredOutputError("OpenAI returned no valid structured interpretation")
        if isinstance(parsed, BaseModel):
            payload = parsed.model_dump(mode="json")
        elif isinstance(parsed, dict):
            payload = dict(parsed)
        else:
            raise OpenAIStructuredOutputError("OpenAI returned an unsupported structured output type")

        metadata = payload.get("interpretation_metadata")
        if not isinstance(metadata, dict):
            raise OpenAIStructuredOutputError("OpenAI output is missing interpretation metadata")
        usage = getattr(response, "usage", None)
        metadata.update({
            "model": self.config.model,
            "openai_response_id": getattr(response, "id", None),
            "input_token_count": _usage_value(usage, "input_tokens"),
            "output_token_count": _usage_value(usage, "output_tokens"),
            "total_token_count": _usage_value(usage, "total_tokens"),
        })
        return payload

    def _raise_safe_api_error(self, exc: Exception) -> NoReturn:
        import openai

        if isinstance(exc, ValidationError):
            raise OpenAIStructuredOutputError("OpenAI returned invalid structured output") from None
        if isinstance(exc, openai.LengthFinishReasonError):
            raise OpenAIIncompleteResponseError("OpenAI returned an incomplete response") from None
        if isinstance(exc, openai.ContentFilterFinishReasonError):
            raise OpenAIRefusalError("OpenAI refused the interpretation request") from None
        if isinstance(exc, openai.AuthenticationError):
            raise OpenAIAuthenticationError("OpenAI authentication failed") from None
        if isinstance(exc, openai.PermissionDeniedError):
            raise OpenAIPermissionError("OpenAI permission was denied") from None
        if isinstance(exc, openai.NotFoundError):
            raise OpenAIModelUnavailableError(
                f"configured OpenAI model {self.config.model!r} is unavailable; no fallback was attempted"
            ) from None
        if isinstance(exc, openai.APITimeoutError):
            raise OpenAITimeoutError("OpenAI request timed out") from None
        if isinstance(exc, openai.RateLimitError):
            raise OpenAIRateLimitError("OpenAI rate or quota limit reached") from None
        if isinstance(exc, openai.APIConnectionError):
            raise OpenAIConnectionError("could not connect to OpenAI") from None
        if isinstance(exc, openai.BadRequestError):
            code = getattr(exc, "code", None)
            if code in {"model_not_found", "model_not_available"}:
                raise OpenAIModelUnavailableError(
                    f"configured OpenAI model {self.config.model!r} is unavailable; no fallback was attempted"
                ) from None
            raise OpenAIRequestError("OpenAI rejected the interpretation request") from None
        if isinstance(exc, openai.APIError):
            raise OpenAIRequestError("OpenAI failed the interpretation request") from None
        raise OpenAIRequestError("OpenAI client failed before producing a response") from None
