from __future__ import annotations

from types import SimpleNamespace

import httpx
import openai
import pytest

from src.interpreter.models import ExposureInterpretation
from src.interpreter.openai_client import (
    DEFAULT_MODEL,
    OpenAIAuthenticationError,
    OpenAIConfigurationError,
    OpenAIConnectionError,
    OpenAIIncompleteResponseError,
    OpenAIInterpreterClient,
    OpenAIInterpreterConfig,
    OpenAIModelUnavailableError,
    OpenAIRateLimitError,
    OpenAIRefusalError,
    OpenAITimeoutError,
)


class FakeResponses:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


def _sdk(response=None, error=None):
    responses = FakeResponses(response, error)
    return SimpleNamespace(responses=responses), responses


def test_environment_configuration_defaults_and_validation():
    config = OpenAIInterpreterConfig.from_environment({"OPENAI_API_KEY": "server-secret"})
    assert config.model == DEFAULT_MODEL
    assert config.reasoning_effort == "low"
    assert config.timeout_seconds == 30

    with pytest.raises(OpenAIConfigurationError, match="OPENAI_API_KEY"):
        OpenAIInterpreterConfig.from_environment({})
    with pytest.raises(OpenAIConfigurationError, match="REASONING"):
        OpenAIInterpreterConfig.from_environment({"OPENAI_API_KEY": "x", "OPENAI_REASONING_EFFORT": "extreme"})
    with pytest.raises(OpenAIConfigurationError, match="TIMEOUT"):
        OpenAIInterpreterConfig.from_environment({"OPENAI_API_KEY": "x", "OPENAI_TIMEOUT_SECONDS": "0"})


def test_responses_parse_uses_strict_model_no_tools_no_storage_and_records_provenance(
    packet_with_finding, valid_output_factory
):
    parsed = ExposureInterpretation.model_validate(valid_output_factory(packet_with_finding, model=DEFAULT_MODEL))
    response = SimpleNamespace(
        status="completed",
        output_parsed=parsed,
        output=[],
        id="resp_test_123",
        usage=SimpleNamespace(input_tokens=111, output_tokens=22, total_tokens=133),
    )
    sdk, responses = _sdk(response=response)
    config = OpenAIInterpreterConfig("server-secret", DEFAULT_MODEL, "low", 12.0)
    result = OpenAIInterpreterClient(config, client=sdk).interpret(packet_with_finding)

    call = responses.calls[0]
    assert call["model"] == DEFAULT_MODEL
    assert call["text_format"] is ExposureInterpretation
    assert call["reasoning"] == {"effort": "low"}
    assert call["store"] is False
    assert call["tools"] == []
    assert call["parallel_tool_calls"] is False
    assert call["timeout"] == 12.0
    assert "client_id" in call["input"]
    metadata = result["interpretation_metadata"]
    assert metadata["model"] == DEFAULT_MODEL
    assert metadata["openai_response_id"] == "resp_test_123"
    assert metadata["input_token_count"] == 111
    assert metadata["output_token_count"] == 22
    assert metadata["total_token_count"] == 133


def _response_error(error):
    sdk, _ = _sdk(error=error)
    return OpenAIInterpreterClient(OpenAIInterpreterConfig("server-secret"), client=sdk)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (openai.APITimeoutError(httpx.Request("POST", "https://api.openai.test")), OpenAITimeoutError),
        (openai.APIConnectionError(request=httpx.Request("POST", "https://api.openai.test")), OpenAIConnectionError),
        (
            openai.RateLimitError(
                "server-secret", response=httpx.Response(429, request=httpx.Request("POST", "https://api.openai.test")), body=None
            ),
            OpenAIRateLimitError,
        ),
        (
            openai.AuthenticationError(
                "server-secret", response=httpx.Response(401, request=httpx.Request("POST", "https://api.openai.test")), body=None
            ),
            OpenAIAuthenticationError,
        ),
        (
            openai.NotFoundError(
                "server-secret", response=httpx.Response(404, request=httpx.Request("POST", "https://api.openai.test")), body=None
            ),
            OpenAIModelUnavailableError,
        ),
    ],
)
def test_transport_and_authentication_errors_are_typed_and_do_not_leak_secrets(
    packet_with_finding, error, expected
):
    with pytest.raises(expected) as raised:
        _response_error(error).interpret(packet_with_finding)
    assert "server-secret" not in str(raised.value)


def test_incomplete_response_and_refusal_are_typed(packet_with_finding):
    sdk, _ = _sdk(response=SimpleNamespace(status="incomplete", output=[], output_parsed=None))
    with pytest.raises(OpenAIIncompleteResponseError):
        OpenAIInterpreterClient(OpenAIInterpreterConfig("x"), client=sdk).interpret(packet_with_finding)

    refusal = SimpleNamespace(
        status="completed",
        output=[SimpleNamespace(content=[SimpleNamespace(type="refusal")])],
        output_parsed=None,
    )
    sdk, _ = _sdk(response=refusal)
    with pytest.raises(OpenAIRefusalError):
        OpenAIInterpreterClient(OpenAIInterpreterConfig("x"), client=sdk).interpret(packet_with_finding)


def test_no_real_client_is_instantiated_at_module_import(monkeypatch):
    called = False

    def fail(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("should not instantiate")

    monkeypatch.setattr(openai, "OpenAI", fail)
    OpenAIInterpreterConfig.from_environment({"OPENAI_API_KEY": "x"})
    assert called is False

