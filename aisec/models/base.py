"""Provider-neutral model client protocol and factory."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from aisec.schema import Message, ModelResponse, ToolSpec

if TYPE_CHECKING:
    from aisec.config import TargetConfig


class ModelClientError(RuntimeError):
    """Raised for configuration problems (e.g. missing API key env var)."""


@runtime_checkable
class ModelClient(Protocol):
    """Anything that can turn (system, messages, tools) into a :class:`ModelResponse`."""

    name: str
    provider: str
    model_id: str

    def complete(
        self,
        system: str | None,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> ModelResponse:
        """``meta`` carries case metadata. Real clients ignore it; the mock uses it."""
        ...


def build_client(target: TargetConfig, mock: bool = False) -> ModelClient:
    """Instantiate the client for a target. ``mock=True`` never touches the network."""
    if mock or target.provider == "mock":
        from aisec.models.mock import MockClient

        return MockClient.from_target(target)
    if target.provider == "anthropic":
        from aisec.models.anthropic_client import AnthropicClient

        return AnthropicClient.from_target(target)
    if target.provider == "openai_compat":
        from aisec.models.openai_compat import OpenAICompatClient

        return OpenAICompatClient.from_target(target)
    raise ModelClientError(f"Unknown provider '{target.provider}' for target '{target.name}'")
