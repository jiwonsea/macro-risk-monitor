"""End-to-end pipeline: Risk -> Readings -> Verdicts -> Decision -> Report.

The orchestrator is the only place that knows how all four layers connect.
Each layer is independently testable in isolation.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from .. import config as cfg
from ..ai.analyzer import analyze
from ..ai.verifier import verify_citations
from ..engine import evaluate, apply_rule_of_three
from ..engine import thesis_state
from ..output.html import default_html_path, render_report
from ..output.markdown import write_raw_markdown
from ..schemas import Reading, Report, Risk, Status, Verdict
from ..sources import FetchError, SourceUnavailable, get_source

logger = logging.getLogger(__name__)


def run_pipeline(
    risk: Risk,
    out_html: Path | None = None,
    skip_llm: bool = False,
) -> Report:
    """Run the full pipeline and write the HTML report. Returns the Report."""

    verdicts = _fetch_and_evaluate(risk)
    decision = apply_rule_of_three(risk.triggers, verdicts)

    if skip_llm:
        analysis_md = "(LLM 분석 건너뜀)"
        llm_model = "skipped"
    else:
        analysis_md, llm_model = analyze(risk, verdicts)

    citation = verify_citations(analysis_md, risk, verdicts)
    if not citation.passed:
        logger.warning(
            "citation check failed for %s: %d ungrounded tokens",
            risk.name,
            len(citation.ungrounded),
        )

    report = Report(
        risk=risk,
        verdicts=verdicts,
        decision=decision,
        llm_analysis_md=analysis_md,
        citation_check=citation,
        generated_at=datetime.now(),
        llm_model=llm_model,
    )

    state_dir = cfg.CACHE_DIR / "state"
    previous = thesis_state.load_previous(state_dir, risk.name)
    diff = thesis_state.diff(previous, verdicts)
    thesis_state.save(state_dir, risk.name, verdicts)

    html_path = out_html or default_html_path(risk.name, report.generated_at)
    render_report(report, html_path, state_diff=diff)
    write_raw_markdown(cfg.REPORTS_RAW_DIR, risk.name, analysis_md)

    logger.info("report ready: %s (action=%s)", html_path, decision.action)
    return report


def _fetch_and_evaluate(risk: Risk) -> list[Verdict]:
    verdicts: list[Verdict] = []
    for trigger in risk.triggers:
        try:
            source = get_source(trigger.source)
            reading: Reading | None = source.fetch(trigger)
        except SourceUnavailable as exc:
            logger.warning("source unavailable for %s: %s", trigger.id, exc)
            reading = None
        except FetchError as exc:
            logger.error("fetch failed for %s: %s", trigger.id, exc)
            reading = None
        except Exception as exc:  # noqa: BLE001 — defensive: never crash the pipeline
            logger.exception("unexpected fetch error for %s: %s", trigger.id, exc)
            reading = None
        if reading is None:
            verdicts.append(
                Verdict(
                    trigger_id=trigger.id,
                    status=Status.UNKNOWN,
                    rationale="source unavailable or fetch failed",
                )
            )
        else:
            verdicts.append(evaluate(trigger, reading))
    return verdicts
