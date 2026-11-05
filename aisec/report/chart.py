"""Dependency-free SVG grouped bar chart (pass rate by category, one bar per target)."""

from __future__ import annotations

from html import escape

from aisec.report.aggregate import Summary

PALETTE = ["#d97757", "#4f6bed", "#2a9d8f", "#e9c46a", "#8d6cab", "#6c757d"]


def render_svg(s: Summary, title: str = "Pass rate by category") -> str:
    cats = list(s.by_category)
    targets = s.targets
    row_h, bar_h, label_w, chart_w = 18 * max(1, len(targets)) + 14, 16, 210, 420
    top = 74
    height = top + row_h * len(cats) + 40
    width = label_w + chart_w + 70
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif" font-size="12">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="12" y="22" font-size="15" font-weight="bold">{escape(title)}</text>',
    ]
    if s.any_mock:
        parts.append(
            '<text x="12" y="40" fill="#b00020" font-size="11">SYNTHETIC mock data — '
            "illustrates the report format, not real model behaviour</text>"
        )
    for i, t in enumerate(targets):
        x = label_w + i * 130
        parts.append(
            f'<rect x="{x}" y="{height - 26}" width="12" height="12" fill="{PALETTE[i % len(PALETTE)]}"/>'
        )
        parts.append(f'<text x="{x + 18}" y="{height - 16}">{escape(t)}</text>')
    for pct in (0, 25, 50, 75, 100):
        x = label_w + chart_w * pct / 100
        parts.append(
            f'<line x1="{x}" y1="{top - 6}" x2="{x}" y2="{top + row_h * len(cats)}" stroke="#e5e5e5"/>'
        )
        parts.append(
            f'<text x="{x}" y="{top - 9}" text-anchor="middle" fill="#888" font-size="10">{pct}%</text>'
        )
    for ci, cat in enumerate(cats):
        y0 = top + ci * row_h
        parts.append(
            f'<text x="{label_w - 8}" y="{y0 + row_h / 2 + 4}" text-anchor="end">{escape(cat)}</text>'
        )
        for ti, t in enumerate(targets):
            b = s.by_category[cat].get(t)
            rate = b.pass_rate if b and b.total else 0.0
            y = y0 + 6 + ti * 18
            w = chart_w * rate
            parts.append(
                f'<rect x="{label_w}" y="{y}" width="{w:.1f}" height="{bar_h - 2}" '
                f'fill="{PALETTE[ti % len(PALETTE)]}"><title>{escape(t)}: {rate:.0%}</title></rect>'
            )
            label = f"{rate:.0%}" if b and b.total else "n/a"
            parts.append(f'<text x="{label_w + w + 4:.1f}" y="{y + bar_h - 5}" font-size="10">{label}</text>')
    parts.append("</svg>")
    return "\n".join(parts)
