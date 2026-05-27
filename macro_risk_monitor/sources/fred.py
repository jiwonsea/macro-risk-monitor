"""FRED economic data source.

Uses the public FRED API directly via `requests`. The `fredapi` package is
listed as an optional dependency but is intentionally not used here so the
core path stays light. Cached responses are stored as JSON keyed by series
id and end date.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

import requests

from .. import schemas  # noqa: F401  (re-export for callers)
from ..schemas import Reading, Trigger
from .base import DataSource, FetchError, SourceUnavailable

logger = logging.getLogger(__name__)

FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES_URL = "https://api.stlouisfed.org/fred/series"
_SERIES_UNITS_CACHE: dict[str, str] = {}


class FredSource(DataSource):
    name = "fred"

    def __init__(self, api_key: str | None, cache_dir: Path, cache_ttl_hours: int = 6):
        self.api_key = api_key
        self.cache_dir = cache_dir
        self.cache_ttl_hours = cache_ttl_hours
        cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch(self, trigger: Trigger, as_of: date | None = None) -> Reading:
        if not trigger.series:
            raise FetchError(f"FRED trigger {trigger.id} missing series id")
        if not self.api_key:
            raise SourceUnavailable("FRED_API_KEY not configured")

        end = as_of or date.today()
        cache_path = self.cache_dir / f"{trigger.series}_{end.isoformat()}.json"

        if cache_path.exists() and self._cache_fresh(cache_path):
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
        else:
            payload = self._call_api(trigger.series, end)
            cache_path.write_text(json.dumps(payload), encoding="utf-8")

        latest = self._latest_observation(payload)
        if latest is None:
            raise FetchError(f"FRED returned no observations for {trigger.series}")
        value_str, obs_date_str = latest
        try:
            value: float | None = float(value_str)
        except ValueError:
            value = None
        raw = {"series": trigger.series, "latest": latest}
        fred_units = self._fetch_series_units(trigger.series)
        if fred_units:
            raw["fred_units"] = fred_units
        return Reading(
            trigger_id=trigger.id,
            value=value,
            as_of=date.fromisoformat(obs_date_str),
            source_url=f"https://fred.stlouisfed.org/series/{trigger.series}",
            raw=raw,
        )

    def _call_api(self, series_id: str, end: date) -> dict:
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "observation_end": end.isoformat(),
            "sort_order": "desc",
            "limit": 50,
        }
        logger.info("FRED API fetch series=%s end=%s", series_id, end.isoformat())
        resp = requests.get(FRED_API_URL, params=params, timeout=20)
        if not resp.ok:
            raise FetchError(f"FRED {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    def _fetch_series_units(self, series_id: str) -> str | None:
        if series_id in _SERIES_UNITS_CACHE:
            return _SERIES_UNITS_CACHE[series_id]
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
        }
        try:
            logger.info("FRED metadata fetch series=%s", series_id)
            resp = requests.get(FRED_SERIES_URL, params=params, timeout=20)
            if not resp.ok:
                logger.warning("FRED metadata %s for %s", resp.status_code, series_id)
                return None
            series = resp.json().get("seriess", [])
            if not series:
                return None
            units = series[0].get("units_short") or series[0].get("units")
        except Exception as exc:  # noqa: BLE001 - metadata is best effort
            logger.warning("FRED metadata fetch failed for %s: %s", series_id, exc)
            return None
        if units:
            _SERIES_UNITS_CACHE[series_id] = units
        return units

    @staticmethod
    def _latest_observation(payload: dict) -> tuple[str, str] | None:
        for obs in payload.get("observations", []):
            if obs.get("value") not in (".", None):
                return obs["value"], obs["date"]
        return None

    def _cache_fresh(self, cache_path: Path) -> bool:
        import time

        age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
        return age_hours < self.cache_ttl_hours
