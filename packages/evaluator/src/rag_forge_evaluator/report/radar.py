"""Inline SVG radar chart generator for audit reports."""

import math

from rag_forge_evaluator.engine import MetricResult

_SVG_SIZE = 400
_CENTER = _SVG_SIZE / 2
_RADIUS = 150
_LABEL_OFFSET = 25


def generate_radar_svg(metrics: list[MetricResult]) -> str:
    if not metrics:
        return (
            f'<svg width="{_SVG_SIZE}" height="{_SVG_SIZE}" xmlns="http://www.w3.org/2000/svg">'
            f'<text x="{_CENTER}" y="{_CENTER}" text-anchor="middle" fill="#999" '
            f'font-family="sans-serif" font-size="14">No metrics to display</text></svg>'
        )

    n = len(metrics)
    angle_step = 2 * math.pi / n
    lines: list[str] = [
        f'<svg width="{_SVG_SIZE}" height="{_SVG_SIZE}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{_SVG_SIZE}" height="{_SVG_SIZE}" fill="white"/>',
    ]

    for pct in (0.25, 0.5, 0.75, 1.0):
        r = _RADIUS * pct
        lines.append(f'<circle cx="{_CENTER}" cy="{_CENTER}" r="{r:.1f}" fill="none" stroke="#e0e0e0" stroke-width="1"/>')

    for i, m in enumerate(metrics):
        angle = -math.pi / 2 + i * angle_step
        x = _CENTER + _RADIUS * math.cos(angle)
        y = _CENTER + _RADIUS * math.sin(angle)
        lines.append(f'<line x1="{_CENTER}" y1="{_CENTER}" x2="{x:.1f}" y2="{y:.1f}" stroke="#ccc" stroke-width="1"/>')

        lx = _CENTER + (_RADIUS + _LABEL_OFFSET) * math.cos(angle)
        ly = _CENTER + (_RADIUS + _LABEL_OFFSET) * math.sin(angle)
        anchor = "middle"
        if math.cos(angle) > 0.3:
            anchor = "start"
        elif math.cos(angle) < -0.3:
            anchor = "end"
        lines.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" dominant-baseline="central" font-family="sans-serif" font-size="11" fill="#555">{m.name}</text>')

    threshold_points: list[str] = []
    for i, m in enumerate(metrics):
        angle = -math.pi / 2 + i * angle_step
        r = _RADIUS * min(m.threshold, 1.0)
        x = _CENTER + r * math.cos(angle)
        y = _CENTER + r * math.sin(angle)
        threshold_points.append(f"{x:.1f},{y:.1f}")
    lines.append(f'<polygon points="{" ".join(threshold_points)}" fill="rgba(255,193,7,0.1)" stroke="#ffc107" stroke-width="1" stroke-dasharray="4,4"/>')

    score_points: list[str] = []
    for i, m in enumerate(metrics):
        angle = -math.pi / 2 + i * angle_step
        r = _RADIUS * min(m.score, 1.0)
        x = _CENTER + r * math.cos(angle)
        y = _CENTER + r * math.sin(angle)
        score_points.append(f"{x:.1f},{y:.1f}")
    lines.append(f'<polygon points="{" ".join(score_points)}" fill="rgba(40,167,69,0.2)" stroke="#28a745" stroke-width="2"/>')

    for i, m in enumerate(metrics):
        angle = -math.pi / 2 + i * angle_step
        r = _RADIUS * min(m.score, 1.0)
        x = _CENTER + r * math.cos(angle)
        y = _CENTER + r * math.sin(angle)
        color = "#28a745" if m.passed else "#dc3545"
        lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}"/>')

    lines.append("</svg>")
    return "\n".join(lines)
