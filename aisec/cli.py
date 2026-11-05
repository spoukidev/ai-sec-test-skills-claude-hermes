"""Command-line interface: ``aisec list``, ``aisec run``, ``aisec report``, ``aisec validate``."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from aisec import __version__, paths
from aisec.config import load_config
from aisec.models.base import ModelClientError
from aisec.skills import SkillError, discover_skills

ETHICS = (
    "Educational, defensive use only. Only test models/deployments you own or are "
    "explicitly authorized to test."
)


def load_dotenv(path: Path) -> int:
    """Minimal .env loader (KEY=VALUE). Never overrides variables already set. Returns #loaded."""
    if not path.is_file():
        return 0
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip().removeprefix("export ").strip(), v.strip().strip('"').strip("'")
        if k and v and k not in os.environ:
            os.environ[k] = v
            n += 1
    return n


def _split(values: list[str] | None) -> list[str]:
    out: list[str] = []
    for v in values or []:
        out += [x.strip() for x in v.split(",") if x.strip()]
    return out


# ---------------------------------------------------------------------------- list
def cmd_list(args: argparse.Namespace) -> int:
    skills = discover_skills()
    if args.suite:
        from aisec.harness.runner import select_skills

        cfg = load_config()
        skills = select_skills(skills, cfg.suites[args.suite])
    if args.json:
        print(
            json.dumps(
                [
                    {
                        **s.meta.model_dump(),
                        "cases": len(s.cases),
                        "hard_negatives": sum(c.hard_negative for c in s.cases),
                    }
                    for s in skills
                ],
                indent=2,
            )
        )
        return 0
    print(f"{'SKILL':<30} {'CATEGORY':<26} {'SEV':<9} {'CASES':>5} {'HARD-NEG':>8}  TOOLS")
    for s in skills:
        hn = sum(c.hard_negative for c in s.cases)
        print(
            f"{s.id:<30} {s.meta.category:<26} {s.meta.severity:<9} {len(s.cases):>5} {hn:>8}  "
            f"{'yes' if s.meta.requires_tools else '-'}"
        )
        if args.cases:
            for c in s.cases:
                print(f"    - {c.id}{' (hard negative)' if c.hard_negative else ''}: {c.description}")
    total = sum(len(s.cases) for s in skills)
    hn = sum(c.hard_negative for s in skills for c in s.cases)
    cats = sorted({s.meta.category for s in skills})
    print(f"\n{len(skills)} skills · {total} cases · {hn} hard negatives · {len(cats)} categories")
    return 0


# ---------------------------------------------------------------------------- run
def cmd_run(args: argparse.Namespace) -> int:
    from aisec.harness.runner import Runner, RunOptions
    from aisec.report.aggregate import summarize
    from aisec.report.markdown import render_markdown

    cfg = load_config()
    targets = _split(args.models)
    opts = RunOptions(
        targets=targets,
        suite=args.suite,
        skills=_split(args.skill) or None,
        judge=args.judge,
        mock=args.mock,
        tools=args.tools,
        output_dir=Path(args.output_dir),
        max_cases_per_skill=args.max_cases,
    )
    print(f"aisec {__version__} — {ETHICS}", file=sys.stderr)
    if args.mock:
        print("MOCK MODE: no network calls; results are synthetic.", file=sys.stderr)
    try:
        runner = Runner(cfg, discover_skills(), opts, progress=lambda m: print(m, file=sys.stderr))
    except (ModelClientError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    n_cases = sum(min(len(s.cases), runner.max_cases or 10**9) for s in runner.skills)
    print(
        f"running {len(runner.skills)} skills / {n_cases} cases on {', '.join(targets)}"
        f"{' with LLM judge' if runner.judge else ''}",
        file=sys.stderr,
    )
    result = runner.run()
    summary = summarize(result.records)

    def rate(b) -> str:
        return f"{b.pass_rate:.0%}" if b.total else "n/a"

    for t in summary.targets:
        ts = summary.by_target[t]
        print(
            f"{t}: pass {ts.overall.passed}/{ts.overall.total} · fail {ts.overall.failed} · "
            f"inconclusive {ts.overall.inconclusive} · attack resistance {rate(ts.attacks)} · "
            f"hard-negative helpfulness {rate(ts.hard_negatives)}"
        )
    print(f"wrote {result.path} (copied to {result.path.parent / 'latest.jsonl'})")
    if args.report:
        md = result.path.with_suffix(".md")
        md.write_text(render_markdown(summary), encoding="utf-8")
        print(f"wrote {md}")
    if args.fail_under is not None:
        rates = [summary.by_target[t].overall.pass_rate for t in summary.targets]
        if any(r < args.fail_under for r in rates):
            print(f"pass rate below --fail-under {args.fail_under}", file=sys.stderr)
            return 1
    return 0


# ---------------------------------------------------------------------------- report
def cmd_report(args: argparse.Namespace) -> int:
    from aisec.report.aggregate import load_records, summarize
    from aisec.report.chart import render_svg
    from aisec.report.html import render_html
    from aisec.report.markdown import render_markdown

    inputs = [Path(p) for p in args.inputs]
    missing = [str(p) for p in inputs if not p.is_file()]
    if missing:
        print(f"error: input not found: {', '.join(missing)}", file=sys.stderr)
        return 2
    summary = summarize(load_records(inputs))
    if not summary.records:
        print("error: no records in input", file=sys.stderr)
        return 2
    md = render_markdown(summary, title=args.title)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(md, encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(md)
    if args.html:
        Path(args.html).parent.mkdir(parents=True, exist_ok=True)
        Path(args.html).write_text(render_html(summary, title=args.title), encoding="utf-8")
        print(f"wrote {args.html}")
    if args.svg:
        Path(args.svg).parent.mkdir(parents=True, exist_ok=True)
        Path(args.svg).write_text(render_svg(summary), encoding="utf-8")
        print(f"wrote {args.svg}")
    return 0


# ---------------------------------------------------------------------------- validate
def cmd_validate(args: argparse.Namespace) -> int:
    from aisec.payloads import load_payloads

    load_config()
    skills = discover_skills()
    for f in sorted(paths.payloads_dir().glob("*.jsonl")):
        print(f"payloads/{f.name}: {len(load_payloads(f.name))} entries OK")
    total = sum(len(s.cases) for s in skills)
    hn = sum(c.hard_negative for s in skills for c in s.cases)
    cats = {s.meta.category for s in skills}
    print(f"{len(skills)} skills, {total} cases, {hn} hard negatives, {len(cats)} categories")
    ok = len(skills) >= 15 and total >= 80 and hn >= 10
    print("v1 corpus targets (≥15 skills, ≥80 cases, ≥10 hard negatives):", "MET" if ok else "NOT MET")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aisec", description=f"AI security test skills for Claude & Hermes. {ETHICS}"
    )
    p.add_argument("--version", action="version", version=f"aisec {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    pl = sub.add_parser("list", help="list available skills")
    pl.add_argument("--suite", help="only skills selected by this suite")
    pl.add_argument("--cases", action="store_true", help="also list every case")
    pl.add_argument("--json", action="store_true", help="machine-readable output")
    pl.set_defaults(func=cmd_list)

    pr = sub.add_parser("run", help="run skills against one or more targets")
    pr.add_argument(
        "--models",
        "-m",
        action="append",
        required=True,
        help="comma-separated targets from config/models.yaml (e.g. claude,hermes)",
    )
    pr.add_argument(
        "--suite", "-s", default="default", help="suite from config/suites.yaml (default: default)"
    )
    pr.add_argument("--skill", action="append", help="run only these skill ids (comma-separated or repeated)")
    pr.add_argument("--judge", action="store_true", help="enable the optional LLM judge (config/judge.yaml)")
    pr.add_argument(
        "--mock", action="store_true", help="use the offline mock client (no API keys, no network)"
    )
    tools = pr.add_mutually_exclusive_group()
    tools.add_argument(
        "--tools", dest="tools", action="store_true", default=None, help="include tool-misuse skills"
    )
    tools.add_argument("--no-tools", dest="tools", action="store_false", help="exclude tool-misuse skills")
    pr.add_argument("--max-cases", type=int, help="max cases per skill (cost control)")
    pr.add_argument("--output-dir", "-o", default=str(paths.results_dir()), help="where to write JSONL")
    pr.add_argument("--report", action="store_true", help="also write a Markdown report next to the JSONL")
    pr.add_argument(
        "--fail-under", type=float, help="exit 1 if any target's overall pass rate is below this (0..1)"
    )
    pr.set_defaults(func=cmd_run)

    prep = sub.add_parser("report", help="render Markdown/HTML report from JSONL run logs")
    prep.add_argument("inputs", nargs="+", help="one or more JSONL files")
    prep.add_argument("-o", "--output", help="Markdown output path (default: stdout)")
    prep.add_argument("--html", help="also write a self-contained HTML report")
    prep.add_argument("--svg", help="also write an SVG category chart")
    prep.add_argument("--title", default="AI Security Test Report")
    prep.set_defaults(func=cmd_report)

    pv = sub.add_parser("validate", help="validate skills, payloads and config; check corpus size")
    pv.set_defaults(func=cmd_validate)
    return p


def main(argv: list[str] | None = None) -> int:
    load_dotenv(paths.project_root() / ".env")
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except SkillError as exc:
        print(f"skill error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
