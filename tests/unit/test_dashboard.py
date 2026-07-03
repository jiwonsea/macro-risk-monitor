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


def test_history_roundtrip_and_frame(tmp_path: Path):
    from datetime import date as date_cls

    from macro_risk_monitor.engine.thesis_state import append_history, load_history
    from macro_risk_monitor.schemas import Reading, Verdict
    from macro_risk_monitor.ui.dashboard import history_frame, status_timeline_rows

    def _verdict(tid: str, status: Status, value=None):
        reading = None
        if value is not None:
            reading = Reading(trigger_id=tid, value=value, as_of=date_cls(2026, 7, 1))
        return Verdict(trigger_id=tid, status=status, reading=reading)

    append_history(tmp_path, "foo", [_verdict("a", Status.GREEN, 1.0),
                                     _verdict("b", Status.UNKNOWN)])
    append_history(tmp_path, "foo", [_verdict("a", Status.RED, 9.0),
                                     _verdict("b", Status.UNKNOWN)])

    entries = load_history(tmp_path, "foo")
    assert len(entries) == 2
    assert entries[0]["verdicts"]["a"] == {"status": "green", "value": 1.0}
    assert entries[1]["verdicts"]["a"]["status"] == "red"
    assert entries[0]["verdicts"]["b"]["value"] is None

    frame = history_frame("foo", state_dir=tmp_path)
    assert frame["values"]["a"] == [1.0, 9.0]
    assert frame["statuses"]["b"] == ["unknown", "unknown"]

    rows = status_timeline_rows(frame)
    row_a = next(r for r in rows if r["trigger"] == "a")
    assert row_a["timeline"] == "🟢🔴"


def test_load_history_skips_corrupt_lines(tmp_path: Path):
    from macro_risk_monitor.engine.thesis_state import load_history

    p = tmp_path / "foo_history.jsonl"
    p.write_text(
        '{"generated_at": "t1", "verdicts": {"a": {"status": "red", "value": 1}}}\n'
        "not-json\n"
        '{"generated_at": "t2", "verdicts": {"a": {"status": "green", "value": 2}}}\n',
        encoding="utf-8",
    )
    entries = load_history(tmp_path, "foo")
    assert [e["generated_at"] for e in entries] == ["t1", "t2"]
    assert load_history(tmp_path, "foo", limit=1)[0]["generated_at"] == "t2"


def test_backtest_frame_missing_returns_none(tmp_path: Path):
    from macro_risk_monitor.ui.dashboard import backtest_frame

    assert backtest_frame("nope", backtest_dir=tmp_path) is None


def test_backtest_frame_parses_csv_and_transitions(tmp_path: Path):
    from macro_risk_monitor.ui.dashboard import action_transitions, backtest_frame

    (tmp_path / "foo.csv").write_text(
        "as_of,action,a_status,a_value\n"
        "2026-01-01,no_signal,green,1.0\n"
        "2026-01-08,monitor,yellow,2.0\n"
        "2026-01-15,bogus_action,red,3.0\n"  # unknown action -> skipped
        "2026-01-22,monitor,yellow,2.5\n"
        "2026-01-29,defensive_position,red,4.0\n",
        encoding="utf-8",
    )
    frame = backtest_frame("foo", backtest_dir=tmp_path)
    assert frame is not None
    assert frame["dates"] == ["2026-01-01", "2026-01-08", "2026-01-22", "2026-01-29"]
    assert frame["levels"] == [0, 1, 1, 3]

    trans = action_transitions(frame)
    assert [(t["as_of"], t["action"]) for t in trans] == [
        ("2026-01-01", "no_signal"),
        ("2026-01-08", "monitor"),
        ("2026-01-29", "defensive_position"),
    ]


def test_backtest_frame_all_rows_invalid_returns_none(tmp_path: Path):
    from macro_risk_monitor.ui.dashboard import backtest_frame

    (tmp_path / "foo.csv").write_text(
        "as_of,action\n,\n2026-01-01,garbage\n", encoding="utf-8"
    )
    assert backtest_frame("foo", backtest_dir=tmp_path) is None
