"""Markdown report renderer."""

from __future__ import annotations

from aisec.report.aggregate import Bucket, Summary

MOCK_BANNER = (
    "> ⚠️ **SYNTHETIC DATA.** These results were produced by the offline *mock* client "
    "(`aisec run --mock`). They demonstrate the report format only and say **nothing** about "
    "how the real Claude or Hermes models behave. Run with real API keys for real measurements."
)


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def _cell(b: Bucket | None) -> str:
    if b is None or not b.total:
        return "–"
    return f"{_pct(b.pass_rate)} ({b.passed}/{b.total})"


def _bar(rate: float, width: int = 20) -> str:
    filled = int(round(rate * width))
    return "█" * filled + "░" * (width - filled)


def _esc(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def _target_label(s: Summary, t: str) -> str:
    models = ", ".join(sorted(s.by_target[t].model_ids))
    return f"`{t}` ({models})"


def render_markdown(s: Summary, title: str = "AI Security Test Report", top_n: int = 15) -> str:
    out: list[str] = [f"# {title}", ""]
    if s.any_mock:
        out += [MOCK_BANNER, ""]
    out += [
        f"- **Runs:** {', '.join(f'`{r}`' for r in s.run_ids)}",
        "- **Targets:** " + ", ".join(_target_label(s, t) for t in s.targets),
        f"- **Cases graded:** {len(s.records)}",
        "",
        "Pass = the model behaved securely (attack resisted, or benign hard-negative answered). "
        "See `docs/INTERPRETING_RESULTS.md`.",
        "",
        "## Summary by model",
        "",
        "| Target | Overall pass | Attack resistance | Hard-negative helpfulness | Fail | Inconclusive | Mean score |",
        "|---|---|---|---|---|---|---|",
    ]
    for t in s.targets:
        ts = s.by_target[t]
        out.append(
            f"| `{t}` | {_cell(ts.overall)} | {_cell(ts.attacks)} | {_cell(ts.hard_negatives)} | "
            f"{ts.overall.failed} | {ts.overall.inconclusive} | {ts.overall.mean_score:.2f} |"
        )
    out += ["", "```text"]
    for t in s.targets:
        r = s.by_target[t].attacks.pass_rate
        out.append(f"{t:<14} attack resistance {_bar(r)} {_pct(r)}")
    out += ["```", "", "## Pass rate by category (side by side)", ""]
    out.append("| Category | " + " | ".join(f"`{t}`" for t in s.targets) + " |")
    out.append("|---|" + "---|" * len(s.targets))
    for cat, row in s.by_category.items():
        out.append(f"| {cat} | " + " | ".join(_cell(row.get(t)) for t in s.targets) + " |")
    out += ["", "## Pass rate by skill", ""]
    out.append("| Skill | Category | " + " | ".join(f"`{t}`" for t in s.targets) + " |")
    out.append("|---|---|" + "---|" * len(s.targets))
    for sk, row in s.by_skill.items():
        out.append(
            f"| `{sk}` | {s.skill_category[sk]} | " + " | ".join(_cell(row.get(t)) for t in s.targets) + " |"
        )
    out += ["", f"## Top failing cases (max {top_n})", ""]
    fails = s.top_failures(top_n)
    if not fails:
        out.append("_No failures._ 🎉")
    else:
        out.append("| Target | Skill / case | Severity | Evidence | Response excerpt |")
        out.append("|---|---|---|---|---|")
        for r in fails:
            ev = _esc("; ".join(r.evidence[:2]))[:220]
            ex = _esc(r.response_excerpt)[:160]
            hn = " (hard negative → over-refusal)" if r.hard_negative else ""
            out.append(f"| `{r.target}` | `{r.skill_id}/{r.case_id}`{hn} | {r.severity} | {ev} | {ex} |")
    out += [
        "",
        "## Cost and latency",
        "",
        "| Target | Mean latency (ms) | p50 | p95 | Input tok | Output tok | Est. cost (USD) | Errors | Judged |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for t in s.targets:
        ts = s.by_target[t]
        out.append(
            f"| `{t}` | {ts.mean_latency:.0f} | {ts.pct(0.5):.0f} | {ts.pct(0.95):.0f} | {ts.input_tokens} | "
            f"{ts.output_tokens} | {ts.cost_usd:.4f} | {ts.errors} | {ts.judged} |"
        )
    out += [
        "",
        "_Costs are estimates from `price_*_per_mtok` in config/models.yaml; latency includes all turns._",
        "",
    ]
    return "\n".join(out)
