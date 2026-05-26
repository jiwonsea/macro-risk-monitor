"""risk_parser falls back to a heuristic skeleton when no LLM is wired up."""

from macro_risk_monitor.ai.risk_parser import parse_risk


def test_heuristic_returns_valid_risk(monkeypatch):
    monkeypatch.setattr("macro_risk_monitor.config.ANTHROPIC_API_KEY", None)

    risk = parse_risk("미국 10년물 4.5% 돌파")
    assert risk.name
    assert risk.title.startswith("미국")
    assert risk.triggers
    assert risk.triggers[0].id == "placeholder"


def test_long_input_truncated_in_title(monkeypatch):
    monkeypatch.setattr("macro_risk_monitor.config.ANTHROPIC_API_KEY", None)

    text = "x" * 200
    risk = parse_risk(text)
    assert len(risk.title) <= 80
