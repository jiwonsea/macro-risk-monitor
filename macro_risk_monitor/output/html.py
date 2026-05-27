"""Render Report -> HTML using jinja2 templates."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import markdown as md_lib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .. import config as cfg
from ..schemas import Report, Status
from .charts import render_trigger_bar


def render_report(
    report: Report,
    out_path: Path,
    state_diff: list[tuple[str, Status, Status]] | None = None,
) -> Path:
    env = Environment(
        loader=FileSystemLoader(cfg.TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "j2"]),
    )

    rows = _build_table_rows(report)
    trigger_table_html = env.get_template("trigger_table.html.j2").render(rows=rows)
    chart_section = render_trigger_bar(report.verdicts, {t.id: t for t in report.risk.triggers})

    analysis_html = md_lib.markdown(
        report.llm_analysis_md,
        extensions=["tables", "fenced_code"],
        output_format="html5",
    )

    css_inline = (cfg.STATIC_DIR / "report.css").read_text(encoding="utf-8")

    rendered = env.get_template("report.html.j2").render(
        report=report,
        css_inline=css_inline,
        trigger_table_html=trigger_table_html,
        chart_section=chart_section,
        analysis_html=analysis_html,
        state_diff=state_diff or [],
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")
    return out_path


def _build_table_rows(report: Report) -> list[dict]:
    trigger_by_id = {t.id: t for t in report.risk.triggers}
    rows: list[dict] = []
    for v in report.verdicts:
        t = trigger_by_id.get(v.trigger_id)
        display_value = (
            v.reading.display_value
            if v.reading and v.reading.display_value is not None
            else v.reading.value if v.reading else None
        )
        rows.append(
            {
                "id": v.trigger_id,
                "category": (t.category.value if t else "unknown"),
                "status": v.status.value,
                "value": _format_value(display_value),
                "unit": (t.unit if t else None),
                "as_of": (v.reading.as_of.isoformat() if v.reading and v.reading.as_of else None),
                "threshold_red": (t.threshold.red if t else None),
                "source": (t.source.value if t else "—"),
                "source_url": v.reading.source_url if v.reading else None,
                "description": (t.description if t else None),
            }
        )
    return rows


def _format_value(value):
    if isinstance(value, float):
        return f"{value:g}"
    return value


def default_html_path(risk_name: str, generated_at: datetime | None = None) -> Path:
    stamp = (generated_at or datetime.now()).strftime("%Y-%m-%d")
    return cfg.REPORTS_HTML_DIR / f"{stamp}-{risk_name}.html"
