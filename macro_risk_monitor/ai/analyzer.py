"""Call Anthropic Claude to produce the analytical markdown.

The Anthropic SDK is an optional dependency. When it's not installed or
ANTHROPIC_API_KEY is missing, the pipeline falls back to AnalyzeStub which
renders a deterministic markdown so HTML rendering and tests can still run.
"""

from __future__ import annotations

import logging

from .. import config as cfg
from ..schemas import Risk, Verdict
from .prompt_templates import ANALYZER_SYSTEM, build_analyzer_user_message

logger = logging.getLogger(__name__)


def analyze(risk: Risk, verdicts: list[Verdict]) -> tuple[str, str]:
    """Return (markdown, model_used). Falls back to stub on missing deps."""

    if not cfg.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set; using AnalyzeStub")
        return AnalyzeStub.render(risk, verdicts), "stub"

    try:
        from anthropic import Anthropic
    except ImportError:
        logger.warning("anthropic SDK not installed; using AnalyzeStub")
        return AnalyzeStub.render(risk, verdicts), "stub"

    client = Anthropic(api_key=cfg.ANTHROPIC_API_KEY)
    user_msg = build_analyzer_user_message(risk, verdicts)
    logger.info("Anthropic analyze model=%s tokens_max=%d", cfg.LLM_MODEL, cfg.LLM_MAX_TOKENS)
    resp = client.messages.create(
        model=cfg.LLM_MODEL,
        max_tokens=cfg.LLM_MAX_TOKENS,
        temperature=cfg.LLM_TEMPERATURE,
        system=ANALYZER_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )
    text = "".join(block.text for block in resp.content if block.type == "text")
    return text, cfg.LLM_MODEL


class AnalyzeStub:
    """Deterministic stand-in used in tests and when no LLM is configured."""

    @staticmethod
    def render(risk: Risk, verdicts: list[Verdict]) -> str:
        lines: list[str] = [
            f"# {risk.title} — analyzer stub",
            "",
            "## 1. 사실관계",
            f"가설: {risk.hypothesis.strip()}",
            "",
            "## 2. 가설 분해",
            "- 맞는 부분: 데이터 부족 (stub 모드)",
            "- 과장된 부분: 데이터 부족",
            "- 누락된 메커니즘: 데이터 부족",
            "",
            "## 3. 역사적 유사 사례",
        ]
        for h in risk.historical_analogy:
            lines.append(f"- {h}")
        lines.append("")
        lines.append("## 4. 트리거 상태 해설")
        for v in verdicts:
            value = v.reading.value if v.reading else None
            lines.append(
                f"- **{v.trigger_id}** [{v.status.value.upper()}]"
                f" value={value} · {v.rationale or ''}"
            )
        lines.append("")
        lines.append("## 5. 다음 critical window")
        for d in risk.critical_windows:
            lines.append(f"- {d.isoformat()}")
        return "\n".join(lines)
