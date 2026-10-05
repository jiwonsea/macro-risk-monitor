"""Bank of Korea ECOS Open API source.

Series id format: ``STAT_CODE/CYCLE/ITEM_CODE`` — e.g. ``817Y002/D/010210000``
(국고채 10년, 일별). CYCLE is one of D / M / Q / A.

Responses are cached as JSON under ``.cache/ecos/{safe_series}_{end}.json`` in
the same shape the API returns, so a snapshot collected elsewhere (e.g. through a
browser when the runtime has no outbound network) can be dropped into the cache
and evaluated offline.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import date, timedelta
from pathlib import Path

import requests

from ..schemas import Reading, Trigger
from .base import DataSource, FetchError, SourceUnavailable

logger = logging.getLogger(__name__)

ECOS_URL = "https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/{start}/{end}/{stat}/{cycle}/{frm}/{to}/{item}"
_LOOKBACK = {"D": 45, "M": 400, "Q": 800, "A": 2200}


def parse_series(series: str) -> tuple[str, str, str]:
    parts = [p.strip() for p in series.split("/")]
    if len(parts) != 3 or parts[1] not in _LOOKBACK:
        raise FetchError(f"ECOS series must be STAT/CYCLE/ITEM with CYCLE in D/M/Q/A: {series!r}")
    return parts[0], parts[1], parts[2]


def _fmt(d: date, cycle: str) -> str:
    if cycle == "D":
        return d.strftime("%Y%m%d")
    if cycle == "M":
        return d.strftime("%Y%m")
    if cycle == "Q":
        return f"{d.year}Q{(d.month - 1) // 3 + 1}"
    return str(d.year)


def _parse_time(t: str, cycle: str) -> date:
    if cycle == "D":
        return date(int(t[:4]), int(t[4:6]), int(t[6:8]))
    if cycle == "M":
        return date(int(t[:4]), int(t[4:6]), 1)
    if cycle == "Q":
        return date(int(t[:4]), (int(t[-1]) - 1) * 3 + 1, 1)
    return date(int(t[:4]), 1, 1)


def latest_row(payload: dict) -> dict | None:
    rows = (payload.get("StatisticSearch") or {}).get("row") or []
    valid = [r for r in rows if r.get("DATA_VALUE") not in (None, "", ".")]
    if not valid:
        return None
    return max(valid, key=lambda r: r["TIME"])


class EcosSource(DataSource):
    name = "ecos"

    def __init__(self, api_key: str | None, cache_dir: Path, cache_ttl_hours: int = 6):
        self.api_key = api_key
        self.cache_dir = cache_dir
        self.cache_ttl_hours = cache_ttl_hours
        cache_dir.mkdir(parents=True, exist_ok=True)

    def cache_path(self, series: str, end: date) -> Path:
        return self.cache_dir / f"{series.replace('/', '_')}_{end.isoformat()}.json"

    def fetch(self, trigger: Trigger, as_of: date | None = None) -> Reading:
        if not trigger.series:
            raise FetchError(f"ECOS trigger {trigger.id} missing series id")
        stat, cycle, item = parse_series(trigger.series)
        end = as_of or date.today()
        path = self.cache_path(trigger.series, end)

        if path.exists() and self._fresh(path):
            payload = json.loads(path.read_text(encoding="utf-8"))
        else:
            if not self.api_key:
                raise SourceUnavailable("ECOS_API_KEY not configured and no cached snapshot")
            payload = self._call(stat, cycle, item, end)
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        row = latest_row(payload)
        if row is None:
            raise FetchError(f"ECOS returned no observations for {trigger.series}")
        try:
            value: float | None = float(row["DATA_VALUE"])
        except (TypeError, ValueError):
            value = None
        return Reading(
            trigger_id=trigger.id,
            value=value,
            as_of=_parse_time(row["TIME"], cycle),
            source_url=f"https://ecos.bok.or.kr/ (STAT {stat} / ITEM {item})",
            raw={
                "series": trigger.series,
                "item_name": row.get("ITEM_NAME1"),
                "unit": row.get("UNIT_NAME"),
                "latest": [row["DATA_VALUE"], row["TIME"]],
            },
        )

    def _call(self, stat: str, cycle: str, item: str, end: date) -> dict:
        start = end - timedelta(days=_LOOKBACK[cycle])
        url = ECOS_URL.format(
            key=self.api_key, start=1, end=1000, stat=stat, cycle=cycle,
            frm=_fmt(start, cycle), to=_fmt(end, cycle), item=item,
        )
        logger.info("ECOS fetch stat=%s cycle=%s item=%s", stat, cycle, item)
        resp = requests.get(url, timeout=20)
        if not resp.ok:
            raise FetchError(f"ECOS {resp.status_code}: {resp.text[:200]}")
        payload = resp.json()
        if "RESULT" in payload and "StatisticSearch" not in payload:
            raise FetchError(f"ECOS error: {payload['RESULT']}")
        return payload

    def _fresh(self, path: Path) -> bool:
        return (time.time() - path.stat().st_mtime) / 3600 < self.cache_ttl_hours
