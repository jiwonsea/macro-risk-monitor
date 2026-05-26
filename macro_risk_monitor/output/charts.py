"""Inline base64-PNG charts rendered with matplotlib.

Phase 1 chart set is intentionally small: a single bar chart of trigger
values vs RED threshold per risk. Matplotlib is optional — if not installed
the orchestrator omits the chart section gracefully.
"""

from __future__ import annotations

import base64
import io
import re
from typing import Iterable

from ..schemas import Status, Verdict


def render_trigger_bar(verdicts: Iterable[Verdict]) -> str | None:
    """Return a `<div class="chart">...<img src="data:image/png;base64,..."></div>` block.

    Returns None if matplotlib is not installed or there are no numeric values.
    """

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    rows: list[tuple[str, float, str]] = []
    for v in verdicts:
        if not v.reading or not isinstance(v.reading.value, (int, float)):
            continue
        rows.append((v.trigger_id, float(v.reading.value), v.status.value))
    if not rows:
        return None

    color_map = {
        "red": "#c53030",
        "yellow": "#b7791f",
        "green": "#2f855a",
        "unknown": "#718096",
    }
    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]
    colors = [color_map.get(r[2], "#718096") for r in rows]

    fig, ax = plt.subplots(figsize=(8.5, max(2.5, 0.45 * len(rows) + 1)))
    bars = ax.barh(labels, values, color=colors)
    ax.invert_yaxis()
    ax.set_xlabel("value")
    ax.set_title("Trigger readings (color = status)")
    ax.grid(True, axis="x", linestyle=":", alpha=0.4)
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width(),
            bar.get_y() + bar.get_height() / 2,
            f" {val:g}",
            va="center",
            fontsize=8,
        )
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    payload = base64.b64encode(buf.getvalue()).decode("ascii")
    return (
        f'<div class="chart"><img alt="Trigger readings" '
        f'src="data:image/png;base64,{payload}"></div>'
    )


_RED_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _first_red_threshold(red_str: str | None) -> float | None:
    if not red_str:
        return None
    m = _RED_NUM.search(red_str)
    return float(m.group(0)) if m else None
