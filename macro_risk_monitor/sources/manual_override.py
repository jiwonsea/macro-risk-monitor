"""Manual override source.

For triggers backed by paid data (Bloomberg CDS, Hiive secondary, DRAMeXchange)
or by qualitative judgement (policy status), the user records the latest
reading in `data/manual_override.yaml`. The file is gitignored if it
contains private credentials, but the default template ships with the
repo.

YAML shape:

    openai_secondary_premium_pct:
      value: -8.5
      as_of: 2026-05-15
      source_url: https://hiive.com/...
      note: |
        Series F preferred at $852B post-money mark.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from ..schemas import Reading, Trigger
from .base import DataSource, FetchError

logger = logging.getLogger(__name__)


class ManualOverrideSource(DataSource):
    name = "manual_override"

    def __init__(self, override_path: Path):
        self.override_path = override_path
        self._cache: dict[str, Any] | None = None

    def fetch(self, trigger: Trigger, as_of: date | None = None) -> Reading:
        data = self._load()
        key = trigger.series or trigger.id
        entry = data.get(key)
        if entry is None:
            raise FetchError(
                f"manual_override missing key '{key}' for trigger {trigger.id}; "
                f"add it to {self.override_path}"
            )
        value = entry.get("value")
        as_of_raw = entry.get("as_of")
        as_of_d = date.fromisoformat(as_of_raw) if isinstance(as_of_raw, str) else as_of_raw
        return Reading(
            trigger_id=trigger.id,
            value=value,
            as_of=as_of_d,
            source_url=entry.get("source_url"),
            raw=entry,
        )

    def _load(self) -> dict[str, Any]:
        if self._cache is not None:
            return self._cache
        if not self.override_path.exists():
            logger.warning("manual_override file missing: %s", self.override_path)
            self._cache = {}
            return self._cache
        with self.override_path.open(encoding="utf-8") as fh:
            self._cache = yaml.safe_load(fh) or {}
        return self._cache
