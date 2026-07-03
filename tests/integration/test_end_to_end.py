"""End-to-end pipeline with all external sources stubbed."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from macro_risk_monitor.engine.hypothesis import load_risk
from macro_risk_monitor.pipeline.orchestrator import run_pipeline
from macro_risk_monitor.schemas import Reading, Status
from macro_risk_monitor.sources.base import DataSource

THESES = Path(__file__).resolve().parents[2] / "theses"


class _FakeSource(DataSource):
    name = "fake"

    def __init__(self, value_map: dict[str, float]):
        self.value_map = value_map
        self.seen_as_of: list = []

    def fetch(self, trigger, as_of=None):
        self.seen_as_of.append(as_of)
        v = self.value_map.get(trigger.series)
        return Reading(
            trigger_id=trigger.id,
            value=v,
            as_of=date(2026, 5, 26),
            source_url="https://example.com/fake",
        )


@pytest.fixture(autouse=True)
def _stub_sources(monkeypatch, tmp_path):
    """Replace the registry with deterministic fake sources for the test run."""

    values = {
        "DGS10": 4.62,
        "DGS30": 5.12,
        "MORTGAGE30US": 7.30,
        "BAMLC0A0CM": 110.0,
        "^VIX": 19.0,
    }
    fake = _FakeSource(values)
    monkeypatch.setattr(
        "macro_risk_monitor.pipeline.orchestrator.get_source",
        lambda kind, thesis_name=None: fake,
    )
    from macro_risk_monitor import config as cfg

    monkeypatch.setattr(cfg, "REPORTS_HTML_DIR", tmp_path / "html")
    monkeypatch.setattr(cfg, "REPORTS_RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(cfg, "CACHE_DIR", tmp_path / "cache")
    (tmp_path / "html").mkdir()
    (tmp_path / "raw").mkdir()
    (tmp_path / "cache").mkdir()
    return fake


def test_us_long_end_yield_end_to_end(tmp_path: Path):
    risk = load_risk(THESES / "us_long_end_yield.yaml")
    out = tmp_path / "report.html"
    report = run_pipeline(risk, out_html=out, skip_llm=True)
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    assert "us_long_end_yield" in html
    assert "status-red" in html  # 10Y 4.62 and 30Y 5.12 both trip red
    assert report.decision.action in {"defensive_position", "hedge_increase", "monitor"}
    # All five triggers must produce verdicts
    assert len(report.verdicts) == len(risk.triggers)
    statuses = {v.status for v in report.verdicts}
    assert Status.RED in statuses


def test_run_pipeline_as_of_honesty_and_no_state(_stub_sources, tmp_path: Path):
    """`run --as-of` contract: non-backtestable sources -> honest UNKNOWN,
    backtestable sources receive the historical as_of, state is untouched."""
    from macro_risk_monitor import config as cfg

    risk = load_risk(THESES / "ai_circular_revenue.yaml")
    out = tmp_path / "asof.html"
    report = run_pipeline(risk, out_html=out, skip_llm=True, as_of=date(2026, 1, 15))

    by_id = {v.trigger_id: v for v in report.verdicts}
    # manual_override / news_rss cannot reproduce history -> declared UNKNOWN
    for tid in ("openai_implied_valuation_discount", "circular_revenue_press_attention"):
        assert by_id[tid].status is Status.UNKNOWN
        assert "not backtestable" in by_id[tid].rationale
    # the backtestable source (earnings_transcript_nlp) was fetched with as_of
    assert _stub_sources.seen_as_of == [date(2026, 1, 15)]

    # a replay never writes the state snapshot or history log
    state_dir = cfg.CACHE_DIR / "state"
    assert not state_dir.exists() or not any(state_dir.iterdir())

    assert report.as_of == date(2026, 1, 15)
    html = out.read_text(encoding="utf-8")
    assert "2026-01-15" in html  # as_of banner rendered


def test_report_stamp_uses_as_of_for_replays():
    from datetime import datetime

    from macro_risk_monitor.pipeline.orchestrator import report_stamp
    from macro_risk_monitor.schemas import CitationCheck, Decision, Report

    risk = load_risk(THESES / "us_long_end_yield.yaml")
    kwargs = dict(
        risk=risk,
        verdicts=[],
        decision=Decision(rule="r", action="no_signal", summary="s"),
        llm_analysis_md="",
        citation_check=CitationCheck(passed=True, grounded_count=0),
        generated_at=datetime(2026, 7, 3, 12, 0),
        llm_model="skipped",
    )
    live = Report(**kwargs)
    assert report_stamp(live) == live.generated_at
    replay = Report(**kwargs, as_of=date(2026, 1, 15))
    assert report_stamp(replay) == datetime(2026, 1, 15, 0, 0)
