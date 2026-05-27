from datetime import date

from macro_risk_monitor.output.charts import render_trigger_bar
from macro_risk_monitor.schemas import (
    Category,
    Reading,
    SourceKind,
    Status,
    Threshold,
    Trigger,
    Verdict,
)


def _trigger(tid: str) -> Trigger:
    return Trigger(
        id=tid,
        category=Category.LEADING,
        source=SourceKind.MANUAL_OVERRIDE,
        series=tid,
        unit="bps",
        threshold=Threshold(red=">= 150", yellow=">= 120", green="< 100"),
    )


def test_render_trigger_bar_has_subplot_count():
    triggers = {"a": _trigger("a"), "b": _trigger("b")}
    verdicts = [
        Verdict(
            trigger_id="a",
            status=Status.GREEN,
            reading=Reading(trigger_id="a", value=74, as_of=date(2026, 5, 26)),
        ),
        Verdict(
            trigger_id="b",
            status=Status.RED,
            reading=Reading(trigger_id="b", value=160, as_of=date(2026, 5, 26)),
        ),
    ]

    html = render_trigger_bar(verdicts, triggers)

    assert html is not None
    assert 'data-subplots="2"' in html
    assert "data:image/png;base64," in html
