"""Claude via the official Anthropic SDK. The API key is read from the environment only."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

from aisec.models.base import ModelClientError
from aisec.schema import Message, ModelResponse, ToolCall, ToolSpec, Usage

if TYPE_CHECKING:
    from aisec.config import TargetConfig


class AnthropicClient:
    provider = "anthropic"

    def __init__(
        self,
        name: str,
        model_id: str,
        api_key: str,
        max_tokens: int = 512,
        base_url: str | None = None,
        params: dict[str, Any] | None = None,
        timeout: float = 60.0,
        sdk_client: Any | None = None,
    ) -> None:
        self.name = name
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.params = dict(params or {})
        if sdk_client is not None:  # dependency injection for tests
            self._client = sdk_client
        else:
            import anthropic

            kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout, "max_retries": 2}
            if base_url:
                kwargs["base_url"] = base_url
            self._client = anthropic.Anthropic(**kwargs)

    @classmethod
    def from_target(cls, target: TargetConfig) -> AnthropicClient:
        key = target.resolve_api_key()
        if not key:
            raise ModelClientError(
                f"Target '{target.name}': set {' or '.join(target.api_key_env)} in your environment "
                "(or run with --mock for an offline demo)."
            )
        return cls(
            target.name,
            target.resolve_model(),
            key,
            target.max_tokens,
            target.resolve_base_url(),
            target.params,
            target.timeout_s,
        )

    @staticmethod
    def to_tools(tools: list[ToolSpec]) -> list[dict[str, Any]]:
        return [{"name": t.name, "description": t.description, "input_schema": t.parameters} for t in tools]

    def complete(
        self,
        system: str | None,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> ModelResponse:
        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "max_tokens": self.max_tokens,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            **self.params,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self.to_tools(tools)
        t0 = time.perf_counter()
        resp = self._client.messages.create(**kwargs)
        latency = (time.perf_counter() - t0) * 1000
        return self.parse_response(resp, latency, self.model_id)

    @staticmethod
    def parse_response(resp: Any, latency_ms: float, fallback_model: str) -> ModelResponse:
        texts: list[str] = []
        calls: list[ToolCall] = []
        for block in getattr(resp, "content", []) or []:
            btype = getattr(block, "type", None)
            if btype == "text":
                texts.append(getattr(block, "text", ""))
            elif btype == "tool_use":
                args = getattr(block, "input", {}) or {}
                calls.append(
                    ToolCall(
                        name=getattr(block, "name", "?"),
                        arguments=dict(args),
                        raw_arguments=json.dumps(args, sort_keys=True),
                    )
                )
        usage = getattr(resp, "usage", None)
        return ModelResponse(
            text="\n".join(texts),
            tool_calls=calls,
            usage=Usage(
                input_tokens=getattr(usage, "input_tokens", 0) or 0,
                output_tokens=getattr(usage, "output_tokens", 0) or 0,
            ),
            latency_ms=latency_ms,
            model_id=getattr(resp, "model", None) or fallback_model,
            stop_reason=getattr(resp, "stop_reason", None),
        )
