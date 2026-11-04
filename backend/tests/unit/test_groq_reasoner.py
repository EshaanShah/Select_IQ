import json

import httpx
import pytest

from selectiq.infrastructure.reasoners import (
    GroqBriefReasoner,
    ReasonerError,
    ReasonerRequest,
)

REQUEST = ReasonerRequest(
    brief="Best lit, nicest smiles.",
    target=2,
    photos=(("P01", 0.21), ("P02", 0.18)),
    contact_sheets=(b"\xff\xd8sheet-one", b"\xff\xd8sheet-two"),
)


def completion(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 1200, "completion_tokens": 90},
        },
    )


def reasoner(handler, **kwargs) -> GroqBriefReasoner:
    return GroqBriefReasoner(
        api_key=kwargs.pop("api_key", "test-key"),
        model="qwen/qwen3.8-27b",
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
        **kwargs,
    )


def test_sends_brief_evidence_images_and_strict_schema() -> None:
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        assert request.headers["authorization"] == "Bearer test-key"
        return completion('{"ok": true}')

    response = reasoner(handler).interpret(REQUEST)

    assert response.content == '{"ok": true}'
    assert (response.input_tokens, response.output_tokens) == (1200, 90)
    body = seen[0]
    assert body["model"] == "qwen/qwen3.8-27b"
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["strict"] is True
    user_content = body["messages"][-1]["content"]
    images = [part for part in user_content if part["type"] == "image_url"]
    texts = " ".join(part["text"] for part in user_content if part["type"] == "text")
    assert len(images) == 2
    assert images[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert "Best lit, nicest smiles." in texts and "P01" in texts and "0.210" in texts


def test_more_than_three_images_is_rejected_before_calling() -> None:
    calls = []
    request = ReasonerRequest("brief", 1, (("P01", 0.1),), (b"a", b"b", b"c", b"d"))
    with pytest.raises(ReasonerError) as error:
        reasoner(lambda r: calls.append(r) or completion("{}")).interpret(request)
    assert error.value.code == "too_many_images"
    assert calls == []


def test_missing_api_key_fails_without_a_network_call() -> None:
    calls = []
    with pytest.raises(ReasonerError) as error:
        reasoner(lambda r: calls.append(r) or completion("{}"), api_key=None).interpret(REQUEST)
    assert error.value.code == "missing_api_key"
    assert calls == []


def test_busy_service_is_retried_then_succeeds() -> None:
    statuses = iter([429, 503])

    def handler(request: httpx.Request) -> httpx.Response:
        status = next(statuses, 200)
        return completion("{}") if status == 200 else httpx.Response(status, json={})

    assert reasoner(handler).interpret(REQUEST).content == "{}"


def test_persistent_rate_limit_becomes_a_typed_failure() -> None:
    with pytest.raises(ReasonerError) as error:
        reasoner(lambda r: httpx.Response(429, json={})).interpret(REQUEST)
    assert error.value.code == "rate_limited"


def test_timeout_becomes_a_typed_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(ReasonerError) as error:
        reasoner(handler).interpret(REQUEST)
    assert error.value.code == "timeout"


def test_authentication_errors_are_not_retried() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(401, json={"error": {"message": "Invalid API Key"}})

    with pytest.raises(ReasonerError) as error:
        reasoner(handler).interpret(REQUEST)
    assert error.value.code == "provider_error"
    assert "Invalid API Key" in str(error.value)
    assert len(calls) == 1


def test_empty_completion_is_a_typed_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": None}}]})

    with pytest.raises(ReasonerError) as error:
        reasoner(handler).interpret(REQUEST)
    assert error.value.code == "empty_response"
