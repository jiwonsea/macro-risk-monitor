"""Derived series: the difference of two other series.

Trigger ``series`` syntax: ``"<source>:<series> - <source>:<series>"``, e.g.
``"ecos:817Y002/D/010210000 - fred:DGS10"`` (한·미 10년물 금리차, %p).

Each leg is fetched through its own DataSource, so caching and credentials are
inherited. ``as_of`` is the older of the two leg dates so the spread never
looks fresher than its stalest input; both leg readings are kept in ``raw`` for
the citation verifier.
"""

from __future__ import annotations

import re
from datetime import date

from ..schemas import Reading, SourceKind, Threshold, Trigger
from .base import DataSource, FetchError

_LEG = r"\s*([a-z_]+)\s*:\s*([^\s].*?)\s*"
_PAT = re.compile(rf"^{_LEG}-{_LEG}$")


def parse_legs(series: str) -> tuple[tuple[SourceKind, str], tuple[SourceKind, str]]:
    m = _PAT.match(series or "")
    if not m:
        raise FetchError(f"derived series must look like 'src:A - src:B', got {series!r}")
    try:
        a = (SourceKind(m.group(1)), m.group(2))
        b = (SourceKind(m.group(3)), m.group(4))
    except ValueError as exc:
        raise FetchError(f"unknown source in derived series {series!r}: {exc}") from exc
    if SourceKind.DERIVED in (a[0], b[0]):
        raise FetchError("nested derived series are not supported")
    return a, b


class DerivedSource(DataSource):
    name = "derived"

    def __init__(self, resolver):
        # resolver(kind) -> DataSource ; injected to avoid a registry import cycle
        self._resolve = resolver

    def fetch(self, trigger: Trigger, as_of: date | None = None) -> Reading:
        (ka, sa), (kb, sb) = parse_legs(trigger.series or "")
        legs = []
        for kind, series in ((ka, sa), (kb, sb)):
            leg_trigger = Trigger(
                id=f"{trigger.id}__{kind.value}",
                category=trigger.category,
                source=kind,
                series=series,
                threshold=Threshold(),
            )
            reading = self._resolve(kind).fetch(leg_trigger, as_of)
            if not isinstance(reading.value, (int, float)):
                raise FetchError(f"derived leg {kind.value}:{series} is non-numeric")
            legs.append(reading)
        a, b = legs
        dates = [d for d in (a.as_of, b.as_of) if d is not None]
        return Reading(
            trigger_id=trigger.id,
            value=round(float(a.value) - float(b.value), 6),
            as_of=min(dates) if dates else None,
            source_url=f"{a.source_url} | {b.source_url}",
            raw={
                "series": trigger.series,
                "legs": [
                    {"series": sa, "value": a.value, "as_of": str(a.as_of)},
                    {"series": sb, "value": b.value, "as_of": str(b.as_of)},
                ],
            },
        )
