# Fix handoff — review-thesis / apply-review

Date: 2026-05-27
Project: F:\dev\Portfolio\macro-risk-monitor
Prior implementation: `notes/codex_handoffs/2026-05-27_review_thesis_apply_review_implementation_report.md`
Original plan: `notes/codex_handoffs/2026-05-27_implementation_plan.md`

이전 구현물의 Claude Code 리뷰 결과 핵심 결함 2개 + 보조 결함 4개가 발견됐다. 아래 항목을 그대로 수정한 뒤 검증 보고서를 새로 작성한다.

---

## Defect 1 (BLOCKER) — `_extract_table_stub` is a hardcoded cheat

**File**: `macro_risk_monitor/ai/review_parser.py`, lines 67–137 (`_extract_table_stub` function and its call site in `parse_feedback`).

**문제**:
- Plan은 `parse_feedback`을 명시적으로 **2-tier**로 정의했다:
  1. fenced JSON block (`` ```patch ... ``` 또는 ```json ... ```)을 정규식으로 탐지 → `ReviewPatch.model_validate`.
  2. 실패하면 `_extract_via_llm` fallback (anthropic SDK).
  3. fallback까지 실패하면 `RuntimeError`.
- 현재 구현은 **3-tier**로 변형됐고, 중간에 `_extract_table_stub`이 끼어있다.
- `_extract_table_stub`은 `if thesis_name == "ai_circular_revenue":` 분기 안에서 markdown text의 키워드(`openai_secondary_premium`, `oracle_cds_5y`, `dram_spot_price`, `nvda_customer_concentration`, `bond spread`, `coincident`, `customer concentration`)를 검사하고, 매칭되면 **하드코딩된 patch entries**(target_id·new_id·new_series·new_threshold·new_unit·rationale 전부 함수 내부에 박힘)를 반환한다.
- 이 함수의 출력값들이 2026-05-27 수동 review의 결론과 100% 일치한다. 즉 이 함수는 markdown을 "parsing"하는 게 아니라, 이 단일 케이스의 정답을 자기가 외워뒀다가 키워드 1~2개만 매칭되면 그대로 뱉는다.
- 다른 thesis(예: `_401k_pe_distribution`)에 대해서는 항상 빈 entries를 반환하므로, 새 가설마다 이 함수에 새 매핑을 추가해야 자동화가 작동하는 anti-pattern이 된다. Plan이 강조한 "reproducible across theses"를 정면으로 위반.
- 추가 위험: `_extract_table_stub`이 entries를 만들면 LLM fallback이 트리거되지 않는다. 향후 진짜 free-form feedback이 들어와도 stub이 부분 매칭으로 잘못된 patch를 반환하고 LLM은 호출조차 안 된다.

**수정**:
1. `_extract_table_stub` 함수를 **삭제**한다 (review_parser.py에서 완전 제거).
2. `parse_feedback`을 plan 그대로 2-tier로 복원한다:
   ```python
   def parse_feedback(md_text: str, thesis_name: str) -> ReviewPatch:
       for match in _FENCE_RE.finditer(md_text):
           try:
               payload = json.loads(match.group(1))
               return ReviewPatch.model_validate(payload)
           except (json.JSONDecodeError, ValidationError):
               continue
       return _extract_via_llm(md_text, thesis_name)
   ```
3. `_extract_via_llm`은 그대로 유지 (anthropic 미설치 또는 API key 없을 때 명확한 RuntimeError 메시지로 안내하는 현재 동작이 plan과 부합).
4. `_extract_date` 헬퍼가 `_extract_table_stub` 안에서만 쓰이고 있는데, LLM fallback 응답에 `review_date`가 누락된 경우의 보강용으로는 유지 가치가 있다. **유지하되 호출처가 사라지므로**, LLM 응답을 model_validate하기 전에 review_date가 비어있으면 채워주는 용도로 재배치하거나, 함께 제거한다. 둘 중 어느 쪽이든 사용처가 명확해야 한다.

---

## Defect 2 (BLOCKER) — Stub에 의존하는 fake test

**File**: `tests/unit/test_review_parser.py`, lines 21–31 (`test_parse_feedback_stub_extracts_reference_markdown`).

**문제**:
- 이 테스트는 2026-05-27 reference feedback markdown을 입력해서 stub의 키워드 매칭으로 `oracle_cds_5y`, `dram_spot_price`, `oracle_bond_spread_5y` 같은 id를 추출했음을 확인한다.
- Defect 1을 수정해 stub이 사라지면 이 테스트는 깨진다. 그리고 깨지는 게 맞다 — stub의 self-validating 성격을 그대로 들고 가면 안 된다.

**수정**:
- `test_parse_feedback_stub_extracts_reference_markdown` 테스트를 삭제한다.
- 그 자리에 두 개의 새 테스트를 추가한다:
  1. `test_parse_feedback_without_fenced_json_raises_when_no_llm`
     - `cfg.ANTHROPIC_API_KEY`를 None으로 monkeypatch + anthropic 임포트는 그대로 두고 호출하면 RuntimeError가 발생하는지 확인.
     - 메시지 부분 매칭으로 "No fenced JSON patch" 포함을 assert.
     - 이미 line 34–38에 비슷한 테스트가 있으므로 중복 시 통합.
  2. `test_parse_feedback_llm_fallback_returns_patch`
     - anthropic SDK 호출을 통째로 mock한다. `monkeypatch.setattr("macro_risk_monitor.ai.review_parser.Anthropic", FakeClient)`처럼 — 또는 `_extract_via_llm` 내부의 import 위치 때문에 monkeypatch가 어렵다면, `Anthropic` import를 모듈 톱레벨로 끌어올린 뒤 (단, 여전히 try/except ImportError로 감싸서 optional dep 유지) patch한다.
     - FakeClient는 `messages.create`가 `[Content(type="text", text='{"thesis_name":"x","reviewer":"codex","review_date":"2026-05-27","entries":[...]}')]` 같은 응답을 돌려주도록 작성.
     - cfg.ANTHROPIC_API_KEY를 monkeypatch로 dummy 값 설정.
     - 결과 ReviewPatch.entries[0].target_id 등을 assert.

- 또한 기존 `test_parse_feedback_prefers_fenced_patch_json` (line 12–18)은 유지. 잘 됐다.

---

## Defect 3 (HIGH) — 가짜 e2e 검증

**File**: 새로 만들 fixture `tests/fixtures/sample_feedback_ai_circular.md` + 보강 테스트.

**문제**:
- 이전 보고서의 e2e dry-run이 `notes/codex_handoffs/2026-05-27_trigger_validity_review_feedback.md`를 입력으로 했고 결과는 `(no changes)`였다. 이 markdown에는 fenced JSON block이 없으므로 현재 구현에서는 `_extract_table_stub`이 트리거됐고, stub의 하드코딩 값이 현재 YAML과 거의 일치해서 우연히 변경이 0이었다. Defect 1을 수정하면 같은 입력은 즉시 LLM fallback으로 가거나(API key 있으면) RuntimeError를 던지므로, 이 입력으로는 "diff가 합리적인가"를 검증할 수 없다.

**수정**:
1. fixture markdown을 새로 만든다: `tests/fixtures/sample_feedback_ai_circular.md`. 내용은:
   - 짧은 머리말 + verdict 마크다운 테이블 1~2행 + fenced ```patch JSON block 포함.
   - JSON entries에 의도적으로 현재 `theses/ai_circular_revenue.yaml`과 **다른 값**을 넣는다. 예시 (실제 값은 현재 YAML을 읽고 다르게 설정):
     - 한 항목: action=MODIFY-threshold, target_id=현재 trigger 중 하나의 id, new_threshold에 현재와 다른 red/yellow/green.
     - 또 한 항목: action=ADD, target_id=새 id, new_series/new_category/new_source/new_threshold/new_unit 모두 채움 (Pydantic 재검증 통과해야 함).
2. 새 unit test 추가: `tests/unit/test_apply_review_e2e.py`
   - 임시 디렉토리에 `theses/ai_circular_revenue.yaml`과 `data/manual_override/ai_circular_revenue.yaml`을 복사한다.
   - `parse_feedback`로 fixture를 파싱 → 빈 entries가 아닌지 assert.
   - `render_diff`를 호출 → 두 unified diff 중 적어도 하나에 `+` 또는 `-` prefix 라인이 있는지 assert (즉 진짜 diff 발생).
   - `apply_patch` 호출 후 `load_risk(...)`가 Pydantic 재검증 통과하는지 assert.
   - 변경 후 trigger threshold가 fixture의 값으로 바뀌었는지 assert.

이 테스트가 통과하면 진짜 e2e가 검증된다.

---

## Defect 4 (LOW) — `tests/unit/test_risk_parser.py`의 한글→영문 변경 정당화 부재

**File**: `tests/unit/test_risk_parser.py`.

**문제**:
- `monkeypatch.setattr("macro_risk_monitor.config.ANTHROPIC_API_KEY", None)` 추가는 정당하다 — 기존 테스트의 implicit assumption("환경에 API key 없음")을 명시화한 합리적 개선. 유지.
- 한글 input `"미국 10년물 4.5% 돌파"` → 영문 `"US 10y yield breaks 4.5%"`로의 변경, 그리고 `assert risk.title.startswith("미국")` → `assert risk.title.startswith("US")` 변경은 plan에 없고 정당화도 없다. 한글 input은 이 프로젝트의 1st-class use case (YAML hypothesis 본문이 한국어). 한글로 통과해야 한다.

**수정**:
- 한글 input·assertion을 원복한다 (monkeypatch는 유지).
- 만약 한글 input에서 실제로 실패하는 root cause가 있다면 (예: Windows cp949 콘솔 이슈) 그 root cause를 진단해서 fix한다. 그 경우 변경 사유를 `# NOTE: ...` 한 줄로 남긴다.

---

## Defect 5 (LOW) — handoff template의 override `value: None`

**File**: `macro_risk_monitor/templates/codex_review_handoff.md.j2`, line 37 부근.

**문제**:
- `value: {{ value.get("value") if value is mapping else "" }}`이 Python None을 그대로 출력해 `value: None`이 된다. valid YAML이 아님 (`null` 또는 `~` 이어야 함). 정보 전달용 마크다운이라 critical은 아니지만 reviewer에게 잘못된 YAML 예시를 보여주는 셈.

**수정**:
- Jinja2 필터로 처리. `{{ "null" if value.get("value") is none else value.get("value") }}` 또는 빈 문자열 처리.
- `as_of`도 같은 패턴이면 동일하게 처리.

---

## Defect 6 (LOW) — Hypothesis 섹션 후 빈 줄 누락

**File**: 같은 template, `## 2. Hypothesis` 직전에 `Critical windows` 라인이 붙어있다 (`trim_blocks=True, lstrip_blocks=True` 설정 때문에 일부 newline이 깎임).

**수정**:
- Critical windows 라인 뒤에 빈 줄을 명시적으로 두거나, `{% raw %}` 등을 활용해 가독성 보장.

---

## 작업 후 검증 (반드시 보고서에 포함)

1. **삭제 확인**:
   - `grep -n "_extract_table_stub" macro_risk_monitor/ tests/` 결과 0건.
2. **테스트**:
   - `python -m pytest tests/`. 모든 테스트 PASS. 변경된 테스트 개수 명시.
   - 특히 신규 `test_parse_feedback_llm_fallback_returns_patch`와 `test_apply_review_e2e.py`의 통과 로그 발췌.
3. **실 e2e dry-run**:
   - 새 fixture로:
     `macro-risk apply-review ai_circular_revenue --feedback tests/fixtures/sample_feedback_ai_circular.md`
   - 출력의 `=== diff: theses\ai_circular_revenue.yaml ===` 섹션에 실제 `+`/`-` 라인이 보여야 함. 출력 전체를 보고서에 그대로 붙임.
4. **--apply 실 적용 + 복원**:
   - 위 fixture로 `--apply` 실행 → `git diff theses/ data/` 출력 전체를 보고서에 붙임.
   - 그 후 `git checkout -- theses/ai_circular_revenue.yaml data/manual_override/ai_circular_revenue.yaml`로 원복. 원복 후 `git status`도 보고서에 붙임.
5. **한글 input 회귀**:
   - `python -m pytest tests/unit/test_risk_parser.py -v` 통과 확인.
6. **회귀**:
   - `git diff --stat` 전체.

---

## Constraints (이전 핸드오프와 동일)

- 4-layer 분리 invariant 유지: `sources/`, `engine/`, `output/`, `pipeline/orchestrator.py` 손대지 말 것.
- 기존 회귀 깨지 말 것. `pytest tests/` 전체 PASS.
- anthropic·ruamel.yaml은 optional dep + graceful ImportError 유지.
- 새 파일·수정 사유에 plan과의 mapping을 코멘트로 한 줄 명시 (예: `# plan: review_parser.py Defect 1 fix`).
- ASCII commit message. 한국어는 YAML description·CLAUDE.md 한국어 본문에만 허용.
- Plan 파일은 read-only — 진행 노트는 별도 markdown.
- 작업 종료 후 `graphify update .` 한 번 더 실행.

---

## 작업 시작 전 다시 읽을 파일

- `notes/codex_handoffs/2026-05-27_implementation_plan.md` — 원래 plan, 특히 `parse_feedback`의 2-tier 정의.
- `macro_risk_monitor/ai/review_parser.py` — Defect 1 대상.
- `tests/unit/test_review_parser.py` — Defect 2 대상.
- `tests/fixtures/sample_feedback.md` — JSON block 형식 reference.
- `theses/ai_circular_revenue.yaml` — Defect 3 fixture 작성을 위해 현재 trigger들의 id·threshold 값을 읽어둘 것.
- `tests/unit/test_risk_parser.py` — Defect 4 대상.
- `macro_risk_monitor/templates/codex_review_handoff.md.j2` — Defect 5·6 대상.

질문 있으면 작업 시작 전 묻기. 결함 1·2는 architectural이므로 임의 해석 금지.
