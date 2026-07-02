"""Dashboard data-prep functions (no streamlit dependency needed)."""

from __future__ import annotations

import json
from pathlib import Path

from macro_risk_monitor.engine.hypothesis import load_risk
from macro_risk_monitor.schemas import Status
from macro_risk_monitor.ui.dashboard import (
    latest_report,
    list_theses,
    load_state,
    status_counts,
    trigger_rows,
)

THESES = Path(__file__).resolve().parents[2] / "theses"


def test_list_theses_finds_bundled_yaml():
    found = [p.stem for p in list_theses(THESES)]
    assert "ai_circular_revenue" in found
    assert "us_long_end_yield" in found


def test_load_state_missing_returns_empty(tmp_path: Path):
    state = load_state("nope", state_dir=tmp_path)
    assert state == {"generated_at": None, "verdicts": {}}


def test_load_state_parses_snapshot(tmp_path: Path):
    (tmp_path / "foo.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-02T13:00:00+00:00",
                "verdicts": {"a": "red", "b": "bogus-status"},
            }
        ),
        encoding="utf-8",
    )
    state = load_state("foo", state_dir=tmp_path)
    assert state["verdicts"]["a"] is Status.RED
    assert state["verdicts"]["b"] is Status.UNKNOWN  # unknown value degrades


def test_trigger_rows_and_counts():
    risk = load_risk(THESES / "us_long_end_yield.yaml")
    verdicts = {risk.triggers[0].id: Status.RED}
    rows = trigger_rows(risk, verdicts)
    assert len(rows) == len(risk.triggers)
    assert rows[0]["status"].endswith("red")
    # triggers without a snapshot entry render as unknown
    assert all("unknown" in r["status"] for r in rows[1:])
    counts = status_counts(verdicts)
    assert counts["red"] == 1


def test_latest_report_picks_newest(tmp_path: Path):
    (tmp_path / "2026-07-01-foo.html").write_text("old", encoding="utf-8")
    (tmp_path / "2026-07-02-foo.html").write_text("new", encoding="utf-8")
    (tmp_path / "2026-07-02-bar.html").write_text("other", encoding="utf-8")
    p = latest_report("foo", html_dir=tmp_path)
    assert p is not None and p.name == "2026-07-02-foo.html"
    assert latest_report("baz", html_dir=tmp_path) is None
