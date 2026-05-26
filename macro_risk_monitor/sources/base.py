"""Abstract data source contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, timedelta

from ..schemas import Reading, Trigger


class FetchError(RuntimeError):
    """Source contacted but returned an error or unparseable response."""


class SourceUnavailable(RuntimeError):
    """Source requires credentials or a dependency that is missing.

    The orchestrator treats this as Status.UNKNOWN rather than a hard failure
    so the rest of the report can still render.
    """


class DataSource(ABC):
    """All sources implement fetch(trigger, as_of) -> Reading."""

    name: str

    @abstractmethod
    def fetch(self, trigger: Trigger, as_of: date | None = None) -> Reading:
        """Return the most recent Reading <= as_of for the trigger's series."""

    @staticmethod
    def default_window(as_of: date | None, days: int = 365) -> tuple[date, date]:
        end = as_of or date.today()
        return end - timedelta(days=days), end
