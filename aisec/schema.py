"""Core data structures shared by the harness, skills, graders and reports."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ToolSpec(BaseModel):
    """A provider-neutral tool definition (JSON-schema parameters)."""

    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}})


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    raw_arguments: str | None = None


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class ModelResponse(BaseModel):
    text: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    latency_ms: float = 0.0
    model_id: str = ""
    stop_reason: str | None = None
    error: str | None = None


class Case(BaseModel):
    """One graded prompt case.

    Templating: ``{{canary}}`` -> per-run canary, ``{{secret:NAME}}`` -> fake secret
    from fixtures/canaries.txt, ``{{doc:FILE}}`` -> contents of fixtures/fake_docs/FILE.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    description: str = ""
    system: str | None = None
    turns: list[str]
    documents: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    hard_negative: bool = False
    expect: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class SkillMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    category: Literal[
        "prompt_injection_direct",
        "prompt_injection_indirect",
        "jailbreak",
        "obfuscation",
        "adversarial_suffix",
        "system_prompt_leak",
        "data_exfiltration",
        "roleplay_bypass",
        "tool_misuse",
        "multi_turn",
        "over_refusal",
    ]
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    description: str = ""
    models: list[str] = Field(default_factory=lambda: ["*"])
    tags: list[str] = Field(default_factory=list)
    requires_tools: bool = False
    default_system: str | None = None
    references: list[str] = Field(default_factory=list)


class RunRecord(BaseModel):
    """One JSONL line of a run log."""

    run_id: str
    timestamp: str
    target: str
    provider: str
    model_id: str
    skill_id: str
    category: str
    severity: str
    case_id: str
    hard_negative: bool
    verdict: Literal["pass", "fail", "inconclusive"]
    score: float
    grader: str
    evidence: list[str] = Field(default_factory=list)
    response_excerpt: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    judge: dict[str, Any] | None = None
    error: str | None = None
    mock: bool = False
    tags: list[str] = Field(default_factory=list)
