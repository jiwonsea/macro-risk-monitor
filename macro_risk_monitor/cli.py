"""Command-line entry: `run` (YAML thesis) and `analyze` (ad-hoc text).

Examples:
    python -m macro_risk_monitor.cli run theses/ai_circular_revenue.yaml
    python -m macro_risk_monitor.cli analyze "미국 10년물 4.5% 돌파 → 모기지·회사채 spillover"
    python -m macro_risk_monitor.cli pdf reports/html/2026-05-26-us_long_end_yield.html
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

import yaml

# Korean Windows console defaults to cp949; force UTF-8 so log output and
# print() with em-dash etc. don't crash.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from . import config as cfg
from .ai.data_selector import (
    manual_override_scaffold,
    select_data,
    selection_to_payload,
)
from .ai.patch import apply_patch, dump_patch, load_patch, render_diff
from .ai.risk_parser import parse_risk
from .ai.review_parser import parse_feedback
from .ai.reviewer import write_review_handoff
from .engine.hypothesis import load_risk
from .output.html import default_html_path
from .output.pdf import html_to_pdf
from .pipeline import run_pipeline
from .schemas import Risk

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="macro-risk", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="run a YAML-defined risk thesis")
    p_run.add_argument("thesis", type=Path)
    p_run.add_argument("--output", type=Path, default=None)
    p_run.add_argument("--skip-llm", action="store_true")
    p_run.add_argument("--pdf", action="store_true", help="also render PDF")
    p_run.add_argument(
        "--as-of",
        dest="as_of",
        default=None,
        metavar="YYYY-MM-DD",
        help=(
            "replay a historical date: backtestable sources only "
            "(others UNKNOWN); state/history not updated"
        ),
    )

    p_an = sub.add_parser("analyze", help="ad-hoc natural-language risk input")
    p_an.add_argument("text", help="risk hypothesis in one to a few sentences")
    p_an.add_argument("--output", type=Path, default=None)
    p_an.add_argument("--save-thesis", type=Path, default=None)
    p_an.add_argument("--skip-llm", action="store_true")
    p_an.add_argument("--yes", action="store_true", help="skip interactive confirmation")
    p_an.add_argument("--pdf", action="store_true")

    p_pdf = sub.add_parser("pdf", help="convert an existing HTML report to PDF")
    p_pdf.add_argument("html_path", type=Path)
    p_pdf.add_argument("--output", type=Path, default=None)

    p_review = sub.add_parser("review-thesis", help="generate a thesis review handoff")
    p_review.add_argument("name", help="thesis name, e.g. ai_circular_revenue")
    p_review.add_argument("--out-dir", type=Path, default=Path("notes/codex_handoffs"))

    p_apply = sub.add_parser("apply-review", help="parse review feedback and render/apply a patch")
    p_apply.add_argument("name", help="thesis name, e.g. ai_circular_revenue")
    src = p_apply.add_mutually_exclusive_group(required=True)
    src.add_argument("--feedback", type=Path, help="review feedback markdown")
    src.add_argument("--patch", type=Path, help="staged review patch YAML")
    p_apply.add_argument("--apply", action="store_true", help="write changes instead of dry-run diff")

    sub.add_parser("dashboard", help="launch the read-only Streamlit dashboard")

    p_bt = sub.add_parser(
        "backtest",
        help="replay a thesis over a historical date range (no LLM)",
    )
    p_bt.add_argument("thesis", type=Path)
    p_bt.add_argument("--start", required=True, help="YYYY-MM-DD")
    p_bt.add_argument("--end", required=True, help="YYYY-MM-DD")
    p_bt.add_argument("--step", type=int, default=7, help="days between evaluations (default 7)")
    p_bt.add_argument("--output", type=Path, default=None, help="CSV path; default reports/backtest/{name}.csv")

    p_draft = sub.add_parser(
        "draft-thesis",
        help="hypothesis -> auto-select & verify data sources -> thesis YAML",
    )
    p_draft.add_argument("hypothesis", help="risk hypothesis in natural language")
    p_draft.add_argument("--name", default=None, help="thesis name (snake_case); default from LLM draft")
    p_draft.add_argument("--out", type=Path, default=None, help="output YAML path; default theses/{name}.yaml")
    p_draft.add_argument("--no-codex", action="store_true", help="skip the Codex multi-model discussion")
    p_draft.add_argument("--max-repair", type=int, default=3, help="max repair rounds for failed series")
    p_draft.add_argument("--yes", action="store_true", help="skip interactive confirmation")

    args = parser.parse_args(argv)

    if args.command == "run":
        return _cmd_run(args)
    if args.command == "analyze":
        return _cmd_analyze(args)
    if args.command == "pdf":
        return _cmd_pdf(args)
    if args.command == "review-thesis":
        return _cmd_review_thesis(args)
    if args.command == "apply-review":
        return _cmd_apply_review(args)
    if args.command == "draft-thesis":
        return _cmd_draft_thesis(args)
    if args.command == "dashboard":
        return _cmd_dashboard()
    if args.command == "backtest":
        return _cmd_backtest(args)
    parser.error("unreachable")
    return 2


def _cmd_run(args: argparse.Namespace) -> int:
    from .pipeline.orchestrator import report_stamp

    risk = load_risk(args.thesis)
    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    report = run_pipeline(
        risk, out_html=args.output, skip_llm=args.skip_llm, as_of=as_of
    )
    if as_of is not None:
        print(f"as_of: {as_of} (historical replay — state/history not updated)")
    print(f"action: {report.decision.action}")
    print(f"summary: {report.decision.summary}")
    if args.pdf:
        html_path = args.output or default_html_path(risk.name, report_stamp(report))
        pdf = html_to_pdf(html_path)
        if pdf:
            print(f"pdf: {pdf}")
    return 0


def _cmd_analyze(args: argparse.Namespace) -> int:
    risk = parse_risk(args.text)
    print(f"Drafted risk skeleton: {risk.name} — {risk.title}")
    print(f"Triggers ({len(risk.triggers)}):")
    for t in risk.triggers:
        print(f"  - {t.id} [{t.category.value}] source={t.source.value}")
    if args.save_thesis:
        _save_yaml(risk, args.save_thesis)
        print(f"saved: {args.save_thesis}")
    if not args.yes:
        ans = input("Proceed with pipeline? [y/N] ").strip().lower()
        if ans != "y":
            print("aborted.")
            return 0
    report = run_pipeline(risk, out_html=args.output, skip_llm=args.skip_llm)
    print(f"action: {report.decision.action}")
    if args.pdf:
        html_path = args.output or default_html_path(risk.name, report.generated_at)
        pdf = html_to_pdf(html_path)
        if pdf:
            print(f"pdf: {pdf}")
    return 0


def _cmd_pdf(args: argparse.Namespace) -> int:
    pdf = html_to_pdf(args.html_path, args.output)
    if pdf is None:
        print("PDF render failed (Chrome unavailable?)", file=sys.stderr)
        return 1
    print(f"pdf: {pdf}")
    return 0


def _cmd_review_thesis(args: argparse.Namespace) -> int:
    path = write_review_handoff(args.name, args.out_dir)
    print(f"Generated: {path.relative_to(cfg.BASE_DIR)}")
    print("Next: paste this file to Codex, save reply as")
    print(f"      notes/codex_handoffs/{path.stem}_feedback.md")
    return 0


def _cmd_apply_review(args: argparse.Namespace) -> int:
    risk_path = cfg.THESES_DIR / f"{args.name}.yaml"
    override_path = cfg.BASE_DIR / "data" / "manual_override" / f"{args.name}.yaml"
    if args.patch:
        patch = load_patch(args.patch)
        patch_path = args.patch
    else:
        md_text = args.feedback.read_text(encoding="utf-8")
        patch = parse_feedback(md_text, args.name)
        patch_path = (
            cfg.BASE_DIR
            / "notes"
            / "codex_handoffs"
            / f"{patch.review_date.isoformat()}_{args.name}_review_patch.yaml"
        )
        dump_patch(patch, patch_path)

    risk_diff, override_diff = render_diff(patch, risk_path, override_path)
    print(f"=== diff: {risk_path.relative_to(cfg.BASE_DIR)} ===")
    print(risk_diff or "(no changes)")
    print(f"=== diff: {override_path.relative_to(cfg.BASE_DIR)} ===")
    print(override_diff or "(no changes)")

    if args.apply:
        apply_patch(patch, risk_path, override_path)
        print(f"Applied patch: {patch_path.relative_to(cfg.BASE_DIR)}")
    else:
        print(f"Patch staged at: {patch_path.relative_to(cfg.BASE_DIR)}")
        print("Re-run with --apply to write changes.")
    return 0


def _cmd_draft_thesis(args: argparse.Namespace) -> int:
    sel = select_data(
        args.hypothesis,
        use_codex=not args.no_codex,
        max_repair_rounds=args.max_repair,
    )
    if args.name:
        sel.name = args.name

    print(f"Drafted thesis: {sel.name} — {sel.title}")
    print(f"Codex discussion: {'yes' if sel.codex_used else 'no (skipped/unavailable)'}")
    print(f"\nResolved triggers ({len(sel.triggers)}):")
    print(_render_trigger_table(sel))

    ok = sum(1 for t in sel.triggers if t.status == "OK")
    manual = sum(1 for t in sel.triggers if t.status == "MANUAL")
    unverified = sum(1 for t in sel.triggers if t.status == "UNVERIFIED")
    print(f"\n  OK={ok}  MANUAL={manual}  UNVERIFIED={unverified}")
    print("  Note: thresholds are scaffolded as TBD — set them yourself (LLM does not decide thresholds).")

    payload = selection_to_payload(sel)
    try:
        Risk.model_validate(payload)  # fail before writing if the draft is malformed
    except Exception as exc:  # noqa: BLE001 — surface validation error to the user
        print(f"\nDraft failed schema validation: {exc}", file=sys.stderr)
        return 1

    out_path = args.out or cfg.THESES_DIR / f"{sel.name}.yaml"
    if not args.yes:
        ans = input(f"\nWrite thesis to {out_path}? [y/N] ").strip().lower()
        if ans != "y":
            print("aborted.")
            return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(payload, fh, allow_unicode=True, sort_keys=False)
    print(f"wrote: {out_path}")

    scaffold = manual_override_scaffold(sel)
    if scaffold:
        ov_path = cfg.BASE_DIR / "data" / "manual_override" / f"{sel.name}.yaml"
        ov_path.parent.mkdir(parents=True, exist_ok=True)
        if ov_path.exists():
            print(f"manual_override file already exists, not overwriting: {ov_path}")
        else:
            with ov_path.open("w", encoding="utf-8") as fh:
                yaml.safe_dump(scaffold, fh, allow_unicode=True, sort_keys=False)
            print(f"wrote manual_override scaffold ({len(scaffold)} keys): {ov_path}")

    print("\nNext: fill thresholds in the thesis YAML, then run:")
    print(f"      python -m macro_risk_monitor.cli run {out_path}")
    return 0


def _render_trigger_table(sel) -> str:
    rows = []
    for t in sel.triggers:
        p = t.probe
        latest = ""
        if p and p.ok:
            latest = f"{p.latest_value}"
            if p.as_of:
                latest += f" ({p.as_of.isoformat()})"
        units = (p.units if p and p.units else t.unit) or ""
        rows.append(
            f"  [{t.status:<10}] {t.category:<10} {t.source}/{t.series}"
            f"{('  units=' + units) if units else ''}"
            f"{('  latest=' + latest) if latest else ''}"
        )
        if t.rationale:
            rows.append(f"               why: {t.rationale}")
    return "\n".join(rows)


def _save_yaml(risk, path: Path) -> None:
    payload = risk.model_dump(mode="json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(payload, fh, allow_unicode=True, sort_keys=False)


def _cmd_backtest(args: argparse.Namespace) -> int:
    from datetime import date as date_cls

    from .pipeline.backtest import run_backtest, summarize, write_csv

    risk = load_risk(args.thesis)
    start = date_cls.fromisoformat(args.start)
    end = date_cls.fromisoformat(args.end)
    rows = run_backtest(risk, start, end, step_days=args.step)
    out = args.output or (cfg.REPORTS_DIR / "backtest" / f"{risk.name}.csv")
    write_csv(rows, risk, out)
    print(summarize(rows))
    print(f"csv: {out}")
    return 0


def _cmd_dashboard() -> int:
    """Launch streamlit with the dashboard module (read-only viewer)."""
    import subprocess

    try:
        import streamlit  # noqa: F401
    except ImportError:
        print(
            "streamlit not installed; install with "
            "`pip install 'macro-risk-monitor[ui]'`",
            file=sys.stderr,
        )
        return 1
    app = Path(__file__).resolve().parent / "ui" / "dashboard.py"
    return subprocess.call([sys.executable, "-m", "streamlit", "run", str(app)])


if __name__ == "__main__":
    raise SystemExit(main())
