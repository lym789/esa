from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

from app.core.config import Settings, get_settings


PLACEHOLDER_API_KEYS = {"", "replace-with-your-key"}


class LLMClientError(RuntimeError):
    """Raised when a model call cannot be completed or parsed."""


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True)
class LLMTextResponse:
    content: str
    model: str
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class LLMJSONResponse:
    data: dict[str, Any]
    model: str
    raw: dict[str, Any] | None = None


class LLMClient(Protocol):
    def generate_text(
        self,
        messages: Sequence[LLMMessage | Mapping[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LLMTextResponse:
        ...

    def generate_json(
        self,
        messages: Sequence[LLMMessage | Mapping[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMJSONResponse:
        ...


def _has_real_api_key(settings: Settings) -> bool:
    return settings.openai_api_key.strip() not in PLACEHOLDER_API_KEYS


def is_llm_configured(settings: Settings | None = None) -> bool:
    active_settings = settings or get_settings()
    return (
        active_settings.llm_enabled
        and active_settings.llm_provider == "openai"
        and _has_real_api_key(active_settings)
    )


def normalize_messages(messages: Sequence[LLMMessage | Mapping[str, str]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for message in messages:
        if isinstance(message, LLMMessage):
            role = message.role
            content = message.content
        else:
            role = str(message["role"])
            content = str(message["content"])
        normalized.append({"role": role, "content": content})
    return normalized


def _response_to_raw(response: Any) -> dict[str, Any] | None:
    if hasattr(response, "model_dump"):
        return response.model_dump()
    if isinstance(response, dict):
        return response
    return None


class DisabledLLMClient:
    def generate_text(
        self,
        messages: Sequence[LLMMessage | Mapping[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LLMTextResponse:
        raise LLMClientError("LLM is disabled or not configured")

    def generate_json(
        self,
        messages: Sequence[LLMMessage | Mapping[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMJSONResponse:
        raise LLMClientError("LLM is disabled or not configured")


class OpenAILLMClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not is_llm_configured(self.settings):
            raise LLMClientError("OpenAI LLM client requires LLM_ENABLED=true and a real OPENAI_API_KEY")

        from openai import OpenAI

        self._client = OpenAI(
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url or None,
            timeout=self.settings.llm_timeout_seconds,
            max_retries=self.settings.llm_max_retries,
        )

    def _create_completion(
        self,
        messages: Sequence[LLMMessage | Mapping[str, str]],
        *,
        temperature: float,
        max_tokens: int | None,
        response_format: dict[str, str] | None = None,
    ) -> Any:
        kwargs: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": normalize_messages(messages),
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if response_format is not None:
            kwargs["response_format"] = response_format

        try:
            return self._client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            raise LLMClientError(f"LLM call failed: {exc}") from exc

    def generate_text(
        self,
        messages: Sequence[LLMMessage | Mapping[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LLMTextResponse:
        response = self._create_completion(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        if not content:
            raise LLMClientError("LLM response did not contain text content")
        return LLMTextResponse(content=content, model=self.settings.llm_model, raw=_response_to_raw(response))

    def generate_json(
        self,
        messages: Sequence[LLMMessage | Mapping[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMJSONResponse:
        response = self._create_completion(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if not content:
            raise LLMClientError("LLM response did not contain JSON content")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMClientError(f"LLM response was not valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise LLMClientError("LLM JSON response must be an object")
        return LLMJSONResponse(data=data, model=self.settings.llm_model, raw=_response_to_raw(response))


class FakeLLMClient:
    def __init__(
        self,
        *,
        text_response: str = "",
        json_response: dict[str, Any] | None = None,
        model: str = "fake-llm",
        error: LLMClientError | None = None,
    ) -> None:
        self.text_response = text_response
        self.json_response = json_response or {}
        self.model = model
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def generate_text(
        self,
        messages: Sequence[LLMMessage | Mapping[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LLMTextResponse:
        normalized = normalize_messages(messages)
        self.calls.append(
            {
                "mode": "text",
                "messages": normalized,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        if self.error is not None:
            raise self.error
        return LLMTextResponse(content=self.text_response, model=self.model, raw={"fake": True})

    def generate_json(
        self,
        messages: Sequence[LLMMessage | Mapping[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMJSONResponse:
        normalized = normalize_messages(messages)
        self.calls.append(
            {
                "mode": "json",
                "messages": normalized,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        if self.error is not None:
            raise self.error
        return LLMJSONResponse(data=self.json_response, model=self.model, raw={"fake": True})


def build_llm_client(settings: Settings | None = None) -> LLMClient:
    active_settings = settings or get_settings()
    if is_llm_configured(active_settings):
        return OpenAILLMClient(active_settings)
    return DisabledLLMClient()
