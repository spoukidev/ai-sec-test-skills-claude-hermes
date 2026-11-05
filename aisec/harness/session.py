"""Multi-turn conversation support.

A :class:`Session` keeps the running message history, sends one user turn at a time and
records every assistant response. Tool calls are *recorded, never executed*; when the model
calls a tool, the assistant turn is stored as a textual summary so the next user turn can
still be sent to providers that require strictly alternating roles.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from aisec.models.base import ModelClient
from aisec.schema import Message, ModelResponse, ToolSpec


class Session:
    def __init__(
        self,
        client: ModelClient,
        system: str | None,
        tools: list[ToolSpec] | None = None,
        meta: dict[str, Any] | None = None,
        call_wrapper: Callable[[Callable[[], ModelResponse]], ModelResponse] | None = None,
    ) -> None:
        self.client = client
        self.system = system
        self.tools = tools or None
        self.meta = dict(meta or {})
        self.history: list[Message] = []
        self.responses: list[ModelResponse] = []
        self._wrap = call_wrapper or (lambda fn: fn())

    def send(self, user_text: str) -> ModelResponse:
        self.history.append(Message(role="user", content=user_text))
        meta = {**self.meta, "turn_index": len(self.responses)}
        history = list(self.history)
        resp = self._wrap(lambda: self.client.complete(self.system, history, self.tools, meta))
        self.responses.append(resp)
        assistant_text = resp.text
        if resp.tool_calls:
            summary = "; ".join(
                f"{c.name}({json.dumps(c.arguments, sort_keys=True)})" for c in resp.tool_calls
            )
            assistant_text = (assistant_text + f"\n[requested tool calls: {summary}]").strip()
        self.history.append(Message(role="assistant", content=assistant_text or "(no text)"))
        return resp

    def run(self, turns: list[str]) -> list[ModelResponse]:
        for t in turns:
            self.send(t)
        return self.responses
