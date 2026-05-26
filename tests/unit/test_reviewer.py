from datetime import date
from pathlib import Path

from macro_risk_monitor.ai.reviewer import render_review_handoff, write_review_handoff
from macro_risk_monitor.engine.hypothesis import load_risk


ROOT = Path(__file__).resolve().parents[2]


def test_render_review_handoff_contains_patch_contract():
    risk = load_risk(ROOT / "theses/ai_circular_revenue.yaml")

    md = render_review_handoff(
        risk,
        ROOT / "data/manual_override/ai_circular_revenue.yaml",
        date(2026, 5, 27),
    )

    assert "# Codex review handoff - ai_circular_revenue" in md
    assert "```patch" in md
    assert "openai_implied_valuation_discount" in md
    assert '"entries"' in md


def test_write_review_handoff_uses_expected_name(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)

    path = write_review_handoff("ai_circular_revenue", tmp_path, date(2026, 5, 27))

    assert path.name == "2026-05-27_ai_circular_revenue_review.md"
    assert path.exists()
