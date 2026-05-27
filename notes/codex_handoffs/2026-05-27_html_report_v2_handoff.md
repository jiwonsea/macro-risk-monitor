# Codex handoff — HTML report v2 (6 user feedback items)

Date: 2026-05-27
Project: F:\dev\Portfolio\macro-risk-monitor
Plan (read-only): `notes/codex_handoffs/2026-05-27_html_report_v2_plan.md`

Claude Code에서 plan을 사용자와 합의·승인 완료. 그 plan을 그대로 구현하면 됨. 두 디자인 결정은 이미 사용자가 confirm:
- 단위: engine-level 자동 변환 (percent ↔ bps만)
- 차트: trigger별 sub-plot, 각 sub-plot에 red/yellow/green axvline
- VIX: yfinance ^VIX → FRED VIXCLS

---

## 작업 시작 전 반드시 읽을 파일

1. `notes/codex_handoffs/2026-05-27_html_report_v2_plan.md` — 전체 plan. Files 섹션의 MODIFY/NEW 리스트가 작업 범위.
2. 핵심 코드:
   - `macro_risk_monitor/engine/trigger.py` (`_match`, `evaluate`)
   - `macro_risk_monitor/engine/rule_of_three.py`
   - `macro_risk_monitor/sources/fred.py`
   - `macro_risk_monitor/schemas.py` (Risk, Trigger, Reading, Decision)
   - `macro_risk_monitor/output/charts.py` (`render_trigger_bar`)
   - `macro_risk_monitor/output/html.py` (`_build_table_rows`, `render_report`)
   - `macro_risk_monitor/templates/report.html.j2`
   - `macro_risk_monitor/ai/prompt_templates.py` (`ANALYZER_SYSTEM`, `build_analyzer_user_message`)
   - `macro_risk_monitor/pipeline/orchestrator.py` (`skip_llm` 분기)
3. 세 가설 YAML:
   - `theses/us_long_end_yield.yaml` (VIX trigger, critical_windows, ig_corp_spread)
   - `theses/ai_circular_revenue.yaml`, `theses/_401k_pe_distribution.yaml` (critical_windows migration)

---

## Critical caveats (실수 방지)

1. **단위 변환 방향 — 가장 흔한 함정**:
   - FRED `BAMLC0A0CM`는 percent를 **`0.74` 자체로** publish (즉 0.74가 0.74%, 74bps).
   - Trigger.unit이 `"bps"`이고 FRED source unit이 `"percent"`면 → **value × 100**으로 환산.
   - 반대 방향(`bps` → `percent`)이면 ÷ 100.
   - 같은 단위면 변환 없이 그대로.
   - 알려지지 않은 단위면 변환 skip + 경고 log (raise 금지 — engine이 거기서 죽으면 안 됨).
   - **test fixture로 0.74 percent → 74 bps 변환을 명시적으로 검증할 것.**

2. **Reading.display_value 추가 시**:
   - `schemas.py`의 Reading에 `display_value: float | str | None = None` 추가.
   - `engine/trigger.py:evaluate()`가 변환된 경우에만 채움. 변환 없으면 None.
   - `output/html.py:_build_table_rows()`가 `display_value or value`로 fallback.
   - 원본 `Reading.value`는 **절대 덮어쓰지 말 것** — verifier가 raw 수치로 cross-check하므로.

3. **critical_windows backward-compat**:
   - `Risk.critical_windows`의 `field_validator(mode="before")`가 입력 항목이 단순 `date`/`str`이면 `{date, event="(미지정)", rationale=None}` dict로 normalize.
   - dict 형식이면 그대로 전달.
   - 세 YAML 파일 모두 새 schema로 migrate하는 것이 plan의 일부 — 단, validator만 정확히 동작하면 기존 simple-date YAML도 깨지지 않아야 함 (회귀 안전망).

4. **차트 sub-plot signature 변경**:
   - `render_trigger_bar(verdicts)` → `render_trigger_bar(verdicts, triggers)`. caller(`output/html.py`)도 함께 수정.
   - matplotlib backend: 테스트와 headless 실행 위해 `matplotlib.use("Agg")` 가 모듈 top-level에서 호출되는지 확인 (없으면 추가).
   - 정성 threshold(예: `"2개사 동시 'rationalize'"`)는 axvline 그릴 수 없음 — `_NUMERIC_PAT` 매칭되는 것만 axvline.
   - sub-plot 1개당 figsize 세로 1.6 inch 권장 (plan에 명시).

5. **FRED metadata fetch**:
   - `fred.py`에 metadata 호출 추가: `https://api.stlouisfed.org/fred/series?series_id=...&api_key=...&file_type=json`. response의 `seriess[0].units_short` 또는 `units` 사용.
   - module-level dict 캐시 `{series_id: units_short}` — 같은 series 두 번 fetch 안 함.
   - API fail (network/quota) 시 Reading.raw에 `fred_units` 채우지 않음 → engine은 자동으로 변환 skip.

6. **VIXCLS 마이그레이션**:
   - `theses/us_long_end_yield.yaml`의 vix trigger만 변경. `source: yfinance` → `source: fred`, `series: ^VIX` → `series: VIXCLS`. threshold·unit·category 그대로.
   - yfinance dep는 pyproject.toml에서 유지. 사용처는 줄어든다는 메모만 CLAUDE.md에.

7. **Summary 문구 (rule_of_three.py)**:
   - 새 문구는 한국어. action ladder별 변형 예:
     - no_signal: `"RED 트리거 0개. 활성 시그널 없음."`
     - monitor: `"RED 트리거 {n}개, RED 카테고리 {k}개 ({카테고리}). 추가 모니터링."`
     - hedge_increase: `"RED 트리거 {n}개, RED 카테고리 {k}개 ({카테고리}). 헤지 증가 권고."`
     - defensive_position: `"RED 트리거 {n}개, RED 카테고리 {k}개. 방어적 포지션 권고."`
   - test에서 정확한 문자열 매칭이 깨지기 쉬우니 `assert "RED 트리거 2개" in summary` 같이 substring 매칭 사용.

8. **LLM prompt 보강**:
   - `ANALYZER_SYSTEM`에 plan에 명시된 두 줄 추가만 하면 됨. 기존 5개 섹션 헤더는 유지.
   - `build_analyzer_user_message()` payload의 `critical_windows`를 dict 형식으로 (date·event·rationale 포함) — verifier가 본문 수치 검증할 때 critical_windows 본문 인용은 verifier scope 외임.

9. **Pydantic 호환성**:
   - 이 프로젝트는 Pydantic v2. `field_validator(mode="before")` 사용. `model_validator`도 사용 가능.

10. **ASCII rule**:
    - commit message는 ASCII. 코드 코멘트도 가급적 영어. 한국어는 YAML description·HTML 본문·CLAUDE.md 한국어 부분에만.

---

## 검증 보고서 (필수 포함)

작업 종료 시 `notes/codex_handoffs/2026-05-27_html_report_v2_report.md`로 작성:

1. `python -m pytest tests/ -v` 전체 결과 (PASS 개수, 신규 테스트 명단).
2. **e2e 실행 — LLM 포함**:
   - 사전: `.env`에 ANTHROPIC_API_KEY 존재 확인 (없으면 보고서에 명시하고 LLM 검증 단계 skip).
   - 명령: `python -m macro_risk_monitor.cli run theses/us_long_end_yield.yaml` (LLM 포함, `--skip-llm` 안 줌).
   - 출력 텍스트(action·summary) + 생성된 HTML 경로.
3. **HTML 본문 검증** — `reports/html/2026-05-27-us_long_end_yield.html`을 grep해서 아래가 모두 보이는지 확인 후 발췌:
   - summary 새 문구 (`"RED 트리거"` 포함)
   - VIX trigger row에 `fred` source + 값이 비어있지 않음 (SSL 에러 사라짐)
   - ig_corp_spread row에 변환된 bps 값 (e.g., `74 bps`)
   - critical_windows table에 event 라벨 (FOMC 등)
   - 차트 img tag — sub-plot N개, height가 trigger 수에 비례
4. **회귀**: `_401k_pe_distribution`·`ai_circular_revenue`로도 `run --skip-llm` 한 번씩 실행 — schema validation 깨지지 않는지.
5. **git diff --stat**.
6. 작업 종료 후 `graphify update .`.

질문 있으면 작업 시작 전 묻기. 단위 변환 방향(특히 percent↔bps)은 plan과 이 핸드오프의 caveat 1번을 정확히 따를 것 — 직관적으로 헷갈리기 쉬움.
