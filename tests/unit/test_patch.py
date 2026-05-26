from datetime import date
from pathlib import Path

import pytest

from macro_risk_monitor.ai.patch import apply_patch, dump_patch, load_patch, render_diff
from macro_risk_monitor.engine.hypothesis import load_risk
from macro_risk_monitor.schemas import PatchAction, PatchEntry, ReviewPatch, Threshold


def _write_sample_files(tmp_path: Path) -> tuple[Path, Path]:
    risk_path = tmp_path / "sample.yaml"
    override_path = tmp_path / "manual.yaml"
    risk_path.write_text(
        """
name: sample
title: Sample thesis
hypothesis: |
  sample hypothesis
triggers:
  - id: a
    category: leading
    source: manual_override
    series: old_key
    unit: percent
    description: |
      keep this block
    threshold:
      red: ">= 1"
      yellow: ">= 0.5"
      green: "< 0.5"
decision_rule: rule_of_three
""".lstrip(),
        encoding="utf-8",
    )
    override_path.write_text(
        """
old_key:
  value: null
  as_of: 2026-05-27
  source_url: https://example.com
  note: |
    keep note
""".lstrip(),
        encoding="utf-8",
    )
    return risk_path, override_path


def test_render_diff_and_apply_patch_round_trip(tmp_path):
    pytest.importorskip("ruamel.yaml")
    risk_path, override_path = _write_sample_files(tmp_path)
    patch = ReviewPatch(
        thesis_name="sample",
        review_date=date(2026, 5, 27),
        entries=[
            PatchEntry(
                target_id="a",
                action=PatchAction.MODIFY_THRESHOLD,
                new_series="new_key",
                new_threshold=Threshold(red=">= 2", yellow=">= 1", green="< 1"),
            )
        ],
    )

    risk_diff, override_diff = render_diff(patch, risk_path, override_path)
    assert "red: '>= 2'" in risk_diff
    assert "new_key:" in override_diff

    apply_patch(patch, risk_path, override_path)
    risk = load_risk(risk_path)
    assert risk.triggers[0].series == "new_key"
    assert risk.triggers[0].threshold.red == ">= 2"
    assert "new_key:" in override_path.read_text(encoding="utf-8")


def test_dump_and_load_patch(tmp_path):
    pytest.importorskip("ruamel.yaml")
    path = tmp_path / "patch.yaml"
    patch = ReviewPatch(
        thesis_name="sample",
        review_date=date(2026, 5, 27),
        entries=[PatchEntry(target_id="a", action=PatchAction.KEEP)],
    )

    dump_patch(patch, path)

    assert load_patch(path).entries[0].action == PatchAction.KEEP
