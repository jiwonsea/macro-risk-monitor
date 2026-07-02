"""Evaluate a Reading against a Trigger's threshold string into a Status.

Threshold strings supported in Phase 1 (numeric):
    ">= 4.5"   ">4.5"   "<= -10"   "< -10"   "== 0"   "!= 0"
    "100~130"          (inclusive range)

Non-numeric thresholds (e.g. "2개사 동시 'rationalize'") cannot be auto-evaluated
in Phase 1 and return Status.UNKNOWN with the threshold echoed back as the
rationale; the LLM layer reads the rationale and explains the qualitative state
in the report.
"""

from __future__ import annotations

import logging
import math
import re

from ..schemas import Reading, Status, Threshold, Trigger, Verdict
from .units import can_convert, canonical_unit, convert

logger = logging.getLogger(__name__)


class ThresholdParseError(ValueError):
    """Raised when a threshold string is malformed (not when it's qualitative)."""


_NUMERIC_PAT = re.compile(r"^\s*(==|!=|>=|<=|>|<)\s*(-?\d+(?:\.\d+)?)\s*$")
_RANGE_PAT = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*~\s*(-?\d+(?:\.\d+)?)\s*$")


def evaluate(trigger: Trigger, reading: Reading | None) -> Verdict:
    """Return a Verdict comparing reading.value against trigger.threshold tiers.

    Evaluation order: red > yellow > green. The first matching tier wins so
    overlapping numeric thresholds behave predictably (most severe first).
    """

    if reading is None or reading.value is None:
        return Verdict(
            trigger_id=trigger.id,
            status=Status.UNKNOWN,
            reading=reading,
            rationale="reading unavailable",
        )
    if isinstance(reading.value, float) and math.isnan(reading.value):
        # NaN compares False against every tier, which would otherwise fall
        # through to the implicit-GREEN branch — a false all-clear.
        return Verdict(
            trigger_id=trigger.id,
            status=Status.UNKNOWN,
            reading=reading,
            rationale="reading is NaN",
        )

    value = reading.value
    display_value: float | str | None = None
    if isinstance(value, (int, float)):
        source_unit = _source_unit(reading)
        source_canon = canonical_unit(source_unit)
        target_canon = canonical_unit(trigger.unit)
        if source_canon and target_canon and source_canon != target_canon:
            if can_convert(source_unit, trigger.unit):
                display_value = convert(float(value), source_unit, trigger.unit)
                value = display_value
            else:
                # convert() would return the value unchanged for unsupported
                # pairs (e.g. percent -> index); don't pretend it converted.
                logger.warning(
                    "no conversion rule for %s: source=%r target=%r — comparing raw value",
                    trigger.id,
                    source_unit,
                    trigger.unit,
                )
        elif source_unit and trigger.unit and not (source_canon and target_canon):
            logger.warning(
                "unit conversion skipped for %s: source=%r target=%r",
                trigger.id,
                source_unit,
                trigger.unit,
            )
    if display_value is not None:
        reading.display_value = display_value

    for tier, status in (
        (trigger.threshold.red, Status.RED),
        (trigger.threshold.yellow, Status.YELLOW),
        (trigger.threshold.green, Status.GREEN),
    ):
        if tier is None:
            continue
        result = _match(tier, value)
        if result is None:
            # Qualitative threshold — defer to LLM, but still echo
            continue
        if result:
            return Verdict(
                trigger_id=trigger.id,
                status=status,
                reading=reading,
                rationale=f"value={value} matches {status.value} tier '{tier}'",
            )

    # Numeric thresholds all defined but none matched -> implicit GREEN
    if all(
        _is_numeric_pattern(t)
        for t in (trigger.threshold.red, trigger.threshold.yellow)
        if t is not None
    ) and (trigger.threshold.red or trigger.threshold.yellow):
        return Verdict(
            trigger_id=trigger.id,
            status=Status.GREEN,
            reading=reading,
            rationale=f"value={value} below all numeric warning tiers",
        )

    # Qualitative-only thresholds: cannot auto-evaluate
    return Verdict(
        trigger_id=trigger.id,
        status=Status.UNKNOWN,
        reading=reading,
        rationale=f"qualitative threshold; value={value}",
    )


def _match(tier_str: str, value: float | str) -> bool | None:
    """Return True/False if comparable numerically, None if qualitative."""

    if not isinstance(value, (int, float)):
        return None

    m = _NUMERIC_PAT.match(tier_str)
    if m:
        op, num_str = m.group(1), m.group(2)
        num = float(num_str)
        if op == ">":
            return value > num
        if op == ">=":
            return value >= num
        if op == "<":
            return value < num
        if op == "<=":
            return value <= num
        if op == "==":
            return value == num
        if op == "!=":
            return value != num
        raise ThresholdParseError(f"unsupported op {op!r} in threshold")

    m = _RANGE_PAT.match(tier_str)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        if lo > hi:
            lo, hi = hi, lo
        return lo <= value <= hi

    return None


def _is_numeric_pattern(tier_str: str | None) -> bool:
    if tier_str is None:
        return False
    return bool(_NUMERIC_PAT.match(tier_str) or _RANGE_PAT.match(tier_str))


def _source_unit(reading: Reading) -> str | None:
    if not reading.raw:
        return None
    return reading.raw.get("fred_units") or reading.raw.get("unit")


__all__ = ["evaluate", "ThresholdParseError", "Threshold"]
