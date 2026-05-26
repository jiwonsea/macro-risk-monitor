"""Persist verdict history per thesis so diff-from-previous-run is possible.

Stored at .cache/state/{risk_name}.json. On each run the orchestrator loads
the previous snapshot, then writes the new one after rendering. The diff
is surfaced in the HTML report's footer so the user sees "X went RED today".
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
