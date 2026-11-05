"""Skill discovery and loading.

A skill is a folder under ``skills/`` containing:

* ``skill.yaml`` – metadata validated by :class:`aisec.schema.SkillMeta`
* ``prompts.py`` – defines ``get_cases() -> list[Case]`` (or a ``CASES`` list)
* ``grade.py``   – defines ``grade(response: ModelResponse, ctx: GradeContext) -> Grade``

Folders starting with ``_`` (e.g. ``_template``) are ignored.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import yaml

from aisec import paths
from aisec.grading.base import Grade, GradeContext
from aisec.schema import Case, ModelResponse, SkillMeta

GradeFn = Callable[[ModelResponse, GradeContext], Grade]


class SkillError(ValueError):
    pass


@dataclass
class Skill:
    meta: SkillMeta
    path: Path
    cases: list[Case]
    grade: GradeFn

    @property
    def id(self) -> str:
        return self.meta.id


def _import(path: Path, modname: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(modname, path)
    if spec is None or spec.loader is None:
        raise SkillError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[modname] = module
    spec.loader.exec_module(module)
    return module


def load_skill(path: Path) -> Skill:
    path = Path(path)
    meta_file = path / "skill.yaml"
    if not meta_file.exists():
        raise SkillError(f"{path}: missing skill.yaml")
    meta = SkillMeta(**(yaml.safe_load(meta_file.read_text(encoding="utf-8")) or {}))
    if meta.id != path.name:
        raise SkillError(f"{path}: skill.yaml id '{meta.id}' must equal folder name '{path.name}'")
    prompts = _import(path / "prompts.py", f"aisec_skills.{meta.id}.prompts")
    grader = _import(path / "grade.py", f"aisec_skills.{meta.id}.grade")
    if hasattr(prompts, "get_cases"):
        raw = prompts.get_cases()
    elif hasattr(prompts, "CASES"):
        raw = prompts.CASES
    else:
        raise SkillError(f"{path}/prompts.py must define get_cases() or CASES")
    cases = [c if isinstance(c, Case) else Case(**c) for c in raw]
    ids = [c.id for c in cases]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise SkillError(f"{meta.id}: duplicate case ids {sorted(dupes)}")
    if not cases:
        raise SkillError(f"{meta.id}: no cases")
    if not callable(getattr(grader, "grade", None)):
        raise SkillError(f"{path}/grade.py must define grade(response, ctx)")
    return Skill(meta=meta, path=path, cases=cases, grade=grader.grade)


def discover_skills(directory: Path | None = None) -> list[Skill]:
    d = directory or paths.skills_dir()
    skills = [
        load_skill(p)
        for p in sorted(d.iterdir())
        if p.is_dir() and not p.name.startswith(("_", ".")) and (p / "skill.yaml").exists()
    ]
    return skills
