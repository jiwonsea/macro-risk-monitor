from pathlib import Path
from shutil import copyfile

from macro_risk_monitor.ai.patch import apply_patch, render_diff
from macro_risk_monitor.ai.review_parser import parse_feedback
from macro_risk_monitor.engine.hypothesis import load_risk


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"


def test_apply_review_fixture_generates_diff_and_valid_yaml(tmp_path):
    risk_path = tmp_path / "ai_circular_revenue.yaml"
    override_path = tmp_path / "ai_circular_revenue_override.yaml"
    copyfile(ROOT / "theses" / "ai_circular_revenue.yaml", risk_path)
    copyfile(ROOT / "data" / "manual_override" / "ai_circular_revenue.yaml", override_path)

    feedback = (FIXTURES / "sample_feedback_ai_circular.md").read_text(encoding="utf-8")
    patch = parse_feedback(feedback, "ai_circular_revenue")

    assert patch.entries

    risk_diff, override_diff = render_diff(patch, risk_path, override_path)
    assert "\n+" in risk_diff or "\n-" in risk_diff
    assert "nvda_receivables_quality" in risk_diff
    assert "nvda_receivables_days_qoq_change" in override_diff

    apply_patch(patch, risk_path, override_path)
    risk = load_risk(risk_path)
    trigger = next(t for t in risk.triggers if t.id == "nvda_data_center_qoq")
    assert trigger.threshold.red == "<= -3"
    assert any(t.id == "nvda_receivables_quality" for t in risk.triggers)
