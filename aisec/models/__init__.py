"""Model clients: Anthropic (Claude), OpenAI-compatible (Hermes & co.) and an offline mock."""

from aisec.models.base import ModelClient, ModelClientError, build_client

__all__ = ["ModelClient", "ModelClientError", "build_client"]
