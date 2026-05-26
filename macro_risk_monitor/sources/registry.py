"""Registry mapping SourceKind -> concrete DataSource instance."""

from __future__ import annotations

from functools import lru_cache

from .. import config as cfg
from ..schemas import SourceKind
from .base import DataSource, SourceUnavailable
from .fred import FredSource
from .manual_override import ManualOverrideSource
from .sec_edgar import SecEdgarSource
from .yfinance_source import YFinanceSource


@lru_cache(maxsize=None)
def get_source(kind: SourceKind, thesis_name: str | None = None) -> DataSource:
    if kind is SourceKind.FRED:
        return FredSource(cfg.FRED_API_KEY, cfg.FRED_CACHE_DIR, cfg.CACHE_TTL_HOURS)
    if kind is SourceKind.YFINANCE:
        return YFinanceSource(cfg.YFINANCE_CACHE_DIR)
    if kind is SourceKind.SEC_EDGAR:
        return SecEdgarSource(cfg.SEC_USER_AGENT, cfg.EDGAR_CACHE_DIR)
    if kind is SourceKind.MANUAL_OVERRIDE:
        if thesis_name is None:
            raise SourceUnavailable(
                "manual_override requires thesis_name (per-thesis file "
                "data/manual_override/{thesis}.yaml)"
            )
        return ManualOverrideSource(
            cfg.BASE_DIR / "data" / "manual_override" / f"{thesis_name}.yaml"
        )
    raise SourceUnavailable(f"source {kind} not implemented in Phase 1")
