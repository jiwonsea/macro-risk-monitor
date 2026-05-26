from datetime import date, datetime
from pathlib import Path

from macro_risk_monitor.output.html import render_report
from macro_risk_monitor.schemas import (
    Category,
    CitationCheck,
    Decision,
    Reading,
    Report,
    Risk,
    SourceKind,
    Status,
    Threshold,
    Trigger,
    Verdict,
)


def _sample_report() -> Report:
    triggers = [
        Trigger(
            id="ust_10y",
            category=Category.LEADING,
            source=SourceKind.FRED,
            series="DGS10",
            unit="percent",
            description="US 10Y treasury yield",
            threshold=Threshold(red=">= 4.5", yellow=">= 4.2", green="< 4.0"),
        ),
        Trigger(
            id="vix",
            category=Category.LAGGING,
            source=SourceKind.YFINANCE,
            series="^VIX",
            description="CBOE VIX",
            threshold=Threshold(red=">= 25", yellow=">= 20", green="< 18"),
        ),
    ]
    risk = Risk(
        name="us_long_end_yield",
        title="US 장기금리 spillover",
        hypothesis="장기금리 상승이 spillover를 일으킨다",
        triggers=triggers,
        critical_windows=[date(2026, 6, 12)],
    )
    verdicts = [
        Verdict(
            trigger_id="ust_10y",
            status=Status.RED,
            reading=Reading(
                trigger_id="ust_10y", value=4.62, as_of=date(2026, 5, 15),
                source_url="https://fred.stlouisfed.org/series/DGS10",
            ),
            rationale="value=4.62 matches red tier '>= 4.5'",
        ),
        Verdict(
            trigger_id="vix",
            status=Status.GREEN,
            reading=Reading(trigger_id="vix", value=14.2, as_of=date(2026, 5, 15)),
            rationale="value=14.2 below tiers",
        ),
    ]
    decision = Decision(
        rule="rule_of_three",
        action="monitor",
        summary="한 카테고리 RED",
        red_categories=[Category.LEADING],
    )
    return Report(
        risk=risk,
        verdicts=verdicts,
        decision=decision,
        llm_analysis_md="## 1. 사실관계\n10년물 4.62%.\n",
        citation_check=CitationCheck(passed=True, grounded_count=1),
        generated_at=datetime(2026, 5, 26, 12, 0, 0),
        llm_model="stub",
    )


def test_render_contains_status_classes(tmp_path: Path):
    out = tmp_path / "report.html"
    render_report(_sample_report(), out)
    html = out.read_text(encoding="utf-8")
    assert "status-red" in html
    assert "status-green" in html
    assert "ust_10y" in html
    assert "monitor" in html.lower()


def test_render_shows_state_diff(tmp_path: Path):
    out = tmp_path / "report.html"
    diff = [("ust_10y", Status.YELLOW, Status.RED)]
    render_report(_sample_report(), out, state_diff=diff)
    html = out.read_text(encoding="utf-8")
    assert "변경 사항" in html
    assert "ust_10y" in html
