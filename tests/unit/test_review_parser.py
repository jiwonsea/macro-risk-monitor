from pathlib import Path
import sys
import types

import pytest

from macro_risk_monitor.ai.review_parser import parse_feedback
from macro_risk_monitor.schemas import PatchAction


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_parse_feedback_prefers_fenced_patch_json():
    patch = parse_feedback((FIXTURES / "sample_feedback.md").read_text(encoding="utf-8"), "sample")

    assert patch.thesis_name == "sample"
    assert patch.entries[0].target_id == "a"
    assert patch.entries[0].action == PatchAction.MODIFY_THRESHOLD
    assert patch.entries[0].new_threshold.red == ">= 2"


def test_parse_feedback_without_fenced_json_raises_when_no_llm(monkeypatch):
    monkeypatch.setattr("macro_risk_monitor.config.ANTHROPIC_API_KEY", None)

    with pytest.raises(RuntimeError, match="No fenced JSON patch"):
        parse_feedback("No machine-readable feedback.", "unknown")


def test_parse_feedback_llm_fallback_returns_patch(monkeypatch):
    class _TextBlock:
        type = "text"
        text = (
            '{"thesis_name":"x","reviewer":"codex","review_date":"2026-05-27",'
            '"entries":[{"target_id":"a","action":"KEEP","rationale":"ok"}]}'
        )

    class _Messages:
        def create(self, **kwargs):
            return types.SimpleNamespace(content=[_TextBlock()])

    class _FakeAnthropic:
        def __init__(self, api_key):
            self.api_key = api_key
            self.messages = _Messages()

    fake_module = types.SimpleNamespace(Anthropic=_FakeAnthropic)
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)
    monkeypatch.setattr("macro_risk_monitor.config.ANTHROPIC_API_KEY", "dummy")

    patch = parse_feedback("No fenced JSON, use fallback.", "x")

    assert patch.thesis_name == "x"
    assert patch.entries[0].target_id == "a"
    assert patch.entries[0].action.value == "KEEP"
