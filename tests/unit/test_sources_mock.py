"""Source unit tests using fake API responses or fixture YAML."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from macro_risk_monitor.schemas import (
    Category,
    SourceKind,
    Threshold,
    Trigger,
)
from macro_risk_monitor.sources.base import FetchError, SourceUnavailable
from macro_risk_monitor.sources.fred import FredSource
from macro_risk_monitor.sources.manual_override import ManualOverrideSource
from macro_risk_monitor.sources.news_rss import NewsRssSource
from macro_risk_monitor.sources.registry import get_source


def _t(source: SourceKind, series: str) -> Trigger:
    return Trigger(
        id="t",
        category=Category.LEADING,
        source=source,
        series=series,
        threshold=Threshold(red=">= 1"),
    )


def test_fred_uses_cache(tmp_path: Path, monkeypatch):
    cache_dir = tmp_path / "fred"
    cache_dir.mkdir()
    cache_path = cache_dir / "DGS10_2026-05-26.json"
    cache_path.write_text(
        json.dumps(
            {
                "observations": [
                    {"date": "2026-05-15", "value": "4.62"},
                    {"date": "2026-05-14", "value": "."},
                ]
            }
        ),
        encoding="utf-8",
    )
    src = FredSource(api_key="key", cache_dir=cache_dir, cache_ttl_hours=24)
    # Force cache hit by mocking requests.get to fail loudly
    import macro_risk_monitor.sources.fred as fred_mod

    def boom(*a, **kw):
        raise AssertionError("should not hit network")

    monkeypatch.setattr(fred_mod.requests, "get", boom)
    reading = src.fetch(_t(SourceKind.FRED, "DGS10"), as_of=date(2026, 5, 26))
    assert reading.value == 4.62
    assert reading.as_of == date(2026, 5, 15)


def test_fred_fetches_series_units(tmp_path: Path, monkeypatch):
    import macro_risk_monitor.sources.fred as fred_mod

    fred_mod._SERIES_UNITS_CACHE.clear()

    class Resp:
        ok = True
        status_code = 200
        text = ""

        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    def fake_get(url, params, timeout):
        if url == fred_mod.FRED_API_URL:
            return Resp({"observations": [{"date": "2026-05-15", "value": "0.74"}]})
        if url == fred_mod.FRED_SERIES_URL:
            return Resp({"seriess": [{"units_short": "percent"}]})
        raise AssertionError(url)

    monkeypatch.setattr(fred_mod.requests, "get", fake_get)
    src = FredSource(api_key="key", cache_dir=tmp_path, cache_ttl_hours=0)

    reading = src.fetch(_t(SourceKind.FRED, "BAMLC0A0CM"), as_of=date(2026, 5, 26))

    assert reading.value == 0.74
    assert reading.raw["fred_units"] == "percent"


def test_fred_raises_when_no_key(tmp_path: Path):
    src = FredSource(api_key=None, cache_dir=tmp_path)
    with pytest.raises(SourceUnavailable):
        src.fetch(_t(SourceKind.FRED, "DGS10"))


def test_manual_override_reads_yaml(tmp_path: Path):
    p = tmp_path / "manual.yaml"
    p.write_text(
        """
oracle_cds_5y_bps:
  value: 142.5
  as_of: 2026-05-20
  source_url: https://example.com
""",
        encoding="utf-8",
    )
    src = ManualOverrideSource(p)
    trig = _t(SourceKind.MANUAL_OVERRIDE, "oracle_cds_5y_bps")
    reading = src.fetch(trig)
    assert reading.value == 142.5
    assert reading.as_of == date(2026, 5, 20)


def test_manual_override_missing_key(tmp_path: Path):
    p = tmp_path / "manual.yaml"
    p.write_text("other_key: {value: 1, as_of: 2026-01-01}\n", encoding="utf-8")
    src = ManualOverrideSource(p)
    with pytest.raises(FetchError):
        src.fetch(_t(SourceKind.MANUAL_OVERRIDE, "missing_key"))


def test_registry_manual_override_per_thesis(tmp_path: Path, monkeypatch):
    """registry resolves manual_override to data/manual_override/{thesis_name}.yaml."""
    import macro_risk_monitor.sources.registry as registry_mod

    monkeypatch.setattr(registry_mod.cfg, "BASE_DIR", tmp_path)
    get_source.cache_clear()

    thesis_dir = tmp_path / "data" / "manual_override"
    thesis_dir.mkdir(parents=True)
    (thesis_dir / "foo_thesis.yaml").write_text(
        "k1: {value: 42, as_of: 2026-05-26}\n", encoding="utf-8"
    )

    src = get_source(SourceKind.MANUAL_OVERRIDE, thesis_name="foo_thesis")
    assert isinstance(src, ManualOverrideSource)
    assert src.override_path == thesis_dir / "foo_thesis.yaml"
    reading = src.fetch(_t(SourceKind.MANUAL_OVERRIDE, "k1"))
    assert reading.value == 42

    # Different thesis_name -> different instance (separate cache entry)
    (thesis_dir / "bar_thesis.yaml").write_text(
        "k1: {value: 99, as_of: 2026-05-26}\n", encoding="utf-8"
    )
    src2 = get_source(SourceKind.MANUAL_OVERRIDE, thesis_name="bar_thesis")
    assert src2.override_path == thesis_dir / "bar_thesis.yaml"
    assert src2 is not src

    get_source.cache_clear()


def test_registry_manual_override_requires_thesis_name():
    get_source.cache_clear()
    with pytest.raises(SourceUnavailable):
        get_source(SourceKind.MANUAL_OVERRIDE)
    get_source.cache_clear()


# ---------------------------------------------------------------------------
# news_rss
# ---------------------------------------------------------------------------
_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Fake Markets</title>
  <item>
    <title>NVDA circular revenue concerns mount</title>
    <description>Analysts flag vendor financing risk</description>
    <pubDate>Wed, 20 May 2026 10:00:00 GMT</pubDate>
    <link>http://example.com/1</link>
  </item>
  <item>
    <title>Unrelated weather story</title>
    <description>Sunny in the northeast</description>
    <pubDate>Thu, 21 May 2026 10:00:00 GMT</pubDate>
    <link>http://example.com/2</link>
  </item>
  <item>
    <title>Old circular revenue piece</title>
    <description>From before the window</description>
    <pubDate>Sun, 01 Mar 2026 10:00:00 GMT</pubDate>
    <link>http://example.com/3</link>
  </item>
</channel></rss>"""

_ATOM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Fake Atom Wire</title>
  <entry>
    <title>Round-trip deal scrutiny intensifies</title>
    <summary>Regulators probe round-trip deal structures</summary>
    <updated>2026-05-22T08:00:00Z</updated>
    <link href="http://example.com/a" rel="alternate"/>
  </entry>
</feed>"""


class _RssResp:
    def __init__(self, text: str, ok: bool = True, status_code: int = 200):
        self.text = text
        self.ok = ok
        self.status_code = status_code


def _news_trigger(series: str | None) -> Trigger:
    return Trigger(
        id="news_t",
        category=Category.LEADING,
        source=SourceKind.NEWS_RSS,
        series=series,
        threshold=Threshold(red=">= 1"),
    )


def test_news_rss_counts_keyword_matches(tmp_path: Path, monkeypatch):
    import macro_risk_monitor.sources.news_rss as news_mod

    monkeypatch.setattr(
        news_mod.requests, "get", lambda *a, **kw: _RssResp(_RSS_XML)
    )
    src = NewsRssSource(["http://feed.example/rss"], tmp_path, lookback_days=30)

    reading = src.fetch(
        _news_trigger("circular revenue, vendor financing"),
        as_of=date(2026, 5, 26),
    )

    # Item 1 matches in window; item 2 no match; item 3 matches but is stale.
    assert reading.value == 1.0
    assert reading.as_of == date(2026, 5, 20)
    assert reading.raw["match_count"] == 1
    assert "NVDA circular revenue concerns mount" in reading.raw["matched_titles"]


def test_news_rss_parses_atom(tmp_path: Path, monkeypatch):
    import macro_risk_monitor.sources.news_rss as news_mod

    monkeypatch.setattr(
        news_mod.requests, "get", lambda *a, **kw: _RssResp(_ATOM_XML)
    )
    src = NewsRssSource(["http://feed.example/atom"], tmp_path, lookback_days=30)

    reading = src.fetch(_news_trigger("round-trip deal"), as_of=date(2026, 5, 26))

    assert reading.value == 1.0
    assert reading.as_of == date(2026, 5, 22)


def test_news_rss_uses_cache(tmp_path: Path, monkeypatch):
    import macro_risk_monitor.sources.news_rss as news_mod

    from macro_risk_monitor.sources.news_rss import _slug

    cache_file = tmp_path / f"{_slug('http://feed.example/rss')}_2026-05-26.xml"
    cache_file.write_text(_RSS_XML, encoding="utf-8")

    def boom(*a, **kw):
        raise AssertionError("should not hit network")

    monkeypatch.setattr(news_mod.requests, "get", boom)
    src = NewsRssSource(
        ["http://feed.example/rss"], tmp_path, cache_ttl_hours=24, lookback_days=30
    )
    reading = src.fetch(_news_trigger("circular revenue"), as_of=date(2026, 5, 26))
    assert reading.value == 1.0


def test_news_rss_cache_slug_unique_per_url():
    # Two feeds on the same host must not share a cache file (regression:
    # netloc-only slugs collided and one feed silently overwrote the other).
    from macro_risk_monitor.sources.news_rss import _slug

    a = _slug("https://www.cnbc.com/id/100003114/device/rss/rss.html")
    b = _slug("https://www.cnbc.com/id/19746125/device/rss/rss.html")
    assert a != b
    assert a.startswith("www.cnbc.com_")


def test_news_rss_excludes_items_after_as_of(tmp_path: Path, monkeypatch):
    # A backdated as_of must not count items published after it.
    import macro_risk_monitor.sources.news_rss as news_mod

    monkeypatch.setattr(
        news_mod.requests, "get", lambda *a, **kw: _RssResp(_RSS_XML)
    )
    src = NewsRssSource(["http://feed.example/rss"], tmp_path, lookback_days=30)
    # Item 1 (2026-05-20, matching) is *after* this as_of -> excluded.
    reading = src.fetch(
        _news_trigger("circular revenue, vendor financing"),
        as_of=date(2026, 5, 19),
    )
    assert reading.value == 0.0


def test_news_rss_no_feeds_unavailable(tmp_path: Path):
    src = NewsRssSource([], tmp_path)
    with pytest.raises(SourceUnavailable):
        src.fetch(_news_trigger("anything"))


def test_news_rss_missing_keywords_raises(tmp_path: Path):
    src = NewsRssSource(["http://feed.example/rss"], tmp_path)
    with pytest.raises(FetchError):
        src.fetch(_news_trigger(None))


def test_news_rss_all_feeds_fail_raises(tmp_path: Path, monkeypatch):
    import macro_risk_monitor.sources.news_rss as news_mod

    def boom(*a, **kw):
        raise ConnectionError("dns")

    monkeypatch.setattr(news_mod.requests, "get", boom)
    src = NewsRssSource(
        ["http://a.example/rss", "http://b.example/rss"], tmp_path
    )
    with pytest.raises(FetchError):
        src.fetch(_news_trigger("circular revenue"), as_of=date(2026, 5, 26))


def test_news_rss_zero_matches(tmp_path: Path, monkeypatch):
    import macro_risk_monitor.sources.news_rss as news_mod

    monkeypatch.setattr(
        news_mod.requests, "get", lambda *a, **kw: _RssResp(_RSS_XML)
    )
    src = NewsRssSource(["http://feed.example/rss"], tmp_path, lookback_days=30)
    reading = src.fetch(_news_trigger("nonexistent topic"), as_of=date(2026, 5, 26))
    assert reading.value == 0.0
    assert reading.as_of == date(2026, 5, 26)  # falls back to as_of when no match


def test_registry_news_rss(tmp_path: Path, monkeypatch):
    import macro_risk_monitor.sources.registry as registry_mod

    monkeypatch.setattr(registry_mod.cfg, "NEWS_RSS_FEEDS", ["http://feed.example/rss"])
    monkeypatch.setattr(registry_mod.cfg, "NEWS_RSS_CACHE_DIR", tmp_path)
    monkeypatch.setattr(registry_mod.cfg, "NEWS_RSS_LOOKBACK_DAYS", 14)
    get_source.cache_clear()

    src = get_source(SourceKind.NEWS_RSS)
    assert isinstance(src, NewsRssSource)
    assert src.feeds == ["http://feed.example/rss"]
    assert src.lookback_days == 14

    get_source.cache_clear()


# ---------------------------------------------------------------------------
# yfinance
# ---------------------------------------------------------------------------
def test_yfinance_skips_nan_close_and_nan_volume(tmp_path: Path, monkeypatch):
    """NaN Close rows must be dropped (not leak NaN into Reading.value) and a
    NaN Volume must not crash fetch() after the yf call succeeded."""
    import sys
    import types

    import pandas as pd

    hist = pd.DataFrame(
        {
            "Open": [1.0, 2.0],
            "High": [1.0, 2.0],
            "Low": [1.0, 2.0],
            "Close": [10.5, float("nan")],
            "Volume": [float("nan"), 100.0],
        },
        index=pd.to_datetime(["2026-05-19", "2026-05-20"]),
    )

    class _FakeTicker:
        def __init__(self, series):
            pass

        def history(self, **kwargs):
            return hist

    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = _FakeTicker
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    from macro_risk_monitor.sources.yfinance_source import YFinanceSource

    src = YFinanceSource(tmp_path)
    reading = src.fetch(_t(SourceKind.YFINANCE, "FAKE"), as_of=date(2026, 5, 26))
    assert reading.value == 10.5           # last non-NaN close
    assert reading.as_of == date(2026, 5, 19)
    assert reading.raw["volume"] is None   # NaN volume -> None, no crash


def test_fred_network_error_redacts_api_key(tmp_path: Path, monkeypatch):
    """Network exceptions embed the request URL incl. api_key; the FetchError
    surfaced to logs must have it redacted."""
    import requests as requests_lib

    import macro_risk_monitor.sources.fred as fred_mod

    def boom(*a, **kw):
        raise requests_lib.ConnectionError(
            "HTTPSConnectionPool: /fred/series/observations?series_id=DGS10"
            "&api_key=SECRETKEY123&file_type=json"
        )

    monkeypatch.setattr(fred_mod.requests, "get", boom)
    src = FredSource(api_key="SECRETKEY123", cache_dir=tmp_path, cache_ttl_hours=0)
    with pytest.raises(FetchError) as ei:
        src.fetch(_t(SourceKind.FRED, "DGS10"), as_of=date(2026, 5, 26))
    assert "SECRETKEY123" not in str(ei.value)
    assert "api_key=***" in str(ei.value)
