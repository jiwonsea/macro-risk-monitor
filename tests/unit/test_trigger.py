"""Threshold evaluation: numeric ops, ranges, qualitative fallthrough."""

from __future__ import annotations

from datetime import date

import pytest

from macro_risk_monitor.engine.trigger import evaluate
from macro_risk_monitor.schemas import (
    Category,
    Reading,
    SourceKind,
    Status,
    Threshold,
    Trigger,
)


def _trig(red: str | None = None, yellow: str | None = None, green: str | None = None) -> Trigger:
    return Trigger(
        id="t",
        category=Category.LEADING,
        source=SourceKind.MANUAL_OVERRIDE,
        series="x",
        threshold=Threshold(red=red, yellow=yellow, green=green),
    )


def _read(v):
    return Reading(trigger_id="t", value=v, as_of=date(2026, 5, 26))


@pytest.mark.parametrize(
    "value,red,expected",
    [
        (5.0, "> 4.5", Status.RED),
        (4.5, ">= 4.5", Status.RED),
        (4.4, ">= 4.5", Status.GREEN),
        (-12, "<= -10", Status.RED),
        (-9, "<= -10", Status.GREEN),
    ],
)
def test_numeric_red_threshold(value, red, expected):
    trig = _trig(red=red, yellow=None, green=None)
    v = evaluate(trig, _read(value))
    assert v.status is expected


def test_three_tier_yellow_intermediate():
    trig = _trig(red=">= 5", yellow=">= 4.5", green="< 4")
    assert evaluate(trig, _read(5.1)).status is Status.RED
    assert evaluate(trig, _read(4.7)).status is Status.YELLOW
    assert evaluate(trig, _read(3.9)).status is Status.GREEN


def test_range_threshold():
    trig = _trig(yellow="100~130")
    assert evaluate(trig, _read(120)).status is Status.YELLOW
    assert evaluate(trig, _read(99)).status is Status.GREEN
    assert evaluate(trig, _read(150)).status is Status.GREEN


def test_unknown_when_reading_missing():
    trig = _trig(red="> 4.5")
    assert evaluate(trig, None).status is Status.UNKNOWN
    assert evaluate(trig, Reading(trigger_id="t", value=None)).status is Status.UNKNOWN


def test_qualitative_threshold_returns_unknown():
    trig = _trig(red="2개사 동시 'rationalize'")
    v = evaluate(trig, _read("rationalize"))
    assert v.status is Status.UNKNOWN
    assert "qualitative" in (v.rationale or "")


def test_implicit_green_below_all_tiers():
    trig = _trig(red=">= 5", yellow=">= 4.5")
    v = evaluate(trig, _read(3.0))
    assert v.status is Status.GREEN


def test_fred_percent_converts_to_bps_for_threshold_comparison():
    trig = _trig(red=">= 150", yellow=">= 120")
    trig.unit = "bps"
    reading = Reading(
        trigger_id="t",
        value=0.74,
        as_of=date(2026, 5, 26),
        raw={"fred_units": "percent"},
    )

    v = evaluate(trig, reading)

    assert v.status is Status.GREEN
    assert reading.value == 0.74
    assert reading.display_value == 74
    assert "value=74" in (v.rationale or "")


def test_fred_percent_to_bps_can_cross_small_threshold():
    trig = _trig(red=">= 0.5")
    trig.unit = "bps"
    reading = Reading(
        trigger_id="t",
        value=0.74,
        as_of=date(2026, 5, 26),
        raw={"fred_units": "percent"},
    )

    v = evaluate(trig, reading)

    assert v.status is Status.RED


def test_nan_reading_returns_unknown_not_green():
    # Regression: NaN compares False on every tier and used to fall through
    # to the implicit-GREEN branch (false all-clear).
    trig = _trig(red=">= 4.5", yellow=">= 4.0")
    v = evaluate(trig, _read(float("nan")))
    assert v.status is Status.UNKNOWN
    assert "NaN" in v.rationale
