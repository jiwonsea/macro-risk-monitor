"""Historical replay: sweep `as_of` over a date range and re-evaluate triggers.

Honesty contract: only sources that can genuinely reproduce a historical
reading are evaluated — FRED / yfinance / SEC EDGAR honour `as_of` in their
fetch, and earnings_transcript_nlp reads date-stamped local files. Sources
that would silently return *today's* value for a past date (manual_override)
or have no archive (news_rss) are reported as UNKNOWN with an explicit
"not backtestable" rationale instead of fabricating history.

The LLM layer is never invoked; a backtest is pure fetch + threshold
evaluation + rule_of_three.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from ..engine import apply_rule_of_three, evaluate
from ..schemas import Risk, SourceKind, Status, Verdict
from ..sources import FetchError, SourceUnavailable, get_source

logger = logging.getLogger(__name__)

BACKTESTABLE_SOURCES = frozenset(
    {
        SourceKind.FRED,
        SourceKind.YFINANCE,
        SourceKind.SEC_EDGAR,
        SourceKind.EARNINGS_TRANSCRIPT_NLP,
    }
)


@dataclass
class BacktestRow:
    as_of: date
    action: str
    statuses: dict[str, str] = field(default_factory=dict)
    values: dict[str, float | None] = field(default_factory=dict)


def run_backtest(
    risk: Risk, start: date, end: date, step_days: int = 7
) -> list[BacktestRow]:
    if start > end:
        raise ValueError(f"start {start} is after end {end}")
    if step_days < 1:
        raise ValueError("step_days must be >= 1")

    rows: list[BacktestRow] = []
    d = start
    while d <= end:
        verdicts = _evaluate_as_of(risk, d)
        decision = apply_rule_of_three(risk.triggers, verdicts)
        row = BacktestRow(as_of=d, action=decision.action)
        for v in verdicts:
            row.statuses[v.trigger_id] = v.status.value
            value = None
            if v.reading is not None:
                raw = (
                    v.reading.display_value
                    if v.reading.display_value is not None
                    else v.reading.value
                )
                if isinstance(raw, (int, float)) and raw == raw:
                    value = float(raw)
            row.values[v.trigger_id] = value
        rows.append(row)
        d += timedelta(days=step_days)
    return rows


def _evaluate_as_of(risk: Risk, as_of: date) -> list[Verdict]:
    verdicts: list[Verdict] = []
    for trigger in risk.triggers:
        if trigger.source not in BACKTESTABLE_SOURCES:
            verdicts.append(
                Verdict(
                    trigger_id=trigger.id,
                    status=Status.UNKNOWN,
                    rationale=(
                        f"source {trigger.source.value} not backtestable "
                        "(cannot reproduce a historical reading)"
                    ),
                )
            )
            continue
        try:
            source = get_source(trigger.source, thesis_name=risk.name)
            reading = source.fetch(trigger, as_of=as_of)
        except (SourceUnavailable, FetchError) as exc:
            logger.warning("backtest fetch failed %s @ %s: %s", trigger.id, as_of, exc)
            reading = None
        except Exception as exc:  # noqa: BLE001 - keep the sweep alive
            logger.exception("backtest unexpected error %s @ %s: %s", trigger.id, as_of, exc)
            reading = None
        if reading is None:
            verdicts.append(
                Verdict(
                    trigger_id=trigger.id,
                    status=Status.UNKNOWN,
                    rationale="fetch failed for historical as_of",
                )
            )
        else:
            verdicts.append(evaluate(trigger, reading))
    return verdicts


def write_csv(rows: list[BacktestRow], risk: Risk, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    trigger_ids = [t.id for t in risk.triggers]
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        header = ["as_of", "action"]
        for tid in trigger_ids:
            header += [f"{tid}_status", f"{tid}_value"]
        writer.writerow(header)
        for row in rows:
            line: list = [row.as_of.isoformat(), row.action]
            for tid in trigger_ids:
                line += [row.statuses.get(tid, ""), row.values.get(tid, "")]
            writer.writerow(line)
    return out_path


def summarize(rows: list[BacktestRow]) -> str:
    """Human-readable action-transition summary."""
    if not rows:
        return "(no backtest rows)"
    lines = [f"{len(rows)} evaluations from {rows[0].as_of} to {rows[-1].as_of}"]
    prev = None
    for row in rows:
        if row.action != prev:
            lines.append(f"{row.as_of}: action -> {row.action}")
            prev = row.action
    n_unknown_only = sum(
        1 for r in rows if r.statuses and all(s == "unknown" for s in r.statuses.values())
    )
    if n_unknown_only:
        lines.append(
            f"note: {n_unknown_only}/{len(rows)} dates had every trigger UNKNOWN "
            "(non-backtestable sources or fetch failures)"
        )
    return "\n".join(lines)
