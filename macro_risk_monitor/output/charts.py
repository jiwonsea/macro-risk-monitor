"""Inline base64-PNG charts rendered with matplotlib."""

from __future__ import annotations

import base64
import io
import re
from collections.abc import Iterable, Mapping

from ..schemas import Status, Trigger, Verdict

_NUMERIC_PAT = re.compile(r"^\s*(?:==|!=|>=|<=|>|<)?\s*(-?\d+(?:\.\d+)?)\s*$")
_RANGE_PAT = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*~\s*(-?\d+(?:\.\d+)?)\s*$")


def render_trigger_bar(
    verdicts: Iterable[Verdict], triggers: Mapping[str, Trigger]
) -> str | None:
    """Return an inline PNG chart with one subplot per numeric trigger."""

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    rows: list[tuple[Verdict, float, Trigger | None]] = []
    for v in verdicts:
        if not v.reading:
            continue
        raw_value = (
            v.reading.display_value
            if v.reading.display_value is not None
            else v.reading.value
        )
        if not isinstance(raw_value, (int, float)):
            continue
        rows.append((v, float(raw_value), triggers.get(v.trigger_id)))
    if not rows:
        return None

    color_map = {
        Status.RED: "#c53030",
        Status.YELLOW: "#b7791f",
        Status.GREEN: "#2f855a",
        Status.UNKNOWN: "#718096",
    }
    nrows = len(rows)
    fig, axes = plt.subplots(nrows=nrows, ncols=1, figsize=(8.5, 1.6 * nrows + 0.8))
    if nrows == 1:
        axes = [axes]

    for ax, (verdict, value, trigger) in zip(axes, rows):
        ax.barh([verdict.trigger_id], [value], color=color_map.get(verdict.status, "#718096"))
        ax.set_title(verdict.trigger_id, loc="left", fontsize=9)
        ax.grid(True, axis="x", linestyle=":", alpha=0.4)
        ax.tick_params(axis="y", labelsize=8)
        ax.tick_params(axis="x", labelsize=8)
        ax.text(value, 0, f" {value:g}", va="center", fontsize=8)
        if trigger is not None:
            _draw_thresholds(ax, trigger)
            if trigger.unit:
                ax.set_xlabel(trigger.unit, fontsize=8)

    fig.suptitle("Trigger readings with thresholds", fontsize=11)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    payload = base64.b64encode(buf.getvalue()).decode("ascii")
    return (
        f'<div class="chart" data-subplots="{nrows}"><img alt="Trigger readings" '
        f'src="data:image/png;base64,{payload}"></div>'
    )


def _draw_thresholds(ax, trigger: Trigger) -> None:
    tiers = (
        ("red", trigger.threshold.red, "#c53030"),
        ("yellow", trigger.threshold.yellow, "#b7791f"),
        ("green", trigger.threshold.green, "#2f855a"),
    )
    for label, tier, color in tiers:
        threshold = _numeric_threshold(tier)
        if threshold is None:
            continue
        ax.axvline(threshold, color=color, linestyle="--", linewidth=1, alpha=0.8)
        ax.text(threshold, 0.35, label, rotation=90, color=color, fontsize=7, va="bottom")


def _numeric_threshold(tier_str: str | None) -> float | None:
    if not tier_str:
        return None
    m = _NUMERIC_PAT.match(tier_str)
    if m:
        return float(m.group(1))
    m = _RANGE_PAT.match(tier_str)
    if m:
        return float(m.group(1))
    return None
