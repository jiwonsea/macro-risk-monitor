"""System and user prompts used by analyzer.py and risk_parser.py.

Design principles distilled from the user's 5/16~5/18 dialog with Claude:
    - Force 3-way decomposition (correct / overstated / missing).
    - Ban hedging ("balanced view", "교과서 답").
    - Restrict numeric citations to the supplied sources block — verifier.py
      will reject answers that smuggle in outside numbers.
    - Cite historical analogy when YAML provides one; if it fits poorly,
      propose a better one.
"""

from __future__ import annotations

import json

from ..schemas import Risk, Verdict


ANALYZER_SYSTEM = """역할: 사용자가 제시한 거시 리스크/가설을 비판적으로 평가하는 분석가.

규칙:
1. 가설에 동의·반대를 단정하지 말고 3분할로 평가:
   - 사실관계는 어디까지 맞는가 (제공된 sources 데이터만 인용, 외부 수치 금지)
   - 과장되거나 부정확한 부분
   - 누락된 메커니즘
2. 역사적 유사 사례가 YAML에 명시되어 있으면 그 정합성을 평가. 비유가 부적절하면 더 정합한 사례 1~2개 제시.
3. 트리거 평가(Verdict) 결과를 본문에서 풀어쓰고, RED 항목은 메커니즘과 함께 설명.
4. "교과서 답"·"양측 균형" 같은 hedging 금지. 근거 부족 시 "데이터 부족"으로 명시.
5. 모든 수치 인용은 제공된 Readings 블록의 값과 정확히 일치해야 한다 (verifier가 검증).
6. 각 트리거 reading과 가설 메커니즘의 인과관계를 명시: 해당 트리거가 가설을 어떻게 검증, 약화, 반증하는지 설명.
7. critical_windows 각 항목별로 event와 rationale을 사용해 그 날짜가 왜 중요한지 분석. 단순 캘린더 나열 금지.
8. readings, thresholds, critical_windows에 없는 숫자는 쓰지 말라. 차이값, bp 환산값, 역사 사례의 시장 레벨도 계산하거나 추가하지 말라.
9. 출력은 markdown — 본문은 한국어. 섹션 헤더는 다음 순서로 고정:
   ## 1. 사실관계
   ## 2. 가설 분해
   ## 3. 역사적 유사 사례
   ## 4. 트리거 상태 해설
   ## 5. 다음 critical window
"""


def build_analyzer_user_message(
    risk: Risk, verdicts: list[Verdict]
) -> str:
    readings_block = []
    for v in verdicts:
        r = v.reading
        readings_block.append(
            {
                "trigger_id": v.trigger_id,
                "status": v.status.value,
                "value": (
                    r.display_value
                    if r and r.display_value is not None
                    else r.value if r else None
                ),
                "raw_value": r.value if r else None,
                "as_of": r.as_of.isoformat() if r and r.as_of else None,
                "source_url": r.source_url if r else None,
                "rationale": v.rationale,
            }
        )

    triggers_block = [
        {
            "id": t.id,
            "category": t.category.value,
            "description": t.description,
            "unit": t.unit,
            "threshold": t.threshold.model_dump(),
        }
        for t in risk.triggers
    ]

    body = {
        "risk_title": risk.title,
        "hypothesis": risk.hypothesis,
        "historical_analogy": risk.historical_analogy,
        "critical_windows": [
            {
                "date": w.date.isoformat(),
                "event": w.event,
                "rationale": w.rationale,
            }
            for w in risk.critical_windows
        ],
        "triggers": triggers_block,
        "readings": readings_block,
    }
    return (
        "다음은 평가 대상 가설과 측정된 트리거 데이터다. 위 규칙대로 markdown 보고서를 작성하라.\n\n"
        "```json\n"
        f"{json.dumps(body, ensure_ascii=False, indent=2)}\n"
        "```"
    )


RISK_PARSER_SYSTEM = """역할: 사용자가 자연어로 제시한 거시 리스크 한 줄을 모니터링 가능한 가설 골격으로 변환.

출력: 다음 JSON 스키마. 마크다운·설명 금지, JSON만:

{
  "name": "snake_case_short_name",
  "title": "사람 읽기용 한 줄 제목",
  "hypothesis": "2~4 문장으로 메커니즘 풀어쓰기",
  "historical_analogy": ["역사적 유사 사례 1~3개"],
  "triggers": [
    {
      "id": "snake_case",
      "category": "leading|coincident|lagging",
      "source": "fred|yfinance|sec_edgar|manual_override",
      "series": "FRED 시리즈 ID 또는 ticker 또는 override 키",
      "unit": "percent|bps|usd|index 등",
      "description": "한 줄 설명",
      "threshold": {"red": "비교식 또는 정성 규칙", "yellow": "...", "green": "..."}
    }
  ]
}

규칙:
- 5~7개 트리거. 각 카테고리(leading/coincident/lagging)에 최소 1개 분배.
- 무료 데이터 소스(fred·yfinance·sec_edgar)로 자동 fetch 가능한 트리거를 우선. 정성·유료 데이터는 manual_override로.
- threshold는 numeric 비교식("> 4.5", "<= -10") 우선. 정성 규칙은 문장으로 작성하되 짧게.
- 출력은 valid JSON만.
"""


def build_risk_parser_user_message(natural_language: str) -> str:
    return f"리스크 한 줄: {natural_language}\n\n위 스키마에 맞게 JSON만 출력하라."
REVIEWER_PARSER_SYSTEM = """Role: convert reviewer feedback markdown into a ReviewPatch JSON object.

Rules:
- Output valid JSON only. Do not wrap it in markdown.
- Preserve the thesis_name requested by the user.
- Use only these actions: KEEP, MODIFY-threshold, MODIFY-category, MODIFY-source, REPLACE, ADD.
- Mark entries unverified=true when the feedback says UNVERIFIED or asks for human validation.
- For threshold changes, emit new_threshold with red/yellow/green string fields.
- For manual override changes, emit new_override with value/as_of/source_url/note keys when available.
"""


def build_review_parser_user_message(md_text: str, thesis_name: str) -> str:
    return (
        "Extract one ReviewPatch for thesis_name="
        f"{json.dumps(thesis_name, ensure_ascii=False)} from this markdown.\n\n"
        "Required JSON schema shape:\n"
        "{\n"
        '  "thesis_name": "name",\n'
        '  "reviewer": "codex",\n'
        '  "review_date": "YYYY-MM-DD",\n'
        '  "entries": [\n'
        "    {\n"
        '      "target_id": "existing_or_new_trigger_id",\n'
        '      "action": "REPLACE",\n'
        '      "new_id": "optional_new_trigger_id",\n'
        '      "new_series": "optional_series",\n'
        '      "new_category": "leading|coincident|lagging",\n'
        '      "new_source": "manual_override|fred|yfinance|sec_edgar|news_rss|earnings_transcript_nlp",\n'
        '      "new_threshold": {"red": ">= 1", "yellow": ">= 0.5", "green": "< 0.5"},\n'
        '      "new_description": "optional description",\n'
        '      "new_unit": "optional unit",\n'
        '      "new_override": {"value": null, "as_of": "YYYY-MM-DD", "source_url": "https://...", "note": "..."},\n'
        '      "rationale": "short reason",\n'
        '      "unverified": false\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Markdown feedback:\n"
        f"{md_text}"
    )
