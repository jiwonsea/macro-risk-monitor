"""analyze() must degrade to AnalyzeStub on transient Anthropic API failures.

The daily GitHub Actions run promises graceful degradation; a rate-limit or
overloaded-API error mid-run must not crash the whole report build.
"""

from __future__ import annotations

import sys
import types

from macro_risk_monitor import config as cfg
from macro_risk_monitor.ai.analyzer import analyze
from macro_risk_monitor.schemas import (
    Category,
    Risk,
    SourceKind,
    Threshold,
    Trigger,
)


def _risk() -> Risk:
    return Risk(
        name="stub_risk",
        title="Stub Risk",
        hypothesis="test hypothesis",
        triggers=[
            Trigger(
                id="t1",
                category=Category.LEADING,
                source=SourceKind.MANUAL_OVERRIDE,
                threshold=Threshold(red=">= 1"),
            )
        ],
    )


def test_analyze_falls_back_to_stub_on_api_error(monkeypatch):
    monkeypatch.setattr(cfg, "ANTHROPIC_API_KEY", "sk-test-not-real")

    class _FakeMessages:
        @staticmethod
        def create(**kwargs):
            raise RuntimeError("529 overloaded")

    class _FakeAnthropic:
        def __init__(self, api_key: str):
            self.messages = _FakeMessages()

    fake_mod = types.ModuleType("anthropic")
    fake_mod.Anthropic = _FakeAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", fake_mod)

    md, model = analyze(_risk(), [])
    assert model == "stub"
    assert "analyzer stub" in md
