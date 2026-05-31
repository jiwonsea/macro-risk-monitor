"""Probe unit tests — fake sources, no network.

probe() resolves through registry.get_source, so tests patch the get_source
*re-export on the probe module* (probe.get_source), mirroring the orchestrator
monkeypatch gotcha documented in CLAUDE.md.
"""

from __future__ import annotations

from datetime import date

from macro_risk_monitor.schemas import Reading, SourceKind
from macro_risk_monitor.sources import probe as probe_mod
from macro_risk_monitor.sources.base import FetchError, SourceUnavailable


class _FakeSource:
    def __init__(self, reading: Reading | None = None, exc: Exception | None = None):
        self._reading = reading
        self._exc = exc

    def fetch(self, trigger, as_of=None):
        if self._exc is not None:
            raise self._exc
        return self._reading


def _patch_source(monkeypatch, **kw) -> _FakeSource:
    fake = _FakeSource(**kw)
    monkeypatch.setattr(probe_mod, "get_source", lambda kind, thesis_name=None: fake)
    return fake


def test_probe_ok(monkeypatch):
    _patch_source(
        monkeypatch,
        reading=Reading(
            trigger_id="__probe__",
            value=4.62,
            as_of=date(2026, 5, 15),
            raw={"fred_units": "Percent"},
        ),
    )
    r = probe_mod.probe(SourceKind.FRED, "DGS10")
    assert r.ok
    assert r.latest_value == 4.62
    assert r.units == "Percent"
    assert r.error_kind is None
    assert not r.replaceable


def test_probe_not_found_is_replaceable(monkeypatch):
    _patch_source(monkeypatch, exc=FetchError("FRED 400: series does not exist"))
    r = probe_mod.probe(SourceKind.FRED, "NOPE")
    assert not r.ok
    assert r.error_kind == "not_found"
    assert r.replaceable


def test_probe_network_not_replaceable(monkeypatch):
    _patch_source(
        monkeypatch,
        exc=FetchError("yfinance error for X: Max retries exceeded (SSL)"),
    )
    r = probe_mod.probe(SourceKind.YFINANCE, "X")
    assert not r.ok
    assert r.error_kind == "network"
    assert not r.replaceable


def test_probe_unavailable_not_replaceable(monkeypatch):
    _patch_source(monkeypatch, exc=SourceUnavailable("FRED_API_KEY not configured"))
    r = probe_mod.probe(SourceKind.FRED, "DGS10")
    assert r.error_kind == "unavailable"
    assert not r.replaceable


def test_probe_empty_value_is_not_found(monkeypatch):
    _patch_source(monkeypatch, reading=Reading(trigger_id="__probe__", value=None))
    r = probe_mod.probe(SourceKind.FRED, "DGS10")
    assert not r.ok
    assert r.error_kind == "not_found"


class _SearchResp:
    ok = True
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_search_fred_series(monkeypatch):
    payload = {
        "seriess": [
            {"id": "DGS30", "title": "30Y", "units_short": "Percent", "frequency_short": "D", "popularity": 80},
            {"id": "DGS10", "title": "10Y", "units": "Percent", "popularity": 90},
            {"title": "no id, skipped"},
        ]
    }
    monkeypatch.setattr(probe_mod.cfg, "FRED_API_KEY", "key")
    monkeypatch.setattr(probe_mod.requests, "get", lambda url, params, timeout: _SearchResp(payload))
    out = probe_mod.search_fred_series("treasury yield")
    assert [c.series for c in out] == ["DGS30", "DGS10"]
    assert out[0].units == "Percent"


def test_search_fred_series_no_key(monkeypatch):
    monkeypatch.setattr(probe_mod.cfg, "FRED_API_KEY", None)
    assert probe_mod.search_fred_series("anything") == []
