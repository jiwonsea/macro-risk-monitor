"""E2E: news_rss flows through the real registry + orchestrator dispatch.

Unlike test_end_to_end.py (which swaps the whole registry for a fake source),
this test keeps the *real* `get_source` so it exercises the registry ->
NewsRssSource wiring for the `circular_revenue_press_attention` trigger that
lives in theses/ai_circular_revenue.yaml. Only `requests.get` is stubbed, so no
network is touched; every other trigger in the thesis degrades to UNKNOWN
(manual_override placeholders / earnings_transcript_nlp not implemented).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path

import pytest

from macro_risk_monitor.engine.hypothesis import load_risk
from macro_risk_monitor.pipeline.orchestrator import run_pipeline
from macro_risk_monitor.schemas import SourceKind, Status
from macro_risk_monitor.sources.registry import get_source

THESES = Path(__file__).resolve().parents[2] / "theses"


def _rss_with_recent_items(n_match: int) -> str:
    """RSS feed with `n_match` items that hit the circular-revenue keywords,
    dated two days ago so they always fall inside the 30-day lookback window."""
    recent = format_datetime(datetime.now(timezone.utc) - timedelta(days=2))
    items = "".join(
        f"""
  <item>
    <title>Analysts flag circular revenue at AI vendor #{i}</title>
    <description>Concerns over vendor financing and round-trip deal structures</description>
    <pubDate>{recent}</pubDate>
    <link>http://example.com/{i}</link>
  </item>"""
        for i in range(n_match)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f"<rss version=\"2.0\"><channel><title>Fake Wire</title>{items}</channel></rss>"
    )


@pytest.fixture
def _wire_news_rss(monkeypatch, tmp_path):
    from macro_risk_monitor import config as cfg
    import macro_risk_monitor.sources.news_rss as news_mod

    # Stub the network: every feed returns the same fixture XML (cache miss path).
    feed_xml = _rss_with_recent_items(8)
    monkeypatch.setattr(
        news_mod.requests,
        "get",
        lambda *a, **kw: type("R", (), {"text": feed_xml, "ok": True, "status_code": 200})(),
    )

    # Point the registry at a single feed + a throwaway cache dir.
    monkeypatch.setattr(cfg, "NEWS_RSS_FEEDS", ["http://feed.example/rss"])
    monkeypatch.setattr(cfg, "NEWS_RSS_CACHE_DIR", tmp_path / "news_cache")
    monkeypatch.setattr(cfg, "NEWS_RSS_LOOKBACK_DAYS", 30)

    # Keep pipeline writes inside tmp.
    monkeypatch.setattr(cfg, "REPORTS_HTML_DIR", tmp_path / "html")
    monkeypatch.setattr(cfg, "REPORTS_RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(cfg, "CACHE_DIR", tmp_path / "cache")
    for sub in ("html", "raw", "cache", "news_cache"):
        (tmp_path / sub).mkdir(exist_ok=True)

    get_source.cache_clear()  # rebuild sources from the patched cfg
    yield
    get_source.cache_clear()  # don't leak patched instances into other tests


def test_news_rss_trigger_evaluated_via_pipeline(_wire_news_rss, tmp_path):
    risk = load_risk(THESES / "ai_circular_revenue.yaml")
    out = tmp_path / "report.html"

    report = run_pipeline(risk, out_html=out, skip_llm=True)

    assert out.exists()
    # Every trigger produces a verdict, including the news_rss one.
    assert len(report.verdicts) == len(risk.triggers)

    news_trigger = next(
        t for t in risk.triggers if t.source is SourceKind.NEWS_RSS
    )
    verdict = next(v for v in report.verdicts if v.trigger_id == news_trigger.id)

    # 8 matching items in-window -> count 8 -> red (>= 8).
    assert verdict.reading is not None
    assert verdict.reading.value == 8.0
    assert verdict.reading.as_of == (date.today() - timedelta(days=2))
    assert verdict.status is Status.RED
