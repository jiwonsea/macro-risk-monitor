"""Persist verdict history per thesis so diff-from-previous-run is possible.

Two artifacts per thesis under .cache/state/:

- {risk_name}.json          — latest snapshot (used for the report footer diff)
- {risk_name}_history.jsonl — append-only run log (one JSON line per run with
  per-trigger status *and* numeric value) consumed by the dashboard trend
  charts and, later, backtesting.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..schemas import Status, Verdict


def load_previous(state_dir: Path, risk_name: str) -> dict[str, Status]:
    p = state_dir / f"{risk_name}.json"
    if not p.exists():
        return {}
    payload = json.loads(p.read_text(encoding="utf-8"))
    return {k: Status(v) for k, v in payload.get("verdicts", {}).items()}


def save(state_dir: Path, risk_name: str, verdicts: list[Verdict]) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    p = state_dir / f"{risk_name}.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "verdicts": {v.trigger_id: v.status.value for v in verdicts},
    }
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_history(state_dir: Path, risk_name: str, verdicts: list[Verdict]) -> None:
    """Append one JSONL line with per-trigger status and numeric value."""
    state_dir.mkdir(parents=True, exist_ok=True)
    p = state_dir / f"{risk_name}_history.jsonl"
    entry = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "verdicts": {v.trigger_id: _verdict_payload(v) for v in verdicts},
    }
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _verdict_payload(v: Verdict) -> dict:
    value = None
    if v.reading is not None:
        raw = v.reading.display_value if v.reading.display_value is not None else v.reading.value
        if isinstance(raw, (int, float)) and raw == raw:  # drop NaN
            value = float(raw)
    return {"status": v.status.value, "value": value}


def load_history(state_dir: Path, risk_name: str, limit: int | None = None) -> list[dict]:
    """Return parsed history entries (oldest first). Bad lines are skipped."""
    p = state_dir / f"{risk_name}_history.jsonl"
    if not p.exists():
        return []
    out: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict) and "verdicts" in entry:
            out.append(entry)
    return out[-limit:] if limit else out


def diff(
    previous: dict[str, Status], current: list[Verdict]
) -> list[tuple[str, Status, Status]]:
    """Return (trigger_id, old_status, new_status) for triggers that changed."""

    out: list[tuple[str, Status, Status]] = []
    for v in current:
        old = previous.get(v.trigger_id)
        if old is None or old != v.status:
            out.append((v.trigger_id, old or Status.UNKNOWN, v.status))
    return out
