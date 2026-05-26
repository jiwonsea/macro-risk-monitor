"""Cross-check that every number quoted in LLM markdown is grounded in Readings.

Heuristic: extract every numeric token from the markdown body (excluding
headers and code blocks), and check that each one appears (within tolerance)
either among the Reading.value set or among the trigger.threshold tier
numerics. Tokens that are pure year strings (1995~2099) or single-digit list
counters are ignored.

This is intentionally conservative — false positives are noisy but safer
than letting a hallucinated `30Y 5.42%` slip through.
"""

from __future__ import annotations

import re

from ..engine.trigger import _NUMERIC_PAT, _RANGE_PAT  # noqa: F401  (regex reuse not used directly)
from ..schemas import CitationCheck, Risk, Verdict


# Only treat as a citable number tokens that either have a decimal point
# or carry an explicit financial unit suffix. This excludes ordinals like
# "10년물" or list counters that would otherwise be flagged as ungrounded.
_NUM_TOKEN = re.compile(
    r"-?\d+\.\d+(?:%|bp|bps|\$|원|억|조)?"     # with decimal
    r"|-?\d+(?:%|bp|bps|\$|원|억|조)"          # or with mandatory unit
)
_YEAR = re.compile(r"^(?:19|20)\d{2}$")
_DEFAULT_TOLERANCE = 0.05


def verify_citations(
    markdown: str,
    risk: Risk,
    verdicts: list[Verdict],
    tolerance: float = _DEFAULT_TOLERANCE,
) -> CitationCheck:
    grounded_values: set[float] = set()
    for v in verdicts:
        if v.reading and isinstance(v.reading.value, (int, float)):
            grounded_values.add(float(v.reading.value))
    for t in risk.triggers:
        for tier in (t.threshold.red, t.threshold.yellow, t.threshold.green):
            grounded_values.update(_extract_numerics(tier or ""))

    body = _strip_code_and_headers(markdown)
    tokens = _NUM_TOKEN.findall(body)

    ungrounded: list[str] = []
    grounded_count = 0
    for tok in tokens:
        bare = tok.rstrip("%$bps원억조")
        if _YEAR.match(bare):
            continue
        try:
            num = float(bare)
        except ValueError:
            continue
        if _is_grounded(num, grounded_values, tolerance):
            grounded_count += 1
        else:
            ungrounded.append(tok)

    return CitationCheck(
        passed=not ungrounded,
        grounded_count=grounded_count,
        ungrounded=ungrounded[:20],  # cap to keep report concise
    )


def _strip_code_and_headers(md: str) -> str:
    md = re.sub(r"```.*?```", "", md, flags=re.DOTALL)
    md = re.sub(r"^#+ .*$", "", md, flags=re.MULTILINE)
    return md


def _extract_numerics(text: str) -> set[float]:
    out: set[float] = set()
    for tok in _NUM_TOKEN.findall(text):
        bare = tok.rstrip("%$bps원억조")
        try:
            out.add(float(bare))
        except ValueError:
            continue
    return out


def _is_grounded(num: float, anchors: set[float], tolerance: float) -> bool:
    if not anchors:
        return False
    for a in anchors:
        if a == 0:
            if abs(num) <= tolerance:
                return True
            continue
        if abs(num - a) / max(abs(a), 1.0) <= tolerance:
            return True
    return False
