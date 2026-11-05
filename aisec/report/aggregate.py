"""Aggregate JSONL run records into report-ready statistics."""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from aisec.schema import RunRecord

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@dataclass
class Bucket:
    passed: int = 0
    failed: int = 0
    inconclusive: int = 0
    score_sum: float = 0.0

    def add(self, r: RunRecord) -> None:
        if r.verdict == "pass":
            self.passed += 1
        elif r.verdict == "fail":
            self.failed += 1
        else:
            self.inconclusive += 1
        self.score_sum += r.score

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.inconclusive

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def mean_score(self) -> float:
        return self.score_sum / self.total if self.total else 0.0


@dataclass
class TargetStats:
    target: str
    model_ids: set[str] = field(default_factory=set)
    overall: Bucket = field(default_factory=Bucket)
    attacks: Bucket = field(default_factory=Bucket)
    hard_negatives: Bucket = field(default_factory=Bucket)
    latencies: list[float] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    errors: int = 0
    judged: int = 0

    def pct(self, q: float) -> float:
        if not self.latencies:
            return 0.0
        xs = sorted(self.latencies)
        return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))]

    @property
    def mean_latency(self) -> float:
        return statistics.fmean(self.latencies) if self.latencies else 0.0


@dataclass
class Summary:
    records: list[RunRecord]
    targets: list[str]
    run_ids: list[str]
    by_target: dict[str, TargetStats]
    by_category: dict[str, dict[str, Bucket]]
    by_skill: dict[str, dict[str, Bucket]]
    skill_category: dict[str, str]
    any_mock: bool

    def top_failures(self, n: int = 15) -> list[RunRecord]:
        fails = [r for r in self.records if r.verdict == "fail"]
        # attacks before over-refusals, then by severity
        fails.sort(
            key=lambda r: (
                r.hard_negative,
                SEVERITY_RANK.get(r.severity, 9),
                r.score,
                r.target,
                r.skill_id,
                r.case_id,
            )
        )
        return fails[:n]


def load_records(paths: list[Path] | Path) -> list[RunRecord]:
    if isinstance(paths, (str, Path)):
        paths = [Path(paths)]
    records: list[RunRecord] = []
    for p in paths:
        for lineno, line in enumerate(Path(p).read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                records.append(RunRecord(**json.loads(line)))
            except Exception as exc:  # noqa: BLE001
                raise ValueError(f"{p}:{lineno}: invalid record: {exc}") from exc
    return records


def summarize(records: list[RunRecord]) -> Summary:
    targets = list(dict.fromkeys(r.target for r in records))
    by_target = {t: TargetStats(target=t) for t in targets}
    by_category: dict[str, dict[str, Bucket]] = defaultdict(lambda: defaultdict(Bucket))
    by_skill: dict[str, dict[str, Bucket]] = defaultdict(lambda: defaultdict(Bucket))
    skill_category: dict[str, str] = {}
    for r in records:
        ts = by_target[r.target]
        ts.model_ids.add(r.model_id)
        ts.overall.add(r)
        (ts.hard_negatives if r.hard_negative else ts.attacks).add(r)
        ts.latencies.append(r.latency_ms)
        ts.input_tokens += r.input_tokens
        ts.output_tokens += r.output_tokens
        ts.cost_usd += r.cost_usd
        ts.errors += 1 if r.error else 0
        ts.judged += 1 if r.judge else 0
        by_category[r.category][r.target].add(r)
        by_skill[r.skill_id][r.target].add(r)
        skill_category[r.skill_id] = r.category
    return Summary(
        records=records,
        targets=targets,
        run_ids=list(dict.fromkeys(r.run_id for r in records)),
        by_target=by_target,
        by_category={k: dict(v) for k, v in sorted(by_category.items())},
        by_skill={k: dict(v) for k, v in sorted(by_skill.items())},
        skill_category=skill_category,
        any_mock=any(r.mock for r in records),
    )
