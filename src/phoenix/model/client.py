from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterator, Literal, Protocol, TypeAlias, runtime_checkable

import httpx

from .profiles import (
    ModelProfile,
    anthropic_messages_endpoint,
    infer_transport,
    load_env_file,
    load_profile,
    openai_chat_endpoint,
    require_api_key,
)


JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
FinishReason: TypeAlias = Literal["stop", "tool_use", "length", "error"]


@dataclass(frozen=True)
class ToolCall:
    id: str | None
    name: str
    arguments: dict[str, JSONValue]


@dataclass
class ChatRequest:
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] = field(default_factory=list)
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False
    extra_headers: dict[str, str] = field(default_factory=dict)


@dataclass
class ChatResponse:
    raw: dict[str, Any]
    text: str
    tool_calls: list[ToolCall]
    finish_reason: FinishReason
    tokens_in: int
    tokens_out: int


class ModelRequestError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        provider: str,
        endpoint: str,
        status_code: int | None = None,
        response_text: str = "",
        response_json: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.endpoint = endpoint
        self.status_code = status_code
        self.response_text = response_text
        self.response_json = response_json

    def as_dict(self) -> dict[str, Any]:
        return {
            "type": type(self).__name__,
            "message": str(self),
            "provider": self.provider,
            "endpoint": self.endpoint,
            "status_code": self.status_code,
            "response_text": self.response_text,
            "response_json": self.response_json,
        }


@runtime_checkable
class LLMClient(Protocol):
    profile: ModelProfile

    def chat(self, req: ChatRequest) -> ChatResponse: ...
    def stream(self, req: ChatRequest) -> Iterator[dict[str, Any]]: ...


class RoutedLLMClient:
    def __init__(self, profile: ModelProfile, *, timeout_s: int = 120, user_agent: str = "PhoenixAgent/0.1") -> None:
        self.profile = profile
        self._timeout_s = timeout_s
        self._user_agent = user_agent

    def chat(self, req: ChatRequest) -> ChatResponse:
        if req.stream:
            raise RuntimeError("ChatRequest.stream=True is not supported by chat(); call stream() instead.")

        transport = infer_transport(self.profile)
        if transport == "anthropic-messages":
            return self._chat_anthropic(req)
        return self._chat_openai(req)

    def stream(self, req: ChatRequest) -> Iterator[dict[str, Any]]:
        raise NotImplementedError("streaming is not implemented for M0 Step 5")

    def _chat_openai(self, req: ChatRequest) -> ChatResponse:
        endpoint = openai_chat_endpoint(self.profile.base_url)
        api_key = require_api_key(self.profile)
        headers = {
            "Content-Type": "application/json",
            "User-Agent": self._user_agent,
            **req.extra_headers,
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload: dict[str, Any] = {
            "model": self.profile.model,
            "messages": req.messages,
            "stream": False,
        }
        if req.tools:
            payload["tools"] = req.tools
        if req.temperature is not None:
            payload["temperature"] = req.temperature
        if req.max_tokens is not None:
            payload["max_tokens"] = req.max_tokens

        data = self._post_json(endpoint, headers=headers, payload=payload)
        choices = data.get("choices") or []
        if not choices:
            raise ModelRequestError(
                "provider returned no choices",
                provider=self.profile.provider,
                endpoint=endpoint,
                response_json=data,
                response_text=json.dumps(data, ensure_ascii=False)[:1000],
            )

        choice = choices[0]
        message = choice.get("message") or {}
        tool_calls = [_parse_openai_tool_call(item) for item in message.get("tool_calls") or []]
        usage = data.get("usage") or {}
        return ChatResponse(
            raw=data,
            text=_coerce_text(message.get("content")),
            tool_calls=tool_calls,
            finish_reason=_map_openai_finish_reason(choice.get("finish_reason")),
            tokens_in=_usage_counter(usage, "prompt_tokens"),
            tokens_out=_usage_counter(usage, "completion_tokens"),
        )

    def _chat_anthropic(self, req: ChatRequest) -> ChatResponse:
        endpoint = anthropic_messages_endpoint(self.profile.base_url)
        api_key = require_api_key(self.profile)
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            "User-Agent": self._user_agent,
            **req.extra_headers,
        }
        if api_key:
            headers["x-api-key"] = api_key

        system_blocks: list[str] = []
        messages: list[dict[str, Any]] = []
        for message in req.messages:
            role = message.get("role")
            if role == "system":
                system_blocks.append(_coerce_text(message.get("content")))
                continue
            messages.append({"role": role, "content": message.get("content", "")})

        payload: dict[str, Any] = {
            "model": self.profile.model,
            "messages": messages,
            "max_tokens": req.max_tokens or 256,
        }
        if system_blocks:
            payload["system"] = "\n\n".join(part for part in system_blocks if part)
        if req.tools:
            payload["tools"] = req.tools
        if req.temperature is not None:
            payload["temperature"] = req.temperature

        data = self._post_json(endpoint, headers=headers, payload=payload)
        content = data.get("content") or []
        usage = data.get("usage") or {}
        return ChatResponse(
            raw=data,
            text=_anthropic_text(content),
            tool_calls=_anthropic_tool_calls(content),
            finish_reason=_map_anthropic_finish_reason(data.get("stop_reason")),
            tokens_in=_usage_counter(usage, "input_tokens"),
            tokens_out=_usage_counter(usage, "output_tokens"),
        )

    def _post_json(self, endpoint: str, *, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=self._timeout_s, follow_redirects=True) as client:
                response = client.post(endpoint, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise ModelRequestError(
                f"request to {endpoint} failed: {exc}",
                provider=self.profile.provider,
                endpoint=endpoint,
            ) from exc

        response_text = response.text[:2000]
        response_json: dict[str, Any] | None = None
        if response.text:
            try:
                parsed = response.json()
                if isinstance(parsed, dict):
                    response_json = parsed
            except ValueError:
                response_json = None

        if response.status_code >= 400:
            raise ModelRequestError(
                f"{self.profile.name} request failed with HTTP {response.status_code}",
                provider=self.profile.provider,
                endpoint=endpoint,
                status_code=response.status_code,
                response_text=response_text,
                response_json=response_json,
            )

        if response_json is None:
            raise ModelRequestError(
                "provider returned non-JSON success payload",
                provider=self.profile.provider,
                endpoint=endpoint,
                status_code=response.status_code,
                response_text=response_text,
            )
        return response_json


def make_client(
    profile: str | ModelProfile,
    *,
    timeout_s: int = 120,
    user_agent: str = "PhoenixAgent/0.1",
) -> RoutedLLMClient:
    load_env_file()
    loaded_profile = load_profile(profile) if isinstance(profile, str) else profile
    return RoutedLLMClient(loaded_profile, timeout_s=timeout_s, user_agent=user_agent)


def _usage_counter(usage: dict[str, Any], field_name: str) -> int:
    value = usage.get(field_name, 0)
    return int(value or 0)


def _coerce_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(part for part in parts if part).strip()
    if content is None:
        return ""
    return str(content)


def _parse_tool_arguments(arguments: Any) -> dict[str, JSONValue]:
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError:
            return {"_raw": arguments}
        if isinstance(parsed, dict):
            return parsed
        return {"value": parsed}
    return {}


def _parse_openai_tool_call(raw: dict[str, Any]) -> ToolCall:
    function = raw.get("function") or {}
    return ToolCall(
        id=raw.get("id"),
        name=str(function.get("name", "")),
        arguments=_parse_tool_arguments(function.get("arguments")),
    )


def _anthropic_text(blocks: list[dict[str, Any]]) -> str:
    parts = [str(block.get("text", "")) for block in blocks if block.get("type") == "text"]
    return "\n".join(part for part in parts if part).strip()


def _anthropic_tool_calls(blocks: list[dict[str, Any]]) -> list[ToolCall]:
    tool_calls: list[ToolCall] = []
    for block in blocks:
        if block.get("type") != "tool_use":
            continue
        raw_input = block.get("input")
        arguments = raw_input if isinstance(raw_input, dict) else {}
        tool_calls.append(
            ToolCall(
                id=block.get("id"),
                name=str(block.get("name", "")),
                arguments=arguments,
            )
        )
    return tool_calls


def _map_openai_finish_reason(reason: Any) -> FinishReason:
    mapping = {
        "stop": "stop",
        "length": "length",
        "tool_calls": "tool_use",
    }
    return mapping.get(str(reason), "error")


def _map_anthropic_finish_reason(reason: Any) -> FinishReason:
    mapping = {
        "end_turn": "stop",
        "stop_sequence": "stop",
        "max_tokens": "length",
        "tool_use": "tool_use",
    }
    return mapping.get(str(reason), "error")


__all__ = [
    "ChatRequest",
    "ChatResponse",
    "FinishReason",
    "JSONValue",
    "LLMClient",
    "ModelRequestError",
    "RoutedLLMClient",
    "ToolCall",
    "make_client",
]
