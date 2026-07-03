"""SEC EDGAR source for company facts (10-Q line items).

Phase 1 implements a thin wrapper over the public Company Facts API. The
typical usage is `series = "NVDA::Revenues"` where the left side is the
ticker (resolved to CIK) and the right side is a US-GAAP concept name.
Custom segment-level metrics like "Data Center revenue" are not in
companyfacts JSON — for those, the orchestrator falls back to
manual_override until Phase 2 NLP extraction is added.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import date
from pathlib import Path

import requests

from ..schemas import Reading, Trigger
from .base import DataSource, FetchError, SourceUnavailable

logger = logging.getLogger(__name__)

TICKER_INDEX_URL = "https://www.sec.gov/files/company_tickers.json"
COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"


class SecEdgarSource(DataSource):
    name = "sec_edgar"

    def __init__(self, user_agent: str, cache_dir: Path):
        if not user_agent or "@" not in user_agent:
            raise SourceUnavailable(
                "SEC EDGAR requires SEC_USER_AGENT env var with contact email"
            )
        self.user_agent = user_agent
        self.cache_dir = cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._cik_index: dict[str, str] | None = None

    def fetch(self, trigger: Trigger, as_of: date | None = None) -> Reading:
        if not trigger.series or "::" not in trigger.series:
            raise FetchError(
                f"sec_edgar trigger {trigger.id} series must be '<TICKER>::<CONCEPT>'"
            )
        ticker, concept = trigger.series.split("::", 1)
        cik = self._resolve_cik(ticker)
        facts = self._load_company_facts(cik)
        value, period_end = self._latest_value(facts, concept, as_of)
        if value is None:
            raise FetchError(
                f"sec_edgar concept {concept} not found for {ticker} (CIK {cik})"
            )
        return Reading(
            trigger_id=trigger.id,
            value=value,
            as_of=period_end,
            source_url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}",
            raw={"ticker": ticker, "cik": cik, "concept": concept},
        )

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self.user_agent, "Accept": "application/json"}

    def _resolve_cik(self, ticker: str) -> str:
        if self._cik_index is None:
            self._cik_index = self._fetch_cik_index()
        cik = self._cik_index.get(ticker.upper())
        if not cik:
            raise FetchError(f"ticker {ticker} not found in SEC index")
        return cik

    def _fetch_cik_index(self) -> dict[str, str]:
        cache_path = self.cache_dir / "company_tickers.json"
        if cache_path.exists() and (time.time() - cache_path.stat().st_mtime) < 86400:
            raw = json.loads(cache_path.read_text(encoding="utf-8"))
        else:
            logger.info("SEC ticker index fetch")
            resp = requests.get(TICKER_INDEX_URL, headers=self._headers(), timeout=20)
            if not resp.ok:
                raise FetchError(f"SEC ticker index {resp.status_code}")
            raw = resp.json()
            cache_path.write_text(json.dumps(raw), encoding="utf-8")
        return {
            row["ticker"].upper(): str(row["cik_str"]).zfill(10)
            for row in raw.values()
        }

    def _load_company_facts(self, cik: str) -> dict:
        cache_path = self.cache_dir / f"facts_{cik}.json"
        if cache_path.exists() and (time.time() - cache_path.stat().st_mtime) < 21600:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        url = COMPANY_FACTS_URL.format(cik=cik)
        logger.info("SEC company facts fetch CIK=%s", cik)
        resp = requests.get(url, headers=self._headers(), timeout=30)
        if not resp.ok:
            raise FetchError(f"SEC company facts {cik} -> {resp.status_code}")
        payload = resp.json()
        cache_path.write_text(json.dumps(payload), encoding="utf-8")
        return payload

    @staticmethod
    def _latest_value(
        facts: dict, concept: str, as_of: date | None
    ) -> tuple[float | None, date | None]:
        cap = as_of or date.today()
        for taxonomy in ("us-gaap", "ifrs-full", "dei"):
            tax_block = facts.get("facts", {}).get(taxonomy, {})
            concept_block = tax_block.get(concept)
            if not concept_block:
                continue
            units = concept_block.get("units", {})
            # (end_date DESC, duration ASC): flow concepts like Revenues carry
            # both the Q4 3-month and the FY 12-month figure with the *same*
            # end date — prefer the shortest duration so quarterly triggers
            # never silently pick up an annual cumulative value.
            best: tuple[float, date, int] | None = None
            for entries in units.values():
                for entry in entries:
                    end_str = entry.get("end")
                    if not end_str:
                        continue
                    end_d = date.fromisoformat(end_str)
                    if end_d > cap:
                        continue
                    val = entry.get("val")
                    if val is None:
                        continue
                    start_str = entry.get("start")
                    duration = 0
                    if start_str:
                        try:
                            duration = (end_d - date.fromisoformat(start_str)).days
                        except ValueError:
                            duration = 0
                    if (
                        best is None
                        or end_d > best[1]
                        or (end_d == best[1] and duration < best[2])
                    ):
                        best = (float(val), end_d, duration)
            if best:
                return best[0], best[1]
        return None, None
