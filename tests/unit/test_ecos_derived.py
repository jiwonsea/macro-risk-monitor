"""ECOS source (offline cache path) and derived spread source."""

from __future__ import annotations

import json
from datetime import date

import pytest

from macro_risk_monitor.schemas import Category, Reading, SourceKind, Threshold, Trigger
from macro_risk_monitor.sources.base import FetchError, SourceUnavailable
from macro_risk_monitor.sources.derived import DerivedSource, parse_legs
from macro_risk_monitor.sources.ecos import EcosSource, latest_row, parse_series


def _trig(source: SourceKind, series: str) -> Trigger:
    return Trigger(id="t", category=Category.LEADING, source=source, series=series,
                   threshold=Threshold(red=">= 1"))


def _payload(rows):
    return {"StatisticSearch": {"list_total_count": len(rows), "row": [
        {"TIME": t, "DATA_VALUE": v, "ITEM_NAME1": "국고채(10년)", "UNIT_NAME": "연%"} for t, v in rows
    ]}}


def test_parse_series_rejects_bad_cycle():
    assert parse_series("817Y002/D/010210000") == ("817Y002", "D", "010210000")
    with pytest.raises(FetchError):
        parse_series("817Y002/X/010210000")


def test_latest_row_skips_blank_and_picks_max_time():
    p = _payload([("20261001", "4.436"), ("20261002", "4.365"), ("20261005", "")])
    assert latest_row(p)["TIME"] == "20261002"


def test_ecos_reads_cached_snapshot_without_key(tmp_path):
    src = EcosSource(api_key=None, cache_dir=tmp_path)
    end = date(2026, 10, 5)
    src.cache_path("817Y002/D/010210000", end).write_text(
        json.dumps(_payload([("20261001", "4.436"), ("20261002", "4.365")])), encoding="utf-8")
    r = src.fetch(_trig(SourceKind.ECOS, "817Y002/D/010210000"), as_of=end)
    assert r.value == pytest.approx(4.365)
    assert r.as_of == date(2026, 10, 2)
    assert r.raw["unit"] == "연%"


def test_ecos_without_key_or_cache_is_unavailable(tmp_path):
    src = EcosSource(api_key=None, cache_dir=tmp_path)
    with pytest.raises(SourceUnavailable):
        src.fetch(_trig(SourceKind.ECOS, "817Y002/D/010210000"), as_of=date(2026, 10, 5))


def test_parse_legs_and_rejects_nested():
    a, b = parse_legs("ecos:817Y002/D/010210000 - fred:DGS10")
    assert a == (SourceKind.ECOS, "817Y002/D/010210000") and b == (SourceKind.FRED, "DGS10")
    with pytest.raises(FetchError):
        parse_legs("derived:x - fred:DGS10")
    with pytest.raises(FetchError):
        parse_legs("ecos 817Y002 minus fred DGS10")


class _Stub:
    def __init__(self, value, as_of):
        self.value, self.as_of = value, as_of

    def fetch(self, trigger, as_of=None):
        return Reading(trigger_id=trigger.id, value=self.value, as_of=self.as_of, source_url="stub")


def test_derived_spread_uses_older_leg_date():
    stubs = {SourceKind.ECOS: _Stub(4.365, date(2026, 10, 2)),
             SourceKind.FRED: _Stub(5.24, date(2026, 10, 1))}
    src = DerivedSource(lambda k: stubs[k])
    r = src.fetch(_trig(SourceKind.DERIVED, "ecos:817Y002/D/010210000 - fred:DGS10"))
    assert r.value == pytest.approx(-0.875)
    assert r.as_of == date(2026, 10, 1)
    assert len(r.raw["legs"]) == 2
