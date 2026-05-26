"""Pydantic models shared across the pipeline.

A Risk (loaded from YAML or built from ad-hoc input) carries a list of Triggers.
Each Trigger is evaluated against a fetched Reading to produce a Verdict.
The aggregation of Verdicts produces a Decision.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Category(str, Enum):
    LEADING = "leading"
    COINCIDENT = "coincident"
    LAGGING = "lagging"


class Status(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    UNKNOWN = "unknown"   # data not available


class SourceKind(str, Enum):
    FRED = "fred"
    YFINANCE = "yfinance"
    SEC_EDGAR = "sec_edgar"
    NEWS_RSS = "news_rss"
    MANUAL_OVERRIDE = "manual_override"
    EARNINGS_TRANSCRIPT_NLP = "earnings_transcript_nlp"


class PatchAction(str, Enum):
    KEEP = "KEEP"
    MODIFY_THRESHOLD = "MODIFY-threshold"
    MODIFY_CATEGORY = "MODIFY-category"
    MODIFY_SOURCE = "MODIFY-source"
    REPLACE = "REPLACE"
    ADD = "ADD"


# ---------------------------------------------------------------------------
# Trigger / Reading / Verdict
# ---------------------------------------------------------------------------
class Threshold(BaseModel):
    red: str | None = None
    yellow: str | None = None
    green: str | None = None

    def has_any(self) -> bool:
        return any([self.red, self.yellow, self.green])


class Trigger(BaseModel):
    id: str
    category: Category
    source: SourceKind
    series: str | None = None           # e.g. FRED series id, ticker, override key
    unit: str | None = None
    description: str | None = None
    threshold: Threshold


class PatchEntry(BaseModel):
    target_id: str
    action: PatchAction
    new_id: str | None = None
    new_series: str | None = None
    new_category: Category | None = None
    new_source: SourceKind | None = None
    new_threshold: Threshold | None = None
    new_description: str | None = None
    new_unit: str | None = None
    new_override: dict[str, Any] | None = None
    rationale: str = ""
    unverified: bool = False


class ReviewPatch(BaseModel):
    thesis_name: str
    reviewer: str = "codex"
    review_date: date
    entries: list[PatchEntry]


class Reading(BaseModel):
    """Single evaluation snapshot for one trigger."""

    trigger_id: str
    value: float | str | None
    as_of: date | None = None
    source_url: str | None = None
    raw: dict[str, Any] | None = None   # original payload for verifier

    @field_validator("as_of", mode="before")
    @classmethod
    def _coerce_date(cls, v: Any) -> Any:
        if isinstance(v, datetime):
            return v.date()
        return v


class Verdict(BaseModel):
    trigger_id: str
    status: Status
    reading: Reading | None = None
    rationale: str | None = None        # one-line text-format threshold comparison


# ---------------------------------------------------------------------------
# Risk (Hypothesis)
# ---------------------------------------------------------------------------
class Risk(BaseModel):
    """A macro risk or hypothesis with associated triggers and decision rule.

    Loaded from theses/*.yaml or synthesised by ai/risk_parser.py.
    """

    name: str
    title: str
    hypothesis: str
    created: date | None = None
    historical_analogy: list[str] = Field(default_factory=list)
    triggers: list[Trigger]
    decision_rule: Literal["rule_of_three"] = "rule_of_three"
    critical_windows: list[date] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("triggers")
    @classmethod
    def _unique_ids(cls, v: list[Trigger]) -> list[Trigger]:
        ids = [t.id for t in v]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate trigger ids in risk: {ids}")
        return v


# ---------------------------------------------------------------------------
# Decision and Report
# ---------------------------------------------------------------------------
class Decision(BaseModel):
    """Output of decision rule applied to the set of Verdicts."""

    rule: str
    action: Literal["defensive_position", "hedge_increase", "monitor", "no_signal"]
    summary: str
    red_categories: list[Category] = Field(default_factory=list)
    yellow_categories: list[Category] = Field(default_factory=list)


class CitationCheck(BaseModel):
    """Result of ai/verifier.py — were LLM-cited numbers grounded in sources?"""

    passed: bool
    grounded_count: int
    ungrounded: list[str] = Field(default_factory=list)


class Report(BaseModel):
    """Final aggregate passed to output/ for rendering."""

    risk: Risk
    verdicts: list[Verdict]
    decision: Decision
    llm_analysis_md: str
    citation_check: CitationCheck
    generated_at: datetime
    llm_model: str
