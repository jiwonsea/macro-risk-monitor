"""Authoring-time data selection: hypothesis -> verified trigger series.

Pipeline (all at thesis-authoring time, never at run time so `run` stays
deterministic):

    A. Claude drafts triggers          (reuse risk_parser.parse_risk)
    A'. Codex critiques the series      (optional, single round)
    B. probe + repair loop              (FRED/yfinance only in phase 1)
    -> SelectionResult                  (CLI confirms, then writes thesis YAML)

Invariant preserved: this module decides *source + series* only. Thresholds are
never chosen here — selection_to_payload scaffolds them as "TBD" for the user
to set (CLAUDE.md: "임계치는 사용자 정의").

The model/network entry points (`parse_risk`, `probe`, `codex_available`,
`run_codex`, `_call_claude`) are module-level so unit tests can patch them and
exercise the repair logic offline.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import date

from .. import config as cfg
from ..schemas import SourceKind
from ..sources.probe import ProbeResult, probe, search_fred_series
from .codex_client import CodexUnavailable, codex_available
from .codex_client import extract_json as codex_extract_json
from .codex_client import run_codex
from .prompt_templates import (
    DATA_REPAIR_SYSTEM,
    build_codex_selection_message,
    build_repair_message,
)
from .risk_parser import _extract_json, parse_risk

logger = logging.getLogger(__name__)

# Only these sources are auto-verified/repaired in phase 1. Others (manual_override,
# sec_edgar, news_rss...) pass through unchanged — their series are trusted as written.
AUTO_SOURCES = frozenset({SourceKind.FRED, SourceKind.YFINANCE})


@dataclass
class ResolvedTrigger:
    id: str
    category: str
    source: str
    series: str
    unit: str | None = None
    description: str | None = None
    rationale: str = ""
    probe: ProbeResult | None = None
    needs_manual: bool = False  # auto-resolution exhausted -> downgraded to manual
    unverified: bool = False  # probe could not run (network/credential)

    @property
    def status(self) -> str:
        if self.needs_manual:
            return "MANUAL"
        if self.unverified:
            return "UNVERIFIED"
        if _to_kind(self.source) not in AUTO_SOURCES:
            return "MANUAL" if _to_kind(self.source) is SourceKind.MANUAL_OVERRIDE else "SKIP"
        return "OK" if self.probe and self.probe.ok else "MANUAL"


@dataclass
class SelectionResult:
    name: str
    title: str
    hypothesis: str
    historical_analogy: list[str] = field(default_factory=list)
    critical_windows: list[dict] = field(default_factory=list)
    triggers: list[ResolvedTrigger] = field(default_factory=list)
    codex_used: bool = False


def select_data(
    hypothesis: str, *, use_codex: bool = True, max_repair_rounds: int = 3
) -> SelectionResult:
    risk = parse_risk(hypothesis)
    candidates = [
        ResolvedTrigger(
            id=t.id,
            category=t.category.value,
            source=t.source.value,
            series=t.series or "",
            unit=t.unit,
            description=t.description,
            rationale="Claude initial proposal",
        )
        for t in risk.triggers
    ]

    codex_used = False
    if use_codex and codex_available():
        candidates = _codex_refine(hypothesis, candidates)
        codex_used = True

    candidates = _repair_loop(hypothesis, candidates, max_repair_rounds)

    return SelectionResult(
        name=risk.name,
        title=risk.title,
        hypothesis=risk.hypothesis,
        historical_analogy=list(risk.historical_analogy),
        critical_windows=[
            {
                "date": w.date.isoformat(),
                "event": w.event,
                "rationale": w.rationale,
            }
            for w in risk.critical_windows
        ],
        triggers=candidates,
        codex_used=codex_used,
    )


# ---------------------------------------------------------------------------
# Stage A': Codex critique
# ---------------------------------------------------------------------------
def _codex_refine(
    hypothesis: str, candidates: list[ResolvedTrigger]
) -> list[ResolvedTrigger]:
    payload = [
        {
            "id": c.id,
            "category": c.category,
            "source": c.source,
            "series": c.series,
            "unit": c.unit,
            "description": c.description,
        }
        for c in candidates
    ]
    prompt = build_codex_selection_message(hypothesis, payload)
    try:
        out = run_codex(prompt, reasoning_effort="medium", timeout=300)
    except CodexUnavailable as exc:
        logger.warning("Codex refine skipped: %s", exc)
        return candidates

    data = codex_extract_json(out)
    if not data or not isinstance(data.get("triggers"), list):
        logger.warning("Codex refine returned no parseable JSON; keeping Claude proposal")
        return candidates

    by_id = {c.id: c for c in candidates}
    for entry in data["triggers"]:
        if not isinstance(entry, dict):
            continue
        c = by_id.get(entry.get("id"))
        if c is None:  # phase 1: Codex may not add/drop triggers
            continue
        if entry.get("source"):
            c.source = entry["source"]
        if entry.get("series"):
            c.series = entry["series"]
        if entry.get("unit"):
            c.unit = entry["unit"]
        if entry.get("description"):
            c.description = entry["description"]
        if entry.get("rationale"):
            c.rationale = f"Codex: {entry['rationale']}"
    return candidates


# ---------------------------------------------------------------------------
# Stage B: probe + repair loop
# ---------------------------------------------------------------------------
def _repair_loop(
    hypothesis: str, candidates: list[ResolvedTrigger], max_rounds: int
) -> list[ResolvedTrigger]:
    for round_i in range(1, max_rounds + 1):
        unresolved: list[ResolvedTrigger] = []
        for c in candidates:
            kind = _to_kind(c.source)
            if kind not in AUTO_SOURCES:
                continue  # phase 1: only verify fred/yfinance
            if c.probe and c.probe.ok:
                continue  # resolved in an earlier round
            c.probe = probe(kind, c.series)
            if c.probe.ok:
                c.unverified = False
            elif c.probe.replaceable:
                unresolved.append(c)
            else:
                c.unverified = True  # network/credential -> keep series, flag it

        if not unresolved:
            break

        replacements = _propose_replacements(hypothesis, unresolved)
        applied = False
        for c in unresolved:
            repl = replacements.get(c.id)
            new_series = repl.get("series") if repl else None
            if not new_series:
                continue
            c.source = repl.get("source", c.source)
            c.series = new_series
            note = repl.get("rationale", "")
            c.rationale = f"{c.rationale} | repair r{round_i}: {note}".strip(" |")
            c.probe = None  # force re-probe on the next round
            applied = True
        if not applied:
            break  # model offered nothing usable; stop spending rounds

    _downgrade_unresolved(candidates)
    return candidates


def _downgrade_unresolved(candidates: list[ResolvedTrigger]) -> None:
    """Anything in an auto-source still unresolved (and not merely unverified)
    after the repair budget is downgraded to manual_override rather than left
    pointing at a non-existent series or silently dropped."""

    for c in candidates:
        if _to_kind(c.source) not in AUTO_SOURCES:
            continue
        if c.probe and c.probe.ok:
            continue
        if c.unverified:
            continue  # network/credential: keep series as-is, already flagged
        c.needs_manual = True
        c.source = SourceKind.MANUAL_OVERRIDE.value


def _propose_replacements(
    hypothesis: str, unresolved: list[ResolvedTrigger]
) -> dict[str, dict]:
    enriched = []
    for c in unresolved:
        fred_candidates: list[dict] = []
        if _to_kind(c.source) is SourceKind.FRED:
            keywords = c.description or c.id.replace("_", " ")
            fred_candidates = [asdict(x) for x in search_fred_series(keywords)]
        enriched.append(
            {
                "id": c.id,
                "source": c.source,
                "series": c.series,
                "description": c.description,
                "error": c.probe.error if c.probe else None,
                "fred_candidates": fred_candidates,
            }
        )

    data = _call_claude(DATA_REPAIR_SYSTEM, build_repair_message(hypothesis, enriched))
    if not data:
        return {}
    out: dict[str, dict] = {}
    for r in data.get("replacements", []):
        if isinstance(r, dict) and r.get("id"):
            out[r["id"]] = r
    return out


# ---------------------------------------------------------------------------
# Claude JSON call (mirrors risk_parser._call_llm degrade contract)
# ---------------------------------------------------------------------------
def _call_claude(system: str, user: str) -> dict | None:
    if not cfg.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set; repair step cannot propose replacements")
        return None
    try:
        from anthropic import Anthropic
    except ImportError:
        logger.warning("anthropic not installed; repair step skipped")
        return None
    client = Anthropic(api_key=cfg.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=cfg.LLM_MODEL,
        max_tokens=2048,
        temperature=0.2,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    raw = "".join(b.text for b in resp.content if b.type == "text")
    json_str = _extract_json(raw)
    if not json_str:
        return None
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# YAML payload
# ---------------------------------------------------------------------------
def selection_to_payload(sel: SelectionResult) -> dict:
    """Build a Risk-validatable dict. Thresholds are scaffolded as TBD."""

    triggers = []
    for c in sel.triggers:
        triggers.append(
            {
                "id": c.id,
                "category": c.category,
                "source": c.source,
                "series": c.series,
                "unit": c.unit,
                "description": c.description,
                "threshold": {"red": "TBD", "yellow": "TBD", "green": "TBD"},
            }
        )
    payload: dict = {
        "name": sel.name,
        "title": sel.title,
        "hypothesis": sel.hypothesis,
        "created": date.today().isoformat(),
        "historical_analogy": sel.historical_analogy,
        "triggers": triggers,
    }
    if sel.critical_windows:
        payload["critical_windows"] = sel.critical_windows
    return payload


def manual_override_scaffold(sel: SelectionResult) -> dict:
    """Stub entries for every manual_override trigger so the user has a file to
    fill. Auto-downgraded triggers carry an explanatory note."""

    out: dict = {}
    for c in sel.triggers:
        if c.source != SourceKind.MANUAL_OVERRIDE.value:
            continue
        key = c.series or c.id
        note = c.description or ""
        if c.needs_manual:
            note = (note + " (auto-resolution failed; fill manually)").strip()
        out[key] = {
            "value": None,
            "as_of": None,
            "source_url": None,
            "note": note,
        }
    return out


def _to_kind(source: str) -> SourceKind | None:
    try:
        return SourceKind(source)
    except ValueError:
        return None
