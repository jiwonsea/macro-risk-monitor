"""Earnings-transcript keyword analysis over *local* transcript files.

Data-access decision (2026-07-02): paid transcript APIs break the
retail-accessible principle and scrapers break reproducibility, so this
source reads transcripts the user drops into a local directory:

    data/transcripts/{TICKER}/{YYYY-MM-DD}[-anything].txt

e.g. data/transcripts/MSFT/2026-04-29-fy26q3.txt. The date prefix makes the
file usable for `as_of`-aware evaluation (and therefore backtesting).

The trigger's `series` field must be `TICKERS::keywords`:

    series: "MSFT|GOOGL|META|AMZN::rationalize,efficiency,discipline"

Reading.value = number of distinct tickers whose *most recent* transcript
(within lookback_days, dated <= as_of) matches at least one keyword
(case-insensitive substring, OR semantics). That maps onto thresholds like
red ">= 2" / yellow ">= 1" / green "< 1" ("N개사 동시" semantics). Per-ticker
hit counts are kept in Reading.raw for the report.
"""

from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from pathlib import Path

from ..schemas import Reading, Trigger
from .base import DataSource, FetchError, SourceUnavailable

logger = logging.getLogger(__name__)

_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")


class TranscriptNlpSource(DataSource):
    name = "earnings_transcript_nlp"

    def __init__(self, transcripts_dir: Path, lookback_days: int = 120):
        self.transcripts_dir = transcripts_dir
        self.lookback_days = lookback_days

    def fetch(self, trigger: Trigger, as_of: date | None = None) -> Reading:
        tickers, keywords = self._parse_series(trigger)
        if not self.transcripts_dir.exists():
            raise SourceUnavailable(
                f"transcripts dir missing: {self.transcripts_dir} — create it and "
                "add {TICKER}/{YYYY-MM-DD}.txt files"
            )

        end = as_of or date.today()
        cutoff = end - timedelta(days=self.lookback_days)

        per_ticker: dict[str, dict] = {}
        n_matching = 0
        latest_seen: date | None = None
        for ticker in tickers:
            found = self._latest_transcript(ticker, cutoff, end)
            if found is None:
                per_ticker[ticker] = {"transcript": None, "hits": None}
                continue
            t_date, path = found
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            hits = {kw: text.count(kw) for kw in keywords}
            matched = any(n > 0 for n in hits.values())
            per_ticker[ticker] = {
                "transcript": path.name,
                "date": t_date.isoformat(),
                "hits": hits,
                "matched": matched,
            }
            if matched:
                n_matching += 1
            if latest_seen is None or t_date > latest_seen:
                latest_seen = t_date

        if latest_seen is None:
            raise FetchError(
                f"no transcripts within lookback for {trigger.id} "
                f"({', '.join(tickers)} in {self.transcripts_dir}, "
                f"window {cutoff}..{end})"
            )

        return Reading(
            trigger_id=trigger.id,
            value=float(n_matching),
            as_of=latest_seen,
            source_url=str(self.transcripts_dir),
            raw={
                "tickers": tickers,
                "keywords": keywords,
                "lookback_days": self.lookback_days,
                "per_ticker": per_ticker,
                "n_matching_tickers": n_matching,
            },
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_series(trigger: Trigger) -> tuple[list[str], list[str]]:
        series = trigger.series or ""
        if "::" not in series:
            raise FetchError(
                f"earnings_transcript_nlp trigger {trigger.id} series must be "
                "'TICKER1|TICKER2::keyword1,keyword2' "
                f"(got {series!r})"
            )
        ticker_part, kw_part = series.split("::", 1)
        tickers = [t.strip().upper() for t in ticker_part.split("|") if t.strip()]
        keywords = [k.strip().lower() for k in kw_part.split(",") if k.strip()]
        if not tickers or not keywords:
            raise FetchError(
                f"earnings_transcript_nlp trigger {trigger.id}: empty tickers or keywords"
            )
        return tickers, keywords

    def _latest_transcript(
        self, ticker: str, cutoff: date, end: date
    ) -> tuple[date, Path] | None:
        d = self.transcripts_dir / ticker
        if not d.is_dir():
            return None
        best: tuple[date, Path] | None = None
        for p in d.glob("*.txt"):
            m = _DATE_PREFIX.match(p.stem)
            if not m:
                logger.warning("transcript without date prefix skipped: %s", p)
                continue
            try:
                t_date = date.fromisoformat(m.group(1))
            except ValueError:
                continue
            if not (cutoff <= t_date <= end):
                continue
            if best is None or t_date > best[0]:
                best = (t_date, p)
        return best
