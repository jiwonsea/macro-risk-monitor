"""data_selector repair-loop tests — parse_risk / probe / codex all mocked.

Exercises the verification + repair logic with no LLM or network by patching
the module-level seams (ds.parse_risk, ds.probe, ds.codex_available,
ds._propose_replacements).
"""

from __future__ import annotations

from datetime import date

from macro_risk_monitor.ai import data_selector as ds
from macro_risk_monitor.schemas import Category, Risk, SourceKind, Threshold, Trigger
from macro_risk_monitor.sources.probe import ProbeResult


def _risk(triggers):
    return Risk(name="test_thesis", title="t", hypothesis="h", triggers=triggers)


def _trig(tid, series, source=SourceKind.FRED, cat=Category.LEADING):
    return Trigger(
        id=tid, category=cat, source=source, series=series, threshold=Threshold(red=">= 1")
    )


def _ok(series, source=SourceKind.FRED):
    return ProbeResult(
        ok=True, series=series, source=source, latest_value=4.5,
        as_of=date(2026, 5, 15), units="Percent",
    )


def _notfound(series, source=SourceKind.FRED):
    return ProbeResult(ok=False, series=series, source=source, error="missing", error_kind="not_found")


def _network(series, source=SourceKind.YFINANCE):
    return ProbeResult(ok=False, series=series, source=source, error="ssl", error_kind="network")


def test_repair_replaces_bad_series(monkeypatch):
    monkeypatch.setattr(ds, "parse_risk", lambda h: _risk([_trig("good", "DGS10"), _trig("bad", "FAKE999")]))
    monkeypatch.setattr(ds, "codex_available", lambda: False)

    def fake_probe(kind, series, thesis_name=None):
        return _notfound(series) if series == "FAKE999" else _ok(series)

    monkeypatch.setattr(ds, "probe", fake_probe)
    monkeypatch.setattr(
        ds, "_propose_replacements",
        lambda h, un: {"bad": {"series": "DGS30", "source": "fred", "rationale": "real 30y"}},
    )

    sel = ds.select_data("hypo", use_codex=False)
    by_id = {t.id: t for t in sel.triggers}
    assert by_id["bad"].series == "DGS30"
    assert by_id["bad"].status == "OK"
    assert not by_id["bad"].needs_manual
    assert "repair r1" in by_id["bad"].rationale


def test_repair_exhausted_downgrades_to_manual(monkeypatch):
    monkeypatch.setattr(ds, "parse_risk", lambda h: _risk([_trig("bad", "FAKE1")]))
    monkeypatch.setattr(ds, "codex_available", lambda: False)
    monkeypatch.setattr(ds, "probe", lambda kind, series, thesis_name=None: _notfound(series))
    monkeypatch.setattr(ds, "_propose_replacements", lambda h, un: {"bad": {"series": "FAKE2", "rationale": "try"}})

    sel = ds.select_data("hypo", use_codex=False, max_repair_rounds=2)
    t = sel.triggers[0]
    assert t.needs_manual
    assert t.source == SourceKind.MANUAL_OVERRIDE.value
    assert t.status == "MANUAL"


def test_network_keeps_series_unverified(monkeypatch):
    monkeypatch.setattr(ds, "parse_risk", lambda h: _risk([_trig("net", "^VIX", source=SourceKind.YFINANCE)]))
    monkeypatch.setattr(ds, "codex_available", lambda: False)
    monkeypatch.setattr(ds, "probe", lambda kind, series, thesis_name=None: _network(series))

    calls = {"n": 0}

    def repl(h, un):
        calls["n"] += 1
        return {}

    monkeypatch.setattr(ds, "_propose_replacements", repl)

    sel = ds.select_data("hypo", use_codex=False)
    t = sel.triggers[0]
    assert t.unverified
    assert not t.needs_manual
    assert t.series == "^VIX"
    assert t.source == SourceKind.YFINANCE.value
    assert calls["n"] == 0  # network errors must never trigger replacement


def test_manual_source_passthrough_not_probed(monkeypatch):
    monkeypatch.setattr(ds, "parse_risk", lambda h: _risk([_trig("m", "some_key", source=SourceKind.MANUAL_OVERRIDE)]))
    monkeypatch.setattr(ds, "codex_available", lambda: False)

    def boom(*a, **k):
        raise AssertionError("manual_override must not be probed")

    monkeypatch.setattr(ds, "probe", boom)
    sel = ds.select_data("hypo", use_codex=False)
    assert sel.triggers[0].source == SourceKind.MANUAL_OVERRIDE.value
    assert sel.triggers[0].status == "MANUAL"


def test_selection_to_payload_validates_with_tbd_thresholds(monkeypatch):
    monkeypatch.setattr(ds, "parse_risk", lambda h: _risk([_trig("good", "DGS10")]))
    monkeypatch.setattr(ds, "codex_available", lambda: False)
    monkeypatch.setattr(ds, "probe", lambda kind, series, thesis_name=None: _ok(series))

    sel = ds.select_data("hypo", use_codex=False)
    payload = ds.selection_to_payload(sel)
    risk = Risk.model_validate(payload)  # must not raise
    assert risk.triggers[0].threshold.red == "TBD"
    assert risk.triggers[0].series == "DGS10"


def test_codex_refine_updates_series(monkeypatch):
    monkeypatch.setattr(ds, "parse_risk", lambda h: _risk([_trig("t1", "DGS10")]))
    monkeypatch.setattr(ds, "codex_available", lambda: True)
    monkeypatch.setattr(ds, "run_codex", lambda prompt, reasoning_effort="medium", timeout=300: "irrelevant")
    monkeypatch.setattr(
        ds, "codex_extract_json",
        lambda out: {"triggers": [{"id": "t1", "series": "DGS30", "rationale": "30y better"}]},
    )
    monkeypatch.setattr(ds, "probe", lambda kind, series, thesis_name=None: _ok(series))

    sel = ds.select_data("hypo", use_codex=True)
    assert sel.codex_used
    t = sel.triggers[0]
    assert t.series == "DGS30"
    assert t.rationale.startswith("Codex:")


def test_manual_override_scaffold_flags_failed(monkeypatch):
    monkeypatch.setattr(ds, "parse_risk", lambda h: _risk([_trig("bad", "FAKE1")]))
    monkeypatch.setattr(ds, "codex_available", lambda: False)
    monkeypatch.setattr(ds, "probe", lambda kind, series, thesis_name=None: _notfound(series))
    monkeypatch.setattr(ds, "_propose_replacements", lambda h, un: {})  # no replacement offered

    sel = ds.select_data("hypo", use_codex=False, max_repair_rounds=1)
    scaffold = ds.manual_override_scaffold(sel)
    # downgraded trigger keeps its series ("FAKE1") as the override key
    assert "FAKE1" in scaffold
    assert "auto-resolution failed" in scaffold["FAKE1"]["note"]
