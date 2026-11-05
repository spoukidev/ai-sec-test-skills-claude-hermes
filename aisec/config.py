"""YAML + Pydantic configuration: targets (models.yaml), suites (suites.yaml), judge (judge.yaml).

Secrets are **never** stored in YAML. Config only names the environment variables to read.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from aisec import paths


def _as_list(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    return list(v)


def _first_env(names: list[str]) -> str | None:
    for n in names:
        val = os.environ.get(n)
        if val:
            return val
    return None


class MockProfile(BaseModel):
    comply_rate: float = Field(0.2, ge=0, le=1)
    vague_rate: float = Field(0.1, ge=0, le=1)
    overrefusal_rate: float = Field(0.05, ge=0, le=1)
    seed: int = 1337


class TargetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    provider: Literal["anthropic", "openai_compat", "mock"]
    description: str = ""
    model: str = ""
    model_env: list[str] = Field(default_factory=list)
    api_key_env: list[str] = Field(default_factory=list)
    base_url: str | None = None
    base_url_env: list[str] = Field(default_factory=list)
    max_tokens: int = 512
    timeout_s: float = 60.0
    requests_per_minute: float = 30.0
    params: dict[str, Any] = Field(default_factory=dict)
    supports_tools: bool = True
    price_input_per_mtok: float = 0.0
    price_output_per_mtok: float = 0.0
    mock_profile: MockProfile = Field(default_factory=MockProfile)

    _norm = field_validator("model_env", "api_key_env", "base_url_env", mode="before")(_as_list)

    def resolve_model(self) -> str:
        return _first_env(self.model_env) or self.model

    def resolve_api_key(self) -> str | None:
        return _first_env(self.api_key_env)

    def resolve_base_url(self) -> str | None:
        return _first_env(self.base_url_env) or self.base_url

    def cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * self.price_input_per_mtok + output_tokens * self.price_output_per_mtok) / 1e6


class SuiteConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = ""
    skills: list[str] | Literal["all"] = "all"
    categories: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)
    include_tool_skills: bool = False
    max_cases_per_skill: int | None = None


class JudgeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    target: TargetConfig | None = None
    apply_to: Literal["inconclusive", "all"] = "inconclusive"
    override_deterministic_fail: bool = False
    prompt: str = ""


class Config(BaseModel):
    targets: dict[str, TargetConfig]
    suites: dict[str, SuiteConfig]
    judge: JudgeConfig


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_config(config_dir: Path | None = None) -> Config:
    cdir = Path(config_dir) if config_dir else paths.config_dir()
    models = _load_yaml(cdir / "models.yaml").get("targets", {})
    targets = {name: TargetConfig(name=name, **spec) for name, spec in models.items()}
    suites = {n: SuiteConfig(**s) for n, s in _load_yaml(cdir / "suites.yaml").get("suites", {}).items()}
    jraw = _load_yaml(cdir / "judge.yaml").get("judge", {})
    if jraw.get("target"):
        jraw["target"] = TargetConfig(name="judge", **jraw["target"])
    return Config(targets=targets, suites=suites, judge=JudgeConfig(**jraw))
