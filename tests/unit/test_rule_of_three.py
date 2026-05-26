from macro_risk_monitor.engine.rule_of_three import apply_rule_of_three
from macro_risk_monitor.schemas import (
    Category,
    SourceKind,
    Status,
    Threshold,
    Trigger,
    Verdict,
)


def _trig(tid: str, cat: Category) -> Trigger:
    return Trigger(
        id=tid,
        category=cat,
        source=SourceKind.MANUAL_OVERRIDE,
        series=tid,
        threshold=Threshold(red=">= 1"),
    )


def _v(tid: str, status: Status) -> Verdict:
    return Verdict(trigger_id=tid, status=status)


def test_three_red_categories_triggers_defensive():
    triggers = [
        _trig("a", Category.LEADING),
        _trig("b", Category.COINCIDENT),
        _trig("c", Category.LAGGING),
    ]
    verdicts = [_v("a", Status.RED), _v("b", Status.RED), _v("c", Status.RED)]
    d = apply_rule_of_three(triggers, verdicts)
    assert d.action == "defensive_position"
    assert len(d.red_categories) == 3


def test_two_red_categories_hedge():
    triggers = [_trig("a", Category.LEADING), _trig("b", Category.COINCIDENT)]
    verdicts = [_v("a", Status.RED), _v("b", Status.RED)]
    d = apply_rule_of_three(triggers, verdicts)
    assert d.action == "hedge_increase"


def test_one_red_category_monitor():
    triggers = [_trig("a", Category.LEADING), _trig("b", Category.COINCIDENT)]
    verdicts = [_v("a", Status.RED), _v("b", Status.GREEN)]
    d = apply_rule_of_three(triggers, verdicts)
    assert d.action == "monitor"


def test_no_red_no_signal_with_yellow_listed():
    triggers = [_trig("a", Category.LEADING), _trig("b", Category.LAGGING)]
    verdicts = [_v("a", Status.YELLOW), _v("b", Status.GREEN)]
    d = apply_rule_of_three(triggers, verdicts)
    assert d.action == "no_signal"
    assert Category.LEADING in d.yellow_categories


def test_two_red_same_category_counts_once():
    triggers = [_trig("a", Category.LEADING), _trig("b", Category.LEADING)]
    verdicts = [_v("a", Status.RED), _v("b", Status.RED)]
    d = apply_rule_of_three(triggers, verdicts)
    assert d.action == "monitor"  # only one distinct category
