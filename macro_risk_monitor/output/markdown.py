"""Persist raw LLM markdown for debugging."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def write_raw_markdown(out_dir: Path, risk_name: str, content: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    p = out_dir / f"{stamp}-{risk_name}.md"
    p.write_text(content, encoding="utf-8")
    return p
