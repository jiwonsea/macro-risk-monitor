"""Load a JSON snapshot of FRED/ECOS observations into the source caches.

Use when the runtime has no outbound network but the data could be collected
elsewhere (e.g. a browser session). Snapshot format::

    {"collected_at": "...", "fred": {"DGS10": [["2026-10-01", "5.24"], ...]},
     "ecos": {"817Y002/D/010210000": [["20261002", "4.365", "국고채(10년)", "연%"], ...]}}

The cache files are written for ``--end`` (default: today) so the pipeline's
normal fetch path picks them up and no source code is bypassed.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from macro_risk_monitor import config as cfg


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot", type=Path)
    ap.add_argument("--end", type=date.fromisoformat, default=date.today())
    a = ap.parse_args()
    snap = json.loads(a.snapshot.read_text(encoding="utf-8"))
    n = 0
    for sid, rows in snap.get("fred", {}).items():
        obs = [{"date": d, "value": v} for d, v in sorted(rows, reverse=True)]
        (cfg.FRED_CACHE_DIR / f"{sid}_{a.end.isoformat()}.json").write_text(
            json.dumps({"observations": obs}), encoding="utf-8")
        n += 1
    for sid, rows in snap.get("ecos", {}).items():
        payload = {"StatisticSearch": {"list_total_count": len(rows), "row": [
            {"TIME": r[0], "DATA_VALUE": r[1], "ITEM_NAME1": r[2] if len(r) > 2 else None,
             "UNIT_NAME": r[3] if len(r) > 3 else None} for r in rows]}}
        (cfg.ECOS_CACHE_DIR / f"{sid.replace('/', '_')}_{a.end.isoformat()}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        n += 1
    print(f"loaded {n} series into cache for end={a.end}")


if __name__ == "__main__":
    main()
