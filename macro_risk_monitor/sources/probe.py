"""Existence / fetchability probe for a (source, series) pair.

Used by ai/data_selector.py at thesis-authoring time to verify that an
LLM-proposed series id actually resolves *before* it is written into a thesis
YAML. The probe reuses each source's own ``fetch()`` so it exercises the exact
code path the pipeline will later run — a series that probes OK is a series the
pipeline can read.

The probe deliberately distinguishes two failure modes, because they drive
different repair decisions in data_selector:

    not_found   the series does not exist or returns no usable value
                -> replaceable: ask the model for a different series
    network     transient connectivity/SSL error
    unavailable missing credential or optional dependency
                -> keep the series as-is, flag it "unverified" (do not replace
                   a possibly-correct series just because we could not reach it)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

import requests

from .. import config as cfg
from ..schemas import Category, SourceKind, Threshold, Trigger
from .base import SourceUnavailable
from .registry import get_source  # patched in tests via probe.get_source

logger = logging.getLogger(__name__)

FRED_SEARCH_URL = "https://api.stlouisfed.org/fred/series/search"

# Substrings that mark a caught error as transient/connectivity rather than a
# genuinely missing series. yfinance funnels network and SSL failures through
# the same FetchError as a bad ticker, so message inspection is the only signal.
_NETWORK_SIGNALS = (
    "ssl",
    "connection",
    "timed out",
    "timeout",
    "max retries",
    "failed to resolve",
    "getaddrinfo",
    "name resolution",
    "temporarily unavailable",
)

# error_kind values that mean "this series is no good, replace it".
REPLACEABLE_KINDS = frozenset({"not_found"})


@dataclass
class ProbeResult:
    ok: bool
    series: str
    source: SourceKind
    units: str | None = None
    latest_value: float | str | None = None
    as_of: date | None = None
    title: str | None = None
    error: str | None = None
    error_kind: str | None = None  # not_found | network | unavailable | None

    @property
    def replaceable(self) -> bool:
        return self.error_kind in REPLACEABLE_KINDS


@dataclass
class SeriesCandidate:
    series: str
    title: str | None = None
    units: str | None = None
    frequency: str | None = None
    popularity: int | None = None


def probe(
    source: SourceKind, series: str, thesis_name: str | None = None
) -> ProbeResult:
    """Attempt to resolve ``series`` through its source's ``fetch()``."""

    trig = Trigger(
        id="__probe__",
        category=Category.LEADING,
        source=source,
        series=series,
        threshold=Threshold(),
    )
    try:
        src = get_source(source, thesis_name=thesis_name)
        reading = src.fetch(trig)
    except Exception as exc:  # noqa: BLE001 — classify, never raise to caller
        kind = _classify(exc)
        logger.info("probe %s/%s failed (%s): %s", source.value, series, kind, exc)
        return ProbeResult(
            ok=False, series=series, source=source, error=str(exc), error_kind=kind
        )

    ok = reading.value is not None
    units = None
    if isinstance(reading.raw, dict):
        units = reading.raw.get("fred_units")
    return ProbeResult(
        ok=ok,
        series=series,
        source=source,
        units=units,
        latest_value=reading.value,
        as_of=reading.as_of,
        error=None if ok else "source returned no usable value",
        error_kind=None if ok else "not_found",
    )


def _classify(exc: Exception) -> str:
    if isinstance(exc, SourceUnavailable):
        return "unavailable"
    msg = str(exc).lower()
    if any(sig in msg for sig in _NETWORK_SIGNALS):
        return "network"
    return "not_found"


def search_fred_series(keywords: str, limit: int = 6) -> list[SeriesCandidate]:
    """Return real FRED series matching ``keywords`` (popularity-ranked).

    Empty list on missing key or any error — the caller treats search results
    as optional grounding, not a hard requirement.
    """

    if not cfg.FRED_API_KEY:
        return []
    params = {
        "search_text": keywords,
        "api_key": cfg.FRED_API_KEY,
        "file_type": "json",
        "order_by": "popularity",
        "sort_order": "desc",
        "limit": limit,
    }
    try:
        resp = requests.get(FRED_SEARCH_URL, params=params, timeout=20)
        if not resp.ok:
            logger.warning("FRED search %s for %r", resp.status_code, keywords)
            return []
        seriess = resp.json().get("seriess", [])
    except Exception as exc:  # noqa: BLE001 — search is best-effort
        logger.warning("FRED search failed for %r: %s", keywords, exc)
        return []
    return [
        SeriesCandidate(
            series=s["id"],
            title=s.get("title"),
            units=s.get("units_short") or s.get("units"),
            frequency=s.get("frequency_short"),
            popularity=s.get("popularity"),
        )
        for s in seriess
        if s.get("id")
    ]
