"""Loader for the shared, educational payload corpus in ``payloads/*.jsonl``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from aisec import paths


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    family: str
    technique: str
    text: str
    hard_negative: bool = False
    tags: list[str] = Field(default_factory=list)
    expect: dict[str, Any] = Field(default_factory=dict)
    source: str = "original"
    note: str = ""


class PayloadError(ValueError):
    pass


def load_payloads(name: str, directory: Path | None = None) -> list[Payload]:
    """Load ``payloads/<name>.jsonl``. Blank lines and ``//`` comment lines are ignored.

    Raises :class:`PayloadError` with the line number on malformed JSON, schema errors or
    duplicate ids.
    """
    d = directory or paths.payloads_dir()
    path = d / (name if name.endswith(".jsonl") else f"{name}.jsonl")
    out: list[Payload] = []
    seen: set[str] = set()
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        s = line.strip()
        if not s or s.startswith("//"):
            continue
        try:
            p = Payload(**json.loads(s))
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise PayloadError(f"{path.name}:{lineno}: {exc}") from exc
        if p.id in seen:
            raise PayloadError(f"{path.name}:{lineno}: duplicate id '{p.id}'")
        seen.add(p.id)
        out.append(p)
    return out


def select(
    payloads: list[Payload], family: str | None = None, technique: str | None = None, tag: str | None = None
) -> list[Payload]:
    return [
        p
        for p in payloads
        if (family is None or p.family == family)
        and (technique is None or p.technique == technique)
        and (tag is None or tag in p.tags)
    ]
