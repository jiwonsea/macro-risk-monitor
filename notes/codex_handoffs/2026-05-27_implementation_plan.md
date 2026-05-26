# Multi-model orchestration: `review-thesis` + `apply-review` (Option B: Patch 자동 생성)

## Context

2026-05-27 세션에서 Codex와 수동으로 진행한 trigger validity review (`notes/codex_handoffs/2026-05-27_trigger_validity_review*.md`) 가 가설 검증에 매우 효과적이었음 — REPLACE 3건, MODIFY 3건, ADD 2건의 patch가 도출됐다. 그러나 흐름이 전부 수동이라 **새 가설 추가 시 반복 비용**이 크고, 사용자의 자연어 요청·Codex feedback·YAML 수정이 분리돼 trace가 끊긴다.

이 작업은 그 수동 흐름을 **두 개의 CLI 서브커맨드로 codify**한다:

1. `mrm review-thesis <name>` — thesis YAML + manual_override YAML을 읽어 표준 핸드오프 markdown을 자동 생성. 사용자는 이를 Codex(또는 임의 외부 reviewer)에 그대로 전달.
2. `mrm apply-review <name> --feedback <path>` — feedback markdown을 파싱해 thesis YAML과 manual_override YAML 양쪽에 unified diff를 생성, staging file로 저장. `--apply` flag가 명시될 때만 실제 파일에 반영.

목표는 **multi-model consensus(Claude analyzer + 외부 reviewer)** 를 reproducible pipeline으로 만드는 것. LLM 비용은 거의 들지 않으며 (apply-review의 fallback parser만 anthropic 호출), 핵심 가치는 reasoning bias hedging — Phase 2b 자동화 격상 전 단계의 brick.

## Architecture

```
review-thesis                       apply-review
─────────────                       ────────────
Risk YAML  ─┐                       feedback.md ─┐
override.yaml ┼─> Jinja2 template ─> handoff.md   ├─> JSON block parser
                                                  │   └─> LLM fallback (anthropic SDK, optional)
                                                  ▼
                                                ReviewPatch (Pydantic)
                                                  │
                              ┌───────────────────┼─────────────────────┐
                              ▼                   ▼                     ▼
                       diff renderer       ruamel.yaml round-trip   staging file
                       (unified diff)      (--apply만)              (patch.yaml)
```

4-layer invariant 유지: 신규 코드는 모두 **ai/** layer에 들어가고 sources/engine/output 은 건드리지 않음 (orchestrator도 무관). schemas.py만 새 모델을 위해 한 번 확장.

## Files

### NEW

- **`macro_risk_monitor/ai/reviewer.py`** — handoff markdown 렌더링
  - `render_review_handoff(risk: Risk, override_path: Path, today: date) -> str`: thesis YAML + manual_override 데이터를 모아 Jinja2 템플릿에 주입.
  - `write_review_handoff(risk_name: str, out_dir: Path = "notes/codex_handoffs") -> Path`: 파일명 `{YYYY-MM-DD}_{thesis_name}_review.md`로 저장 후 경로 반환.

- **`macro_risk_monitor/ai/review_parser.py`** — feedback → `ReviewPatch`
  - `parse_feedback(md_text: str, thesis_name: str) -> ReviewPatch`:
    1. fenced JSON block (` ```patch ... ``` `) 우선 탐지 → `ReviewPatch.model_validate`.
    2. JSON block 없거나 schema 실패 → `_extract_via_llm(md_text)` fallback.
    3. fallback도 실패 → `RuntimeError`로 escalate (apply-review가 stderr에 안내).
  - `_extract_via_llm(md_text)`: `ai/analyzer.py`와 동일한 pattern — try-import anthropic, stub fallback, `cfg.LLM_MODEL`. prompt는 `prompt_templates.REVIEWER_PARSER_SYSTEM` + JSON-only output 강제.

- **`macro_risk_monitor/ai/patch.py`** — patch 적용 + diff 생성
  - `render_diff(patch: ReviewPatch, risk_path: Path, override_path: Path) -> tuple[str, str]`: 두 파일 각각의 unified diff (변경 전/후 in-memory).
  - `apply_patch(patch: ReviewPatch, risk_path: Path, override_path: Path) -> None`: ruamel.yaml round-trip — `YAML(typ='rt')` 로 load → in-place mutate → dump. 적용 후 `load_risk(risk_path)` 재검증; Pydantic 실패 시 원본 복원 + `RuntimeError`.
  - `dump_patch(patch: ReviewPatch, path: Path) -> None`: ReviewPatch를 사람이 검토·편집 가능한 YAML로 직렬화 (staging file).
  - `load_patch(path: Path) -> ReviewPatch`: 편집된 staging file 재로딩 (재적용 시).

- **`macro_risk_monitor/templates/codex_review_handoff.md.j2`** — Jinja2 템플릿
  - 2026-05-27 핸드오프의 섹션 구조 그대로 모사: header → 0.목적 → 1.context → 2.검토 대상 trigger table → 4.평가 차원 → 5.가설 수준 평가 → 6.출력 형식 (markdown verdict table + **fenced JSON block 명시 요구**) → 7.유의사항.
  - JSON block schema 예시를 inline 포함해 reviewer가 그대로 emit하도록 유도.

- **`tests/unit/test_reviewer.py`** — handoff 렌더링 골든 테스트 (기존 `ai_circular_revenue.yaml` 로 생성한 결과를 fixture와 비교).
- **`tests/unit/test_review_parser.py`** — JSON block 파싱 + LLM stub fallback (anthropic 미설치 환경에서 결정론적 stub 동작 검증).
- **`tests/unit/test_patch.py`** — ruamel.yaml round-trip 시 코멘트·multiline description 보존 + diff 정확성 + apply 후 Pydantic 재검증.
- **`tests/fixtures/sample_feedback.md`** — 2026-05-27 feedback markdown 단순화 버전 + JSON block 부착.

### MODIFY

- **`macro_risk_monitor/cli.py`** — `_build_parser()`에 2개 subparser 추가, `_cmd_review_thesis`, `_cmd_apply_review` 헬퍼 추가, `main()` 분기 확장. argparse pattern은 기존 `run`/`analyze`/`pdf` 그대로 따름.
- **`macro_risk_monitor/ai/prompt_templates.py`** — `REVIEWER_PARSER_SYSTEM` 상수 + `build_review_parser_user_message(md_text)` 추가. 기존 `ANALYZER_SYSTEM` 패턴 미러링.
- **`macro_risk_monitor/schemas.py`** — `PatchAction` Enum, `PatchEntry`, `ReviewPatch` Pydantic 모델 추가 (Trigger·Threshold 재사용).
- **`pyproject.toml`** — `ruamel.yaml>=0.18,<1` 을 main dependencies에 추가. (anthropic 처럼 optional로 두면 default 설치 환경에서 apply-review가 못 돌아감 — 핵심 기능이므로 main.)
- **`CLAUDE.md`** — Session log에 본 작업 entry 추가, `## Conventions` 섹션에 "새 reviewer 종류 추가 시 `notes/codex_handoffs/{date}_{thesis}_{reviewer}_review.md` 명명 규칙" 한 줄 추가.

### NOT TOUCHED

- `sources/`, `engine/`, `output/`, `pipeline/orchestrator.py` — review/apply 흐름은 layer 간 cross-cutting 만들 필요 없음.
- 기존 `theses/*.yaml`, `data/manual_override/*.yaml` 내용 — 이번 작업은 도구만 추가, 데이터 변경은 사용자가 새 가설로 시험할 때 발생.

## Data model (schemas.py 추가분)

```python
class PatchAction(str, Enum):
    KEEP = "KEEP"
    MODIFY_THRESHOLD = "MODIFY-threshold"
    MODIFY_CATEGORY = "MODIFY-category"
    MODIFY_SOURCE = "MODIFY-source"
    REPLACE = "REPLACE"
    ADD = "ADD"

class PatchEntry(BaseModel):
    target_id: str               # REPLACE/MODIFY: 기존 trigger id; ADD: 새 id
    action: PatchAction
    new_id: str | None = None    # REPLACE 시 trigger 이름 변경
    new_series: str | None = None
    new_category: Category | None = None
    new_source: SourceKind | None = None
    new_threshold: Threshold | None = None
    new_description: str | None = None
    new_unit: str | None = None
    new_override: dict | None = None  # manual_override 항목 (value/as_of/source_url/note)
    rationale: str = ""
    unverified: bool = False     # feedback에 UNVERIFIED 플래그가 있으면 자동 skip 후보

class ReviewPatch(BaseModel):
    thesis_name: str
    reviewer: str = "codex"
    review_date: date
    entries: list[PatchEntry]
```

## Reused existing code

- **`ai/analyzer.py:22-43`** — anthropic SDK 호출 패턴 (try-import + Stub fallback + `cfg.LLM_MODEL`). `review_parser._extract_via_llm` 가 동일 구조로 복제.
- **`ai/prompt_templates.py`** — `ANALYZER_SYSTEM`/`build_analyzer_user_message` 미러링.
- **`hypothesis.py` (yaml.safe_load → Risk.model_validate)** — `apply_patch` 종료 후 재검증에 그대로 사용.
- **`engine/trigger.py:24` regex `_NUMERIC_PAT`** — patch에서 새 threshold 문자열 검증 시 import해서 사용.
- **`config.py`의 `LLM_MODEL`/`ANTHROPIC_API_KEY`** — review_parser fallback에서 그대로.
- **Jinja2** (이미 dep) — handoff 템플릿.

## CLI contract

```
# Step 1: 핸드오프 생성
$ macro-risk review-thesis ai_circular_revenue
Generated: notes/codex_handoffs/2026-05-27_ai_circular_revenue_review.md
Next: paste this file to Codex, save reply as
      notes/codex_handoffs/2026-05-27_ai_circular_revenue_review_feedback.md

# Step 2: feedback 파싱 + diff 생성 (dry-run)
$ macro-risk apply-review ai_circular_revenue \
      --feedback notes/codex_handoffs/2026-05-27_ai_circular_revenue_review_feedback.md
=== diff: theses/ai_circular_revenue.yaml ===
...unified diff...
=== diff: data/manual_override/ai_circular_revenue.yaml ===
...unified diff...
Patch staged at: notes/codex_handoffs/2026-05-27_ai_circular_revenue_review_patch.yaml
Re-run with --apply to write changes.

# Step 3a: staging file 편집 후 재적용
$ vim notes/codex_handoffs/2026-05-27_ai_circular_revenue_review_patch.yaml
$ macro-risk apply-review ai_circular_revenue \
      --patch notes/codex_handoffs/2026-05-27_ai_circular_revenue_review_patch.yaml \
      --apply

# Step 3b: feedback 그대로 적용
$ macro-risk apply-review ai_circular_revenue --feedback <path> --apply
```

`--patch <path>` flag는 편집된 staging file 재로딩 용도; `--feedback` 와 mutually exclusive.

## Verification

엔드투엔드 확인:

1. **Unit test**: `pytest tests/unit/test_reviewer.py tests/unit/test_review_parser.py tests/unit/test_patch.py`. ruamel round-trip이 `description: |` 블록과 `# 주석`을 보존하는지 golden file로 검증.
2. **기존 회귀**: `pytest tests/` 전체 — 신규 모델·CLI 추가가 기존 import 그래프를 깨지 않음을 확인.
3. **수동 e2e (existing thesis로)**:
   - `macro-risk review-thesis ai_circular_revenue` → 생성된 markdown이 2026-05-27 핸드오프와 구조적으로 동일한지 육안 확인.
   - `tests/fixtures/sample_feedback.md` 를 `--feedback` 으로 넣어 `apply-review` 실행 → diff 가 합리적인지 확인 후 `--apply` (별도 branch에서) → `git checkout -- theses/ data/` 로 복원.
4. **재검증 안전망**: apply_patch 함수가 mutate 후 `load_risk(risk_path)` 호출, Pydantic ValidationError 발생 시 원본 백업으로 자동 복원 + non-zero exit.
5. **LLM fallback 격리**: anthropic 미설치 환경에서 `_extract_via_llm`이 명확한 메시지로 fail → 사용자가 JSON block을 직접 추가하거나 staging file을 수동 작성하도록 안내.

## Open caveats

- **첫 핸드오프 파일이 유일한 reference**. Jinja2 템플릿은 2026-05-27 핸드오프를 그대로 모사하되, 2-3개 가설로 시험하며 형식이 진화할 수 있음. 템플릿 변경은 시간 흐름에 따라 일어날 것으로 가정.
- **ADD 트리거의 new_trigger 정의 완전성**: feedback이 새 trigger의 unit/description을 누락하면 ruamel은 잘 dump 하지만 Pydantic 재검증에서 실패할 수 있음. 이 경우 staging file을 사용자가 보강하는 흐름으로 처리 (자동 prompt 없음, 메시지로만 안내).
- **UNVERIFIED 플래그**: PatchEntry.unverified=True인 항목은 default로 skip + diff에 `# UNVERIFIED: ...` 코멘트로 표시. 사용자가 staging file에서 직접 활성화하도록.
- **multi-thesis 단일 feedback**: 현 설계는 1 feedback = 1 thesis. 2026-05-27 핸드오프처럼 두 가설을 함께 review하려면 두 번 호출해야 함 (혹은 향후 `--all` 옵션 추가; 이번 scope 외).
