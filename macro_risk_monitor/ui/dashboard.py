"""Streamlit dashboard: read-only viewer over theses + verdict snapshots.

Layer contract: the UI reads *artifacts* (thesis YAML, .cache/state snapshots,
reports/html) and never runs the pipeline itself — running stays in the CLI /
daily cron so `run` remains the single mutation path (CLAUDE.md architecture
invariant). Launch with:

    streamlit run macro_risk_monitor/ui/dashboard.py
    # or
    macro-risk dashboard
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .. import config as cfg
from ..engine.hypothesis import load_risk
from ..engine.thesis_state import load_history
from ..schemas import Risk, Status

_STATUS_ICON = {
    Status.RED: "🔴",
    Status.YELLOW: "🟡",
    Status.GREEN: "🟢",
    Status.UNKNOWN: "⚪",
}


# ---------------------------------------------------------------- data prep
def list_theses(theses_dir: Path | None = None) -> list[Path]:
    d = theses_dir or cfg.THESES_DIR
    return sorted(d.glob("*.yaml"))


def load_state(risk_name: str, state_dir: Path | None = None) -> dict:
    """Return {"generated_at": str|None, "verdicts": {trigger_id: Status}}."""
    d = state_dir or (cfg.CACHE_DIR / "state")
    p = d / f"{risk_name}.json"
    if not p.exists():
        return {"generated_at": None, "verdicts": {}}
    payload = json.loads(p.read_text(encoding="utf-8"))
    verdicts = {}
    for k, v in payload.get("verdicts", {}).items():
        try:
            verdicts[k] = Status(v)
        except ValueError:
            verdicts[k] = Status.UNKNOWN
    return {"generated_at": payload.get("generated_at"), "verdicts": verdicts}


def latest_report(risk_name: str, html_dir: Path | None = None) -> Path | None:
    d = html_dir or cfg.REPORTS_HTML_DIR
    candidates = sorted(d.glob(f"*-{risk_name}.html"))
    return candidates[-1] if candidates else None


def trigger_rows(risk: Risk, verdicts: dict[str, Status]) -> list[dict]:
    rows = []
    for t in risk.triggers:
        status = verdicts.get(t.id, Status.UNKNOWN)
        rows.append(
            {
                "status": f"{_STATUS_ICON[status]} {status.value}",
                "id": t.id,
                "category": t.category.value,
                "source": t.source.value,
                "series": t.series or "—",
                "red": t.threshold.red or "—",
                "yellow": t.threshold.yellow or "—",
                "green": t.threshold.green or "—",
            }
        )
    return rows


def status_counts(verdicts: dict[str, Status]) -> dict[str, int]:
    out = {s.value: 0 for s in Status}
    for s in verdicts.values():
        out[s.value] += 1
    return out


def history_frame(risk_name: str, state_dir: Path | None = None) -> dict:
    """Reshape history JSONL into chart-ready columns.

    Returns {"timestamps": [str], "values": {trigger_id: [float|None]},
             "statuses": {trigger_id: [str]}} — aligned by run.
    """
    d = state_dir or (cfg.CACHE_DIR / "state")
    entries = load_history(d, risk_name)
    timestamps: list[str] = []
    values: dict[str, list] = {}
    statuses: dict[str, list] = {}
    ids: list[str] = []
    for e in entries:
        for tid in e.get("verdicts", {}):
            if tid not in ids:
                ids.append(tid)
    for e in entries:
        timestamps.append(e.get("generated_at") or "")
        verdicts = e.get("verdicts", {})
        for tid in ids:
            v = verdicts.get(tid) or {}
            values.setdefault(tid, []).append(v.get("value"))
            statuses.setdefault(tid, []).append(v.get("status", "unknown"))
    return {"timestamps": timestamps, "values": values, "statuses": statuses}


def status_timeline_rows(frame: dict) -> list[dict]:
    """One row per trigger; one icon-cell per run (oldest -> newest)."""
    rows = []
    for tid, sts in frame["statuses"].items():
        icons = "".join(
            _STATUS_ICON.get(_safe_status(s), "⚪") for s in sts
        )
        rows.append({"trigger": tid, "timeline": icons})
    return rows


def _safe_status(value: str) -> Status:
    try:
        return Status(value)
    except ValueError:
        return Status.UNKNOWN


# ---------------------------------------------------------------- streamlit
def main() -> None:  # pragma: no cover - thin streamlit glue
    import streamlit as st

    st.set_page_config(page_title="macro-risk-monitor", layout="wide")
    st.title("macro-risk-monitor")

    theses = list_theses()
    if not theses:
        st.warning(f"No thesis YAML found in {cfg.THESES_DIR}")
        return

    names = [p.stem for p in theses]
    selected = st.sidebar.radio("Thesis", names)
    path = theses[names.index(selected)]

    try:
        risk = load_risk(path)
    except Exception as exc:  # noqa: BLE001 - show, do not crash the app
        st.error(f"failed to load {path.name}: {exc}")
        return

    state = load_state(risk.name)
    st.subheader(risk.title)
    st.markdown(risk.hypothesis)

    counts = status_counts(state["verdicts"])
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("RED", counts.get("red", 0))
    c2.metric("YELLOW", counts.get("yellow", 0))
    c3.metric("GREEN", counts.get("green", 0))
    c4.metric("UNKNOWN", counts.get("unknown", 0))
    c5.metric(
        "Last run",
        _short_ts(state["generated_at"]) if state["generated_at"] else "never",
    )

    st.dataframe(trigger_rows(risk, state["verdicts"]), use_container_width=True)

    if risk.critical_windows:
        st.subheader("Critical windows")
        for w in risk.critical_windows:
            line = f"- **{w.date.isoformat()}** — {w.event}"
            if w.rationale:
                line += f" ({w.rationale})"
            st.markdown(line)

    frame = history_frame(risk.name)
    if len(frame["timestamps"]) >= 2:
        st.subheader("History")
        st.dataframe(status_timeline_rows(frame), use_container_width=True)
        numeric_ids = [
            tid
            for tid, vals in frame["values"].items()
            if any(v is not None for v in vals)
        ]
        if numeric_ids:
            pick = st.selectbox("Trigger value trend", numeric_ids)
            st.line_chart(
                {
                    "value": [
                        v if v is not None else float("nan")
                        for v in frame["values"][pick]
                    ]
                }
            )

    report = latest_report(risk.name)
    if report:
        st.subheader("Latest report")
        st.components.v1.html(
            report.read_text(encoding="utf-8"), height=800, scrolling=True
        )
    else:
        st.info("No HTML report yet — run `macro-risk run theses/%s.yaml`" % risk.name)


def _short_ts(ts: str) -> str:
    try:
        return datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return ts


if __name__ == "__main__":
    main()
