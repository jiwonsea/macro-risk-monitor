"""Backtest sweep: as_of-aware fake sources, honesty for non-backtestable."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from macro_risk_monitor.pipeline import backtest as bt
from macro_risk_monitor.schemas import (
    Category,
    Reading,
    Risk,
    SourceKind,
    Threshold,
    Trigger,
)


def _risk() -> Risk:
    return Risk(
        name="bt_sample",
        title="Backtest sample",
        hypothesis="h",
        triggers=[
            Trigger(
                id="auto_t",
                category=Category.LEADING,
                source=SourceKind.FRED,
                series="FAKE",
                threshold=Threshold(red=">= 5", yellow=">= 3"),
            ),
            Trigger(
                id="manual_t",
                category=Category.COINCIDENT,
                source=SourceKind.MANUAL_OVERRIDE,
                series="k",
                threshold=Threshold(red=">= 1"),
            ),
        ],
    )


class _FakeSource:
    """Value grows over time: 1.0 at 2026-01-01 + 1.0/week."""

    def fetch(self, trigger, as_of=None):
        days = (as_of - date(2026, 1, 1)).days
        return Reading(
            trigger_id=trigger.id, value=1.0 + days / 7.0, as_of=as_of
        )


@pytest.fixture
def _patched(monkeypatch):
    monkeypatch.setattr(bt, "get_source", lambda kind, thesis_name=None: _FakeSource())


def test_backtest_sweeps_and_crosses_thresholds(_patched):
    rows = bt.run_backtest(_risk(), date(2026, 1, 1), date(2026, 2, 26), step_days=7)
    assert len(rows) == 9
    # value 1.0 -> ... crosses yellow (>=3) then red (>=5)
    statuses = [r.statuses["auto_t"] for r in rows]
    assert statuses[0] == "green"
    assert "yellow" in statuses
    assert statuses[-1] == "red"
    assert rows[0].values["auto_t"] == 1.0


def test_backtest_manual_override_stays_unknown(_patched):
    """manual_override cannot reproduce history — must be UNKNOWN, never
    today's value dressed up as a historical reading."""
    rows = bt.run_backtest(_risk(), date(2026, 1, 1), date(2026, 1, 1))
    assert rows[0].statuses["manual_t"] == "unknown"
    assert rows[0].values["manual_t"] is None


def test_backtest_csv_and_summary(tmp_path: Path, _patched):
    risk = _risk()
    rows = bt.run_backtest(risk, date(2026, 1, 1), date(2026, 2, 26), step_days=7)
    out = bt.write_csv(rows, risk, tmp_path / "bt.csv")
    text = out.read_text(encoding="utf-8")
    assert text.splitlines()[0] == (
        "as_of,action,auto_t_status,auto_t_value,manual_t_status,manual_t_value"
    )
    assert len(text.splitlines()) == 10  # header + 9 rows

    summary = bt.summarize(rows)
    assert "action -> monitor" in summary  # red on auto_t -> 1 red category


def test_backtest_rejects_bad_range():
    with pytest.raises(ValueError):
        bt.run_backtest(_risk(), date(2026, 2, 1), date(2026, 1, 1))
    with pytest.raises(ValueError):
        bt.run_backtest(_risk(), date(2026, 1, 1), date(2026, 2, 1), step_days=0)
