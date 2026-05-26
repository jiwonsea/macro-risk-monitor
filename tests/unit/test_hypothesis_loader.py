from pathlib import Path

import pytest

from macro_risk_monitor.engine.hypothesis import load_risk
from macro_risk_monitor.schemas import Category, SourceKind

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
