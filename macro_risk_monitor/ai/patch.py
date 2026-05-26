"""Apply ReviewPatch objects to thesis and manual_override YAML files."""

from __future__ import annotations

import difflib
import io
from copy import deepcopy
from pathlib import Path
from typing import Any

from ..engine.hypothesis import load_risk
from ..schemas import PatchAction, PatchEntry, ReviewPatch


def render_diff(patch: ReviewPatch, risk_path: Path, override_path: Path) -> tuple[str, str]:
    risk_before = _read_text(risk_path)
    override_before = _read_text(override_path)

    risk_data, override_data = _load_yaml_docs(risk_path, override_path)
    risk_original = deepcopy(risk_data)
    override_original = deepcopy(override_data)
    _mutate_docs(patch, risk_data, override_data)
    risk_after = risk_before if risk_data == risk_original else _dump_yaml(risk_data)
    override_after = (
        override_before if override_data == override_original else _dump_yaml(override_data)
    )

    return (
        _unified(risk_before, risk_after, risk_path),
        _unified(override_before, override_after, override_path),
    )


def apply_patch(patch: ReviewPatch, risk_path: Path, override_path: Path) -> None:
    risk_before = _read_text(risk_path)
    override_before = _read_text(override_path)
    risk_data, override_data = _load_yaml_docs(risk_path, override_path)
    risk_original = deepcopy(risk_data)
    override_original = deepcopy(override_data)
    _mutate_docs(patch, risk_data, override_data)

    risk_after = risk_before if risk_data == risk_original else _dump_yaml(risk_data)
    override_after = (
        override_before if override_data == override_original else _dump_yaml(override_data)
    )
    if risk_after != risk_before:
        risk_path.write_text(risk_after, encoding="utf-8")
    if override_after != override_before:
        override_path.parent.mkdir(parents=True, exist_ok=True)
        override_path.write_text(override_after, encoding="utf-8")

    try:
        load_risk(risk_path)
    except Exception:
        risk_path.write_text(risk_before, encoding="utf-8")
        override_path.write_text(override_before, encoding="utf-8")
        raise


def dump_patch(patch: ReviewPatch, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = patch.model_dump(mode="json", exclude_none=True)
    path.write_text(_dump_yaml(data), encoding="utf-8")


def load_patch(path: Path) -> ReviewPatch:
    data = _load_yaml_file(path)
    return ReviewPatch.model_validate(data)


def _mutate_docs(patch: ReviewPatch, risk_data: Any, override_data: Any) -> None:
    if override_data is None:
        override_data = {}
    triggers = risk_data.setdefault("triggers", [])
    for entry in patch.entries:
        if entry.unverified:
            continue
        if entry.action == PatchAction.KEEP:
            continue
        if entry.action == PatchAction.ADD:
            trigger = _find_trigger(triggers, entry.target_id)
            if trigger is None:
                trigger = _new_trigger(entry)
                triggers.append(trigger)
            _apply_entry(trigger, entry)
        else:
            trigger = _find_trigger(triggers, entry.target_id)
            if trigger is None and entry.new_id:
                trigger = _find_trigger(triggers, entry.new_id)
            if trigger is None:
                raise RuntimeError(f"trigger not found for patch entry: {entry.target_id}")
            old_series = trigger.get("series")
            _apply_entry(trigger, entry)
            _move_override_key(override_data, old_series, trigger.get("series"))

        if entry.new_override is not None:
            key = _override_key(trigger)
            override_data[key] = deepcopy(entry.new_override)


def _apply_entry(trigger: Any, entry: PatchEntry) -> None:
    if entry.new_id:
        _set_if_changed(trigger, "id", entry.new_id)
    if entry.new_category:
        _set_if_changed(trigger, "category", entry.new_category.value)
    if entry.new_source:
        _set_if_changed(trigger, "source", entry.new_source.value)
    if entry.new_series:
        _set_if_changed(trigger, "series", entry.new_series)
    if entry.new_unit:
        _set_if_changed(trigger, "unit", entry.new_unit)
    if entry.new_description:
        _set_if_changed(trigger, "description", entry.new_description)
    if entry.new_threshold:
        new_threshold = entry.new_threshold.model_dump(mode="json", exclude_none=True)
        if dict(trigger.get("threshold", {})) != new_threshold:
            trigger["threshold"] = new_threshold


def _set_if_changed(mapping: Any, key: str, value: Any) -> None:
    if mapping.get(key) != value:
        mapping[key] = value


def _new_trigger(entry: PatchEntry) -> dict[str, Any]:
    if not entry.new_category or not entry.new_source or not entry.new_threshold:
        raise RuntimeError(f"ADD entry is missing required trigger fields: {entry.target_id}")
    return {
        "id": entry.new_id or entry.target_id,
        "category": entry.new_category.value,
        "source": entry.new_source.value,
        "series": entry.new_series,
        "unit": entry.new_unit,
        "description": entry.new_description or entry.rationale,
        "threshold": entry.new_threshold.model_dump(mode="json", exclude_none=True),
    }


def _find_trigger(triggers: list[Any], trigger_id: str) -> Any | None:
    for trigger in triggers:
        if trigger.get("id") == trigger_id:
            return trigger
    return None


def _move_override_key(override_data: Any, old_series: str | None, new_series: str | None) -> None:
    if not old_series or not new_series or old_series == new_series:
        return
    if old_series in override_data and new_series not in override_data:
        override_data[new_series] = override_data.pop(old_series)


def _override_key(trigger: Any) -> str:
    return trigger.get("series") or trigger["id"]


def _load_yaml_docs(risk_path: Path, override_path: Path) -> tuple[Any, Any]:
    return _load_yaml_file(risk_path), _load_yaml_file(override_path) if override_path.exists() else {}


def _load_yaml_file(path: Path) -> Any:
    yaml = _yaml()
    with path.open(encoding="utf-8") as fh:
        return yaml.load(fh)


def _dump_yaml(data: Any) -> str:
    yaml = _yaml()
    buf = io.StringIO()
    yaml.dump(data, buf)
    return buf.getvalue()


def _yaml():
    try:
        from ruamel.yaml import YAML
    except ImportError as exc:
        raise RuntimeError(
            "ruamel.yaml is required for review patch round-trip editing. "
            "Install dependencies with `pip install -e .`."
        ) from exc
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 100
    # rt mode dumps None as an empty scalar; force explicit `null` so existing
    # `value: null` rows survive round-trip without diff noise when ADD entries
    # mutate the mapping.
    yaml.representer.add_representer(
        type(None),
        lambda r, _: r.represent_scalar("tag:yaml.org,2002:null", "null"),
    )
    return yaml


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _unified(before: str, after: str, path: Path) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path),
        )
    )
