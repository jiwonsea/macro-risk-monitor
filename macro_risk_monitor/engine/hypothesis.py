"""YAML -> Risk loader and validator."""

from __future__ import annotations

from pathlib import Path

import yaml

from ..schemas import Risk


def load_risk(path: str | Path) -> Risk:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"thesis YAML not found: {p}")
    with p.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return Risk.model_validate(data)
