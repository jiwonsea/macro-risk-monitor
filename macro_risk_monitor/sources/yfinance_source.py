"""yfinance source for equities, ETFs, and CBOE indices like ^VIX."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from ..schemas import Reading, Trigger
from .base import DataSource, FetchError, SourceUnavailable

logger = logging.getLogger(__name__)


class YFinanceSource(DataSource):
    name = "yfinance"

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch(self, trigger: Trigger, as_of: date | None = None) -> Reading:
        if not trigger.series:
            raise FetchError(f"yfinance trigger {trigger.id} missing series id")

        try:
            import yfinance as yf
        except ImportError as exc:
            raise SourceUnavailable(
                "yfinance not installed; install with `pip install 'macro-risk-monitor[sources]'`"
            ) from exc

        start, end = self.default_window(as_of, days=180)
        logger.info("yfinance fetch ticker=%s window=%s..%s", trigger.series, start, end)
        try:
            ticker = yf.Ticker(trigger.series)
            hist = ticker.history(start=start.isoformat(), end=end.isoformat(), auto_adjust=False)
        except Exception as exc:  # noqa: BLE001 — yfinance can raise SSL, JSON, etc.
            raise FetchError(f"yfinance error for {trigger.series}: {exc}") from exc
        if hist is None or hist.empty:
            raise FetchError(f"yfinance returned empty history for {trigger.series}")

        # Rows with NaN Close (e.g. partially populated sessions) would leak a
        # NaN Reading value downstream; keep only rows with a real close.
        hist = hist[hist["Close"].notna()]
        if hist.empty:
            raise FetchError(f"yfinance history has no non-NaN close for {trigger.series}")

        last_row = hist.iloc[-1]
        last_date = hist.index[-1].date()
        return Reading(
            trigger_id=trigger.id,
            value=float(last_row["Close"]),
            as_of=last_date,
            source_url=f"https://finance.yahoo.com/quote/{trigger.series}",
            raw={
                "ticker": trigger.series,
                "open": float(last_row["Open"]),
                "high": float(last_row["High"]),
                "low": float(last_row["Low"]),
                "close": float(last_row["Close"]),
                "volume": _safe_volume(last_row),
            },
        )


def _safe_volume(row) -> int | None:
    # Volume can be missing or NaN (indices like ^VIX); int(NaN) raises.
    if "Volume" not in row:
        return None
    vol = row["Volume"]
    try:
        if vol != vol:  # NaN check without importing numpy/math for pandas scalars
            return None
        return int(vol)
    except (TypeError, ValueError):
        return None
