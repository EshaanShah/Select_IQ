"""Generative-model adapters that interpret a creative brief against gallery evidence."""

import base64
import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

import httpx

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_IMAGES_PER_REQUEST = 3
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

INTERPRETATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "positive_descriptors", "negative_descriptors", "photo_notes"],
    "properties": {
        "summary": {"type": "string"},
        "positive_descriptors": {"type": "array", "items": {"type": "string"}},
        "negative_descriptors": {"type": "array", "items": {"type": "string"}},
        "photo_notes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["label", "effect", "reason"],
                "properties": {
                    "label": {"type": "string"},
                    "effect": {"type": "string", "enum": ["boost", "penalize"]},
                    "reason": {"type": "string"},
                },
            },
        },
    },
}

SYSTEM_PROMPT = """You are a professional photo editor helping cull a client gallery.
You receive the photographer's creative brief, the number of photographs they want, contact
sheets where every photograph is captioned with a label such as P01, and each photograph's
CLIP similarity to the brief (higher means closer, but CLIP is literal and often misses intent).

Return JSON only, matching the schema:
- summary: one or two sentences on what the brief really asks for.
- positive_descriptors: 1-6 short visual phrases (at most 12 words each) describing what
  the chosen photographs should show, written like image captions, e.g. "a person smiling".
- negative_descriptors: 0-4 short visual phrases describing what to avoid.
- photo_notes: photographs that clearly match or clearly violate the brief. Use only labels
  that appear on the contact sheets. effect is "boost" or "penalize"; reason is one sentence
  grounded in what is visible in that photograph."""


@dataclass(frozen=True, slots=True)
class ReasonerRequest:
    brief: str
    target: int
    photos: tuple[tuple[str, float | None], ...]  # (label, CLIP brief relevance)
    contact_sheets: tuple[bytes, ...]


@dataclass(frozen=True, slots=True)
class ReasonerResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class ReasonerError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class BriefReasoner(Protocol):
    provider: str
    model_name: str

    def interpret(self, request: ReasonerRequest) -> ReasonerResponse: ...


def build_user_content(request: ReasonerRequest) -> list[dict]:
    evidence = "\n".join(
        f"{label}: CLIP brief similarity "
        + ("unavailable" if relevance is None else f"{relevance:.3f}")
        for label, relevance in request.photos
    )
    text = (
        f"Creative brief:\n{request.brief}\n\n"
        f"Target: {request.target} of {len(request.photos)} photographs.\n\n"
        f"Image evidence:\n{evidence}"
    )
    content: list[dict] = [{"type": "text", "text": text}]
    for sheet in request.contact_sheets:
        encoded = base64.b64encode(sheet).decode("ascii")
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
        )
    return content


class GroqBriefReasoner:
    provider = "groq"

    def __init__(
        self,
        api_key: str | None,
        model: str,
        timeout_seconds: float = 30,
        max_retries: int = 2,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key
        self.model_name = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.transport = transport
        self.sleep = sleep

    def interpret(self, request: ReasonerRequest) -> ReasonerResponse:
        if not self.api_key:
            raise ReasonerError(
                "missing_api_key", "GROQ_API_KEY is not set, so the brief was not interpreted."
            )
        if len(request.contact_sheets) > MAX_IMAGES_PER_REQUEST:
            raise ReasonerError(
                "too_many_images",
                f"Groq accepts at most {MAX_IMAGES_PER_REQUEST} images per request.",
            )
        body = {
            "model": self.model_name,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_content(request)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "brief_interpretation",
                    "strict": True,
                    "schema": INTERPRETATION_SCHEMA,
                },
            },
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as client:
            response = self._post_with_retries(client, body, headers)
        try:
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise ReasonerError("empty_response", "Groq returned no completion.") from error
        if not isinstance(content, str) or not content.strip():
            raise ReasonerError("empty_response", "Groq returned an empty completion.")
        usage = payload.get("usage") or {}
        return ReasonerResponse(
            content=content,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )

    def _post_with_retries(self, client: httpx.Client, body: dict, headers: dict) -> httpx.Response:
        for attempt in range(self.max_retries + 1):
            last_attempt = attempt == self.max_retries
            try:
                response = client.post(GROQ_URL, json=body, headers=headers)
            except httpx.TimeoutException as error:
                if last_attempt:
                    raise ReasonerError(
                        "timeout", f"Groq did not answer within {self.timeout_seconds:g} seconds."
                    ) from error
            except httpx.HTTPError as error:
                if last_attempt:
                    raise ReasonerError("network_error", f"Could not reach Groq: {error}") from error
            else:
                if response.is_success:
                    return response
                if response.status_code not in RETRYABLE_STATUS:
                    raise ReasonerError("provider_error", _error_message(response))
                if last_attempt:
                    code = "rate_limited" if response.status_code == 429 else "provider_unavailable"
                    raise ReasonerError(code, _error_message(response))
                self.sleep(_retry_delay(response, attempt))
                continue
            self.sleep(2**attempt)
        raise AssertionError("unreachable")


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    try:
        return min(float(response.headers.get("retry-after", "")), 10.0)
    except ValueError:
        return float(2**attempt)


def _error_message(response: httpx.Response) -> str:
    try:
        detail = response.json().get("error", {}).get("message")
    except (ValueError, AttributeError):
        detail = None
    return f"Groq returned HTTP {response.status_code}" + (f": {detail}" if detail else ".")


class ScriptedBriefReasoner:
    """Deterministic adapter for tests and offline development.

    Each call consumes the next scripted item: a string is returned as the model's raw
    completion and an exception is raised. With no script it echoes a valid interpretation
    built from the brief text, so the offline workflow still exercises validation.
    """

    provider = "scripted"
    model_name = "scripted-test"

    def __init__(self, script: Sequence[str | Exception] | None = None) -> None:
        self.script = list(script) if script is not None else None
        self.requests: list[ReasonerRequest] = []

    def interpret(self, request: ReasonerRequest) -> ReasonerResponse:
        self.requests.append(request)
        if self.script is None:
            descriptor = " ".join(request.brief.split()[:10])
            return ReasonerResponse(
                json.dumps(
                    {
                        "summary": f"Offline echo of the brief: {request.brief[:200]}",
                        "positive_descriptors": [descriptor],
                        "negative_descriptors": [],
                        "photo_notes": [],
                    }
                )
            )
        if not self.script:
            raise ReasonerError("script_exhausted", "No scripted response remains.")
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return ReasonerResponse(item)
