from datetime import date

from macro_risk_monitor.schemas import Category, Risk, SourceKind, Threshold, Trigger


def _trigger() -> Trigger:
    return Trigger(
        id="t",
        category=Category.LEADING,
        source=SourceKind.MANUAL_OVERRIDE,
        series="x",
        threshold=Threshold(red=">= 1"),
    )


def test_critical_windows_accept_legacy_date_list():
    risk = Risk(
        name="x",
        title="x",
        hypothesis="x",
        triggers=[_trigger()],
        critical_windows=[date(2026, 6, 1)],
    )
    assert risk.critical_windows[0].date == date(2026, 6, 1)
    assert risk.critical_windows[0].event == "(unspecified)"


def test_critical_windows_accept_event_schema():
    risk = Risk(
        name="x",
        title="x",
        hypothesis="x",
        triggers=[_trigger()],
        critical_windows=[
            {
                "date": "2026-06-12",
                "event": "FOMC",
                "rationale": "policy guidance",
            }
        ],
    )
    window = risk.critical_windows[0]
    assert window.date == date(2026, 6, 12)
    assert window.event == "FOMC"
    assert window.rationale == "policy guidance"
