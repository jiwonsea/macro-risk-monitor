"""Render thesis review handoffs for external reviewers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .. import config as cfg
from ..engine.hypothesis import load_risk
from ..schemas import Risk


def render_review_handoff(risk: Risk, override_path: Path, today: date) -> str:
    override_data = {}
    if override_path.exists():
        with override_path.open(encoding="utf-8") as fh:
            override_data = yaml.safe_load(fh) or {}

    env = Environment(
        loader=FileSystemLoader(cfg.TEMPLATE_DIR),
        autoescape=select_autoescape(default_for_string=False, default=False),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("codex_review_handoff.md.j2")
    return template.render(
        risk=risk,
        override_path=override_path,
        override_data=override_data,
        today=today,
        project_root=cfg.BASE_DIR,
    )


def write_review_handoff(
    risk_name: str,
    out_dir: Path = Path("notes/codex_handoffs"),
    today: date | None = None,
) -> Path:
    today = today or date.today()
    risk_path = cfg.THESES_DIR / f"{risk_name}.yaml"
    override_path = cfg.BASE_DIR / "data" / "manual_override" / f"{risk_name}.yaml"
    risk = load_risk(risk_path)
    out_path = cfg.BASE_DIR / out_dir / f"{today.isoformat()}_{risk_name}_review.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_review_handoff(risk, override_path, today), encoding="utf-8")
    return out_path
