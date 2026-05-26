"""Parse reviewer feedback markdown into ReviewPatch objects."""

from __future__ import annotations

import json
import logging
import re

from pydantic import ValidationError

from .. import config as cfg
from ..schemas import ReviewPatch
from .prompt_templates import REVIEWER_PARSER_SYSTEM, build_review_parser_user_message

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"```(?:json|patch)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def parse_feedback(md_text: str, thesis_name: str) -> ReviewPatch:
    for match in _FENCE_RE.finditer(md_text):
        try:
            payload = json.loads(match.group(1))
            return ReviewPatch.model_validate(payload)
        except (json.JSONDecodeError, ValidationError):
            continue

    # plan: review_parser.py Defect 1 fix. Free-form feedback must go through
    # the Anthropic parser fallback; no thesis-specific hardcoded extraction.
    return _extract_via_llm(md_text, thesis_name)


def _extract_via_llm(md_text: str, thesis_name: str) -> ReviewPatch:
    if not cfg.ANTHROPIC_API_KEY:
        raise RuntimeError(
            "No fenced JSON patch found and ANTHROPIC_API_KEY is not set. "
            "Add a ```patch JSON block or pass --patch with a staged patch file."
        )

    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise RuntimeError(
            "No fenced JSON patch found and anthropic SDK is not installed. "
            "Install macro-risk-monitor[ai] or pass --patch."
        ) from exc

    client = Anthropic(api_key=cfg.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=cfg.LLM_MODEL,
        max_tokens=cfg.LLM_MAX_TOKENS,
        temperature=0,
        system=REVIEWER_PARSER_SYSTEM,
        messages=[{"role": "user", "content": build_review_parser_user_message(md_text, thesis_name)}],
    )
    text = "".join(block.text for block in resp.content if block.type == "text")
    try:
        return ReviewPatch.model_validate(json.loads(text))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise RuntimeError("LLM fallback did not return a valid ReviewPatch JSON object") from exc
