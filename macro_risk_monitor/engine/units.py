"""Small unit conversion helpers used during trigger evaluation."""

from __future__ import annotations

KNOWN_UNITS = {"percent", "pct", "%", "bps", "bp", "basis_points", "index", "usd", "count"}

_ALIASES = {
    "percent": "percent",
    "pct": "percent",
    "%": "percent",
    "bps": "bps",
    "bp": "bps",
    "basis_points": "bps",
    "basis points": "bps",
    "index": "index",
    "usd": "usd",
    "count": "count",
}


def canonical_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    return _ALIASES.get(str(unit).strip().lower())


_CONVERTIBLE_PAIRS = {("percent", "bps"), ("bps", "percent")}


def can_convert(source: str | None, target: str | None) -> bool:
    """True when convert() can produce a genuinely converted value."""
    s, t = canonical_unit(source), canonical_unit(target)
    if s is None or t is None:
        return False
    return s == t or (s, t) in _CONVERTIBLE_PAIRS


def convert(value: float, source: str | None, target: str | None) -> float:
    source_unit = canonical_unit(source)
    target_unit = canonical_unit(target)
    if source_unit is None or target_unit is None or source_unit == target_unit:
        return value
    if source_unit == "percent" and target_unit == "bps":
        return value * 100
    if source_unit == "bps" and target_unit == "percent":
        return value / 100
    return value
