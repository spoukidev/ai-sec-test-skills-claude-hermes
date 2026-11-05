"""Hermes (or any model) via an OpenAI-compatible Chat Completions endpoint.

Works with OpenRouter, Together, Fireworks, vLLM and Ollama (``/v1``). Key and base URL come
from environment variables named in ``config/models.yaml``.
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

from aisec.models.base import ModelClientError
from aisec.schema import Message, ModelResponse, ToolCall, ToolSpec, Usage

if TYPE_CHECKING:
    from aisec.config import TargetConfig


class OpenAICompatClient:
    provider = "openai_compat"

    def __init__(
        self,
        name: str,
        model_id: str,
        api_key: str,
        base_url: str | None = None,
        max_tokens: int = 512,
        params: dict[str, Any] | None = None,
        timeout: float = 60.0,
        sdk_client: Any | None = None,
    ) -> None:
        self.name = name
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.params = dict(params or {})
        if sdk_client is not None:
            self._client = sdk_client
        else:
            import openai

            self._client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=2)

    @classmethod
    def from_target(cls, target: TargetConfig) -> OpenAICompatClient:
        key = target.resolve_api_key()
        if not key:
            raise ModelClientError(
                f"Target '{target.name}': set {' or '.join(target.api_key_env)} in your environment "
                "(for a local Ollama server any non-empty value works, e.g. OPENAI_API_KEY=ollama), "
                "or run with --mock for an offline demo."
            )
        return cls(
            target.name,
            target.resolve_model(),
            key,
            target.resolve_base_url(),
            target.max_tokens,
            target.params,
            target.timeout_s,
        )

    @staticmethod
    def to_tools(tools: list[ToolSpec]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {"name": t.name, "description": t.description, "parameters": t.parameters},
            }
            for t in tools
        ]

    def complete(
        self,
        system: str | None,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> ModelResponse:
        msgs: list[dict[str, Any]] = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend({"role": m.role, "content": m.content} for m in messages)
        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "messages": msgs,
            "max_tokens": self.max_tokens,
            **self.params,
        }
        if tools:
            kwargs["tools"] = self.to_tools(tools)
        t0 = time.perf_counter()
        resp = self._client.chat.completions.create(**kwargs)
        latency = (time.perf_counter() - t0) * 1000
        return self.parse_response(resp, latency, self.model_id)

    @staticmethod
    def parse_response(resp: Any, latency_ms: float, fallback_model: str) -> ModelResponse:
        choice = (getattr(resp, "choices", None) or [None])[0]
        msg = getattr(choice, "message", None)
        text = getattr(msg, "content", None) or ""
        calls: list[ToolCall] = []
        for tc in getattr(msg, "tool_calls", None) or []:
            fn = getattr(tc, "function", None)
            raw = getattr(fn, "arguments", "") or ""
            try:
                args = json.loads(raw) if raw else {}
                if not isinstance(args, dict):
                    args = {"_value": args}
            except json.JSONDecodeError:
                args = {"_unparsed": raw}
            calls.append(ToolCall(name=getattr(fn, "name", "?"), arguments=args, raw_arguments=raw))
        usage = getattr(resp, "usage", None)
        return ModelResponse(
            text=text,
            tool_calls=calls,
            usage=Usage(
                input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            ),
            latency_ms=latency_ms,
            model_id=getattr(resp, "model", None) or fallback_model,
            stop_reason=getattr(choice, "finish_reason", None),
        )
