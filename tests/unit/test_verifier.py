from datetime import date

from macro_risk_monitor.ai.verifier import verify_citations
from macro_risk_monitor.schemas import (
    Category,
    Reading,
    Risk,
    SourceKind,
    Status,
    Threshold,
    Trigger,
    Verdict,
)


def _risk_and_verdicts() -> tuple[Risk, list[Verdict]]:
    trig = Trigger(
        id="ust_10y",
        category=Category.LEADING,
        source=SourceKind.FRED,
        series="DGS10",
        threshold=Threshold(red=">= 4.5", yellow=">= 4.2", green="< 4.0"),
    )
    risk = Risk(
        name="x", title="x", hypothesis="...", triggers=[trig], critical_windows=[date(2026, 6, 1)]
    )
    verdicts = [
        Verdict(
            trigger_id="ust_10y",
            status=Status.RED,
            reading=Reading(trigger_id="ust_10y", value=4.62, as_of=date(2026, 5, 15)),
            rationale="ok",
        )
    ]
    return risk, verdicts


def test_passes_when_only_grounded_numbers_quoted():
    risk, verdicts = _risk_and_verdicts()
    md = "10년물이 4.62%까지 올랐고 임계는 4.5%다."
    check = verify_citations(md, risk, verdicts)
    assert check.passed
    assert check.grounded_count >= 2


def test_flags_ungrounded_number():
    risk, verdicts = _risk_and_verdicts()
    md = "10년물이 7.31%로 폭등했다."  # 7.31 is not grounded
    check = verify_citations(md, risk, verdicts)
    assert not check.passed
    assert any("7.31" in u for u in check.ungrounded)


def test_year_tokens_ignored():
    risk, verdicts = _risk_and_verdicts()
    md = "2025년 이래 최고. 임계 4.5% 돌파."
    check = verify_citations(md, risk, verdicts)
    assert check.passed


def test_code_blocks_excluded():
    risk, verdicts = _risk_and_verdicts()
    md = "값은 4.62%다.\n\n```\n<garbage>1234.5</garbage>\n```\n"
    check = verify_citations(md, risk, verdicts)
    assert check.passed
