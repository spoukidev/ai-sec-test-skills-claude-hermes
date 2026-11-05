"""Self-contained HTML report (Jinja2) with an inline SVG chart and a filterable case table."""

from __future__ import annotations

from jinja2 import Environment, select_autoescape

from aisec.report.aggregate import Summary
from aisec.report.chart import render_svg
from aisec.report.markdown import MOCK_BANNER

TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{{ title }}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
 body{font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;margin:2rem auto;max-width:1200px;color:#222;padding:0 1rem}
 table{border-collapse:collapse;width:100%;margin:1rem 0;font-size:.9rem}
 th,td{border:1px solid #ddd;padding:.35rem .5rem;text-align:left;vertical-align:top}
 th{background:#f6f6f6} code{background:#f2f2f2;padding:0 .2rem;border-radius:3px}
 .pass{color:#1b7f3b;font-weight:600}.fail{color:#b00020;font-weight:600}.inconclusive{color:#a66b00;font-weight:600}
 .banner{background:#fff4e5;border-left:4px solid #e08b00;padding:.75rem 1rem;margin:1rem 0}
 .filters{display:flex;gap:.75rem;flex-wrap:wrap;margin:.5rem 0} .filters select,.filters input{padding:.25rem}
 td.ex{font-family:ui-monospace,Menlo,monospace;font-size:.8rem;max-width:420px;word-break:break-word}
</style></head><body>
<h1>{{ title }}</h1>
{% if s.any_mock %}<div class="banner">{{ banner }}</div>{% endif %}
<p><b>Runs:</b> {% for r in s.run_ids %}<code>{{ r }}</code> {% endfor %}<br>
<b>Cases graded:</b> {{ s.records|length }}</p>

<h2>Summary by model</h2>
<table><tr><th>Target</th><th>Model id</th><th>Overall pass</th><th>Attack resistance</th><th>Hard-negative helpfulness</th><th>Fail</th><th>Inconclusive</th><th>Mean score</th></tr>
{% for t in s.targets %}{% set ts = s.by_target[t] %}
<tr><td><code>{{ t }}</code></td><td>{{ ts.model_ids|sort|join(', ') }}</td>
<td>{{ pct(ts.overall) }}</td><td>{{ pct(ts.attacks) }}</td><td>{{ pct(ts.hard_negatives) }}</td>
<td>{{ ts.overall.failed }}</td><td>{{ ts.overall.inconclusive }}</td><td>{{ '%.2f'|format(ts.overall.mean_score) }}</td></tr>
{% endfor %}</table>

<h2>Pass rate by category</h2>
{{ svg|safe }}
<table><tr><th>Category</th>{% for t in s.targets %}<th>{{ t }}</th>{% endfor %}</tr>
{% for cat, row in s.by_category.items() %}<tr><td>{{ cat }}</td>{% for t in s.targets %}<td>{{ pct(row.get(t)) }}</td>{% endfor %}</tr>{% endfor %}
</table>

<h2>Pass rate by skill</h2>
<table><tr><th>Skill</th><th>Category</th>{% for t in s.targets %}<th>{{ t }}</th>{% endfor %}</tr>
{% for sk, row in s.by_skill.items() %}<tr><td><code>{{ sk }}</code></td><td>{{ s.skill_category[sk] }}</td>{% for t in s.targets %}<td>{{ pct(row.get(t)) }}</td>{% endfor %}</tr>{% endfor %}
</table>

<h2>Cost and latency</h2>
<table><tr><th>Target</th><th>Mean latency (ms)</th><th>p50</th><th>p95</th><th>Input tok</th><th>Output tok</th><th>Est. cost (USD)</th><th>Errors</th></tr>
{% for t in s.targets %}{% set ts = s.by_target[t] %}<tr><td>{{ t }}</td><td>{{ '%.0f'|format(ts.mean_latency) }}</td><td>{{ '%.0f'|format(ts.pct(0.5)) }}</td><td>{{ '%.0f'|format(ts.pct(0.95)) }}</td><td>{{ ts.input_tokens }}</td><td>{{ ts.output_tokens }}</td><td>{{ '%.4f'|format(ts.cost_usd) }}</td><td>{{ ts.errors }}</td></tr>{% endfor %}
</table>

<h2>All cases</h2>
<div class="filters">
 <label>Target <select id="fTarget"><option value="">all</option>{% for t in s.targets %}<option>{{ t }}</option>{% endfor %}</select></label>
 <label>Verdict <select id="fVerdict"><option value="">all</option><option>pass</option><option>fail</option><option>inconclusive</option></select></label>
 <label>Category <select id="fCat"><option value="">all</option>{% for c in s.by_category %}<option>{{ c }}</option>{% endfor %}</select></label>
 <label>Search <input id="fText" placeholder="skill, case, evidence…"></label>
</div>
<table id="cases"><thead><tr><th>Target</th><th>Category</th><th>Skill / case</th><th>Verdict</th><th>Score</th><th>Evidence</th><th>Response excerpt</th></tr></thead><tbody>
{% for r in records %}<tr data-target="{{ r.target }}" data-verdict="{{ r.verdict }}" data-cat="{{ r.category }}">
<td>{{ r.target }}</td><td>{{ r.category }}</td><td><code>{{ r.skill_id }}/{{ r.case_id }}</code>{% if r.hard_negative %} <small>(hard negative)</small>{% endif %}</td>
<td class="{{ r.verdict }}">{{ r.verdict }}</td><td>{{ r.score }}</td><td>{{ r.evidence[:3]|join(' · ') }}</td><td class="ex">{{ r.response_excerpt }}</td></tr>
{% endfor %}</tbody></table>
<script>
(function(){const ids=["fTarget","fVerdict","fCat","fText"];function apply(){const t=fTarget.value,v=fVerdict.value,c=fCat.value,q=fText.value.toLowerCase();
document.querySelectorAll("#cases tbody tr").forEach(function(tr){const ok=(!t||tr.dataset.target===t)&&(!v||tr.dataset.verdict===v)&&(!c||tr.dataset.cat===c)&&(!q||tr.textContent.toLowerCase().includes(q));tr.style.display=ok?"":"none";});}
ids.forEach(function(i){document.getElementById(i).addEventListener("input",apply);});})();
</script>
<p><small>Generated by aisec. Educational, defensive evaluation only.</small></p>
</body></html>
"""


def render_html(s: Summary, title: str = "AI Security Test Report") -> str:
    env = Environment(autoescape=select_autoescape(default=True, default_for_string=True))

    def pct(b) -> str:
        if b is None or not b.total:
            return "–"
        return f"{b.pass_rate * 100:.0f}% ({b.passed}/{b.total})"

    tpl = env.from_string(TEMPLATE)
    records = sorted(s.records, key=lambda r: (r.target, r.category, r.skill_id, r.case_id))
    return tpl.render(
        s=s,
        title=title,
        pct=pct,
        svg=render_svg(s),
        banner=MOCK_BANNER.replace("> ", "").replace("*", "").replace("`", ""),
        records=records,
    )
