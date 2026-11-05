"""Locate project directories (config/, skills/, payloads/, fixtures/).

Resolution order for the project root: ``AISEC_HOME`` env var → current working directory
(if it contains ``skills/``) → the source checkout that contains this package.
"""

from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    env = os.environ.get("AISEC_HOME")
    if env:
        return Path(env).resolve()
    cwd = Path.cwd()
    if (cwd / "skills").is_dir() and (cwd / "config").is_dir():
        return cwd
    return Path(__file__).resolve().parents[1]


def config_dir() -> Path:
    return project_root() / "config"


def skills_dir() -> Path:
    return project_root() / "skills"


def payloads_dir() -> Path:
    return project_root() / "payloads"


def fixtures_dir() -> Path:
    return project_root() / "fixtures"


def results_dir() -> Path:
    return project_root() / "results"
