from pathlib import Path

import pytest

from macro_risk_monitor.engine.hypothesis import load_risk
from macro_risk_monitor.schemas import SourceKind

THESES = Path(__file__).resolve().parents[2] / "theses"


@pytest.mark.parametrize(
    "fname",
    ["ai_circular_revenue.yaml", "_401k_pe_distribution.yaml", "us_long_end_yield.yaml"],
)
def test_load_shipped_theses(fname):
    risk = load_risk(THESES / fname)
    assert risk.name
    assert risk.title
    assert risk.triggers
    categories = {t.category for t in risk.triggers}
    # require at least two categories present for a meaningful rule_of_three
    assert len(categories) >= 2


def test_us_long_end_yield_uses_free_sources():
    risk = load_risk(THESES / "us_long_end_yield.yaml")
    sources = {t.source for t in risk.triggers}
    assert SourceKind.FRED in sources or SourceKind.YFINANCE in sources


def test_ai_circular_revenue_wires_news_rss():
    """news_rss is exercised by a real thesis, not dead code."""
    risk = load_risk(THESES / "ai_circular_revenue.yaml")
    news = [t for t in risk.triggers if t.source is SourceKind.NEWS_RSS]
    assert len(news) == 1
    trig = news[0]
    assert trig.series, "news_rss trigger needs a keyword spec in 'series'"
    assert trig.category.value == "leading"


def test_duplicate_trigger_ids_rejected(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        """
name: bad
title: dup
hypothesis: |
  duplicates
triggers:
  - id: a
    category: leading
    source: manual_override
    series: a
    threshold: { red: ">= 1" }
  - id: a
    category: lagging
    source: manual_override
    series: a
    threshold: { red: ">= 1" }
""",
        encoding="utf-8",
    )
    with pytest.raises(Exception):
        load_risk(bad)
