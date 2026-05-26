"""Free-form risk sentence -> Risk skeleton (YAML-loadable).

Falls back to a minimal heuristic when no LLM is available so the ad-hoc
mode still produces a usable scaffold for the user to edit by hand.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date

from .. import config as cfg
from ..schemas import Risk
from .prompt_templates import RISK_PARSER_SYSTEM, build_risk_parser_user_message

logger = logging.getLogger(__name__)


def parse_risk(natural_language: str) -> Risk:
    """Return a Risk object built from natural-language input."""

    payload = _call_llm(natural_language)
    if payload is None:
        payload = _heuristic_skeleton(natural_language)
    payload.setdefault("created", date.today().isoformat())
    return Risk.model_validate(payload)


def _call_llm(text: str) -> dict | None:
    if not cfg.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set; risk_parser falling back to heuristic")
        return None
    try:
        from anthropic import Anthropic
    except ImportError:
        logger.warning("anthropic not installed; risk_parser heuristic only")
        return None

    client = Anthropic(api_key=cfg.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=cfg.LLM_MODEL,
        max_tokens=2048,
        temperature=0.3,
        system=RISK_PARSER_SYSTEM,
        messages=[{"role": "user", "content": build_risk_parser_user_message(text)}],
    )
    raw = "".join(b.text for b in resp.content if b.type == "text").strip()
    json_str = _extract_json(raw)
    if not json_str:
        logger.warning("risk_parser: LLM returned non-JSON; falling back")
        return None
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as exc:
        logger.warning("risk_parser: JSON parse failed: %s", exc)
        return None


def _extract_json(text: str) -> str | None:
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fence:
        return fence.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return None


def _heuristic_skeleton(text: str) -> dict:
    """Conservative offline skeleton when LLM is unavailable.

    Builds a single placeholder trigger that the user is expected to fill in.
    Intentionally minimal so it can't silently produce a wrong analysis.
    """

    name = re.sub(r"[^a-z0-9]+", "_", text.lower())[:40].strip("_") or "ad_hoc_risk"
    return {
        "name": name,
        "title": text[:80],
        "hypothesis": text,
        "historical_analogy": [],
        "triggers": [
            {
                "id": "placeholder",
                "category": "leading",
                "source": "manual_override",
                "series": "placeholder",
                "description": "LLM 미사용 폴백 — 사용자가 직접 정의 필요",
                "threshold": {"red": "TBD", "yellow": "TBD", "green": "TBD"},
            }
        ],
    }
