"""Fake secrets, fake documents and template rendering for cases.

All secrets in ``fixtures/canaries.txt`` are FAKE, randomly shaped placeholders.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from aisec import paths

_TEMPLATE_RE = re.compile(r"\{\{\s*(canary|secret:[A-Za-z0-9_]+|doc:[A-Za-z0-9_.\-]+|documents)\s*\}\}")


@lru_cache(maxsize=8)
def load_secrets(path: str | None = None) -> dict[str, str]:
    """Parse ``NAME=VALUE`` lines (``#`` comments allowed)."""
    p = Path(path) if path else paths.fixtures_dir() / "canaries.txt"
    out: dict[str, str] = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def load_doc(name: str, docs_dir: Path | None = None) -> str:
    d = docs_dir or (paths.fixtures_dir() / "fake_docs")
    path = (d / name).resolve()
    if d.resolve() not in path.parents:
        raise ValueError(f"document path escapes fixtures dir: {name}")
    return path.read_text(encoding="utf-8")


def render(text: str, canary: str, secrets: dict[str, str], documents: str = "") -> str:
    """Replace ``{{canary}}``, ``{{secret:NAME}}``, ``{{doc:FILE}}`` and ``{{documents}}``."""

    def sub(m: re.Match[str]) -> str:
        key = m.group(1)
        if key == "canary":
            return canary
        if key == "documents":
            return documents
        if key.startswith("secret:"):
            name = key.split(":", 1)[1]
            if name not in secrets:
                raise KeyError(f"unknown secret '{name}' (see fixtures/canaries.txt)")
            return secrets[name]
        return load_doc(key.split(":", 1)[1])

    return _TEMPLATE_RE.sub(sub, text)


def used_secrets(*texts: str) -> list[str]:
    """Names of secrets referenced via ``{{secret:NAME}}`` in the given templates."""
    names: list[str] = []
    for t in texts:
        for m in re.finditer(r"\{\{\s*secret:([A-Za-z0-9_]+)\s*\}\}", t or ""):
            if m.group(1) not in names:
                names.append(m.group(1))
    return names


def wrap_documents(docs: list[tuple[str, str]]) -> str:
    """Format retrieved documents the way a naive RAG app would paste them into context."""
    return "\n\n".join(f'<document source="{name}">\n{body.strip()}\n</document>' for name, body in docs)
