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
