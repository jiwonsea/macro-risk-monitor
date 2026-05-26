"""Rule-of-three decision aggregation.

From the user's 5/18 dialog:
    - RED in 3 categories  -> defensive_position
    - RED in 2 categories  -> hedge_increase
    - RED in 1 category    -> monitor
    - otherwise            -> no_signal (but yellow categories surfaced)
"""

from __future__ import annotations

from ..schemas import Category, Decision, Status, Trigger, Verdict


def apply_rule_of_three(
    triggers: list[Trigger], verdicts: list[Verdict]
) -> Decision:
    by_id = {t.id: t for t in triggers}
    red_categories: set[Category] = set()
    yellow_categories: set[Category] = set()
    for v in verdicts:
        trig = by_id.get(v.trigger_id)
        if trig is None:
            continue
        if v.status is Status.RED:
            red_categories.add(trig.category)
        elif v.status is Status.YELLOW:
            yellow_categories.add(trig.category)

    n_red = len(red_categories)
    if n_red >= 3:
        action = "defensive_position"
        summary = "세 카테고리(leading/coincident/lagging) 모두 RED — 방어 포지션 전환 시점."
    elif n_red == 2:
        action = "hedge_increase"
        summary = "두 카테고리 RED — 헤지 비중 확대 검토."
    elif n_red == 1:
        action = "monitor"
        summary = "한 카테고리 RED — 추가 모니터링 강화."
    else:
        action = "no_signal"
        summary = "RED 카테고리 없음."
        if yellow_categories:
            summary += f" YELLOW 카테고리: {sorted(c.value for c in yellow_categories)}."

    return Decision(
        rule="rule_of_three",
        action=action,
        summary=summary,
        red_categories=sorted(red_categories, key=lambda c: c.value),
        yellow_categories=sorted(yellow_categories, key=lambda c: c.value),
    )
