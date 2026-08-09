# 설계안 — 최소 ScoreItem + vintage/시각 provenance (개선 #2 + #7)

**상태: 미구현.** 이 문서는 변경 파일·스키마·마이그레이션·검증 기준만 제안한다. 승인 전에는 코드를 쓰지 않는다.
근거: `2026-08-07_project_improvement_review_feedback.md` §1(#2, #7), §2(1·2·7번), §3 착수 순서, §4.3·4.4.

---

## 0. 이 설계가 풀려는 문제, 한 줄씩

1. **같은 사전 기준으로도 빈티지 선택에 따라 판정이 뒤집힐 수 있다.** P4는 여유가 0.015%p였고 기준값(5월 Core PCE)은 3.41 → 3.42로 개정됐다.
2. **`actual` 한 열이 표시문과 계산 입력을 겸한다.** `"3.2% (시간당 $37.62, 전월 +2센트)"` — 쉼표 하나로 열이 밀렸고 자동 재계산도 불가능하다.
3. **등록·발표·채점의 시간 순서를 증명할 수 없다.** `registered_on`이 날짜 단위라 FOMC 발표 전후를 구분하지 못하고, 발표일은 수기 입력이라 실제로 하루 틀렸다(7/31로 적었으나 실제 7/30).

---

## 1. 먼저 결정해야 하는 것 — 설계의 방향이 갈린다

### 결정 A. 저장 포맷: CSV 확장 vs YAML 전환

| | CSV에 열 추가 | **YAML 전환 + CSV는 표 생성용 export** |
|---|---|---|
| 마이그레이션 | 가장 쉬움 | 일회성 변환 스크립트 필요 |
| 필드 수 | 11 → **24열**. 사람이 못 읽는다 | 항목당 블록. 읽힌다 |
| 파생 입력 provenance | **표현 불가** (중첩 필요) | 자연스럽다 |
| correction ledger | 표현 불가 | 자연스럽다 |
| 쉼표/따옴표 사고 | 재발 가능 | 구조적으로 소멸 |
| 저장소 관례 | 없음 | `theses/*.yaml` + Pydantic과 동일 |

**권고: YAML 전환.** 이번에 실제로 난 사고가 CSV 인용 사고이고, 아래 §3에서 보듯 파생 지표에는 **입력별 빈티지**가 필요해서 평면 CSV로는 애초에 표현이 안 된다.

동결 증거는 파일 포맷이 아니라 **git**이 맡는다. `scorecard.csv`는 등록 커밋 시점 상태 그대로 저장소에 남겨 원본 감사물로 쓰고, 이후 작업은 `scorecard.yaml`에서 한다. 두 파일의 기준 4필드가 일치하는지는 validator가 검사한다(§4 V2).

### 결정 B. 기존 15건에 빈티지 정책을 소급 지정할 것인가

**이건 함정이다.** 지금 항목별로 빈티지 정책을 고르면, P1~P9는 이미 결과를 아는 상태이므로 **v2 기준이 오염된 것과 정확히 같은 방식으로** 오염된다. 항목마다 유리한 빈티지를 고를 수 있게 된다.

**권고:** 항목별 사전 선언은 **다음 등록분(v2)부터** 시작한다. 기존 15건에는 결과와 무관하게 서술 가능한 **단일 규칙**을 일괄 적용하고 `policy_assigned: retroactive`로 표시한다.

> **소급 규칙 (v1 전체 공통).** 판정에 쓰는 관측치는 **해당 지표의 최초 발표치(first print)** 로 한다. 비교 기준값(직전월·전년동월 등)은 **등록 시점에 공표돼 있던 값**으로 한다. 개정치는 병기하되 판정을 바꾸지 않는다.

기준값을 first print가 아니라 *등록 시점 값*으로 두는 이유는 §3의 P4 사례에 있다.

그리고 §4 V9: **소급 적용 후 9건의 판정이 하나라도 바뀌면 자동 채택하지 않고 중단·에스컬레이션한다.**

---

## 2. 스키마 (`ScoreItem`)

Pydantic. 필드를 네 묶음으로 나눈다. **등록 묶음은 동결 대상, 나머지는 추가 대상.**

```yaml
# blog/posts/2026-08_war_two_inflation_followup/data/scorecard.yaml
criteria_version: v1
registered_commit: <등록 시점 커밋 해시>
source_csv: data/scorecard.csv          # 원본 감사물
items:
  - # ── 등록 (동결) ──────────────────────────────
    id: P4
    category: 물가
    claim: Core PCE YoY가 5월 대비 유의하게 내려오지 않는다(정체)
    source_post_section: 4장
    registered_at: 2026-07-28T16:37:56+00:00   # 등록 커밋 66fd5e08의 시각 (자기신고 아님)
    registered_at_source: commit               # commit | self_reported
    # FOMC 발표는 2026-07-29T18:00Z — 등록이 약 25시간 앞섰음이 커밋으로 증명된다.
    criterion_hit: 5월 대비 -0.15%p 이내
    criterion_miss: -0.15%p 초과 하락

    # ── 대상 유형과 빈티지 정책 ──────────────────
    target_type: release_outcome        # release_outcome | economic_state | policy_text
    vintage_policy: first_print         # first_print | current | as_registered
    policy_assigned: retroactive        # prospective | retroactive
    judgment: mechanical                # mechanical | manual

    # ── 발표 provenance ─────────────────────────
    release:
      source_url: https://www.bea.gov/news/2026/personal-income-and-outlays-june-2026
      scheduled_at: 2026-07-31          # 등록 당시 적어둔 예정일 (틀렸다)
      actual_at: 2026-07-30T08:30:00-04:00
      schedule_error_days: -1           # validator가 계산해 채움

    # ── 관측 ────────────────────────────────────
    observation_period: 2026-06
    inputs:                             # 파생 지표는 입력별 빈티지가 따로 필요하다
      - role: current
        series: PCEPILFE
        observation_period: 2026-06
        vintage: first_print
        value: 3.29
      - role: base
        series: PCEPILFE
        observation_period: 2026-05
        vintage: as_registered          # 등록 시점(2026-07-28)에 공표돼 있던 값
        value: 3.41
    actual_value: -0.12
    actual_unit: '%p'
    actual_display: '-0.12%p (5월 3.41% → 6월 3.29%, 모두 발표 시점 값)'
    actual_current: -0.135              # 개정 반영 이중 장부
    vintage_divergence: false           # true면 두 빈티지가 판정을 가른다는 뜻
    margin_to_threshold: 0.03           # 기준선까지 남은 거리 — 아슬아슬한 적중을 드러낸다

    # ── 채점 ────────────────────────────────────
    scored_at: 2026-08-01T00:00:00+09:00
    verdict: 적중
    note: |
      ...

    # ── 정정 원장 (원본 수정 금지) ───────────────
    corrections: []                     # {corrected_on, reason, field, from, to, supersedes}
```

**설계 근거 몇 가지.**

- `registered_at_precision: day` — v1 등록은 실제로 날짜 단위였다. 분 단위인 척하지 않는다. v2부터 `minute`.
- `vintage_policy`가 항목 하나에 하나뿐인 게 아니라 **`inputs[].vintage`가 진짜 계약**이다. 항목 수준 값은 요약 표시용.
- `margin_to_threshold` — "적중의 난이도"를 사람이 서술하는 대신 기계가 낸다. P4의 0.03%p, P2의 판정 재량이 표에 자동으로 드러난다.
- `judgment: manual`은 P2처럼 수치가 없는 항목용. `actual_value: null` 허용하되 `note` 필수.
- `corrections[]` — 오타도 원본을 고치지 않는다(피드백 §2-1번 권고).

---

## 3. P4가 왜 이 설계를 강제하는가 (워크드 예제)

| 계산 방식 | 기준(5월) | 관측(6월) | 차이 | 기준선까지 |
|---|---|---|---|---|
| `as_registered` 기준 (**권고**) | **3.4120** (등록 스냅샷) | 3.2865 (first print) | **−0.1255%p** | 0.0245%p |
| 현재 계열 기준 (이번에 기입한 값) | 3.4216 (개정) | 3.2865 | −0.1350%p | 0.0150%p |
| 순수 first print 기준 | 5월의 first print(≈6/26 발표치, **미확인**) | 3.2865 | ? | ? |

**`as_registered` 값은 외부 조회 없이 저장소 안에서 재현된다.** 등록 커밋 `66fd5e08`의 `blog/posts/2026-07_war_two_inflation/data/s2_inflation.csv`에 `2026-05-01, core_pce_yoy = 3.412035932904045`가 들어 있고, 같은 커밋의 `manifest.json`에 `PCEPILFE last_obs=2026-05-01, last_value=130.082`가 있다. 현재 FRED 값은 130.094 — **지수가 130.082 → 130.094로 개정됐고 그것이 3.41 → 3.42의 정체다.**

즉 v1 15건에 대해서는 **ALFRED가 필요 없다.** `data/*.csv` + `manifest.json`이 이미 등록 시점 빈티지 스냅샷이다. `inputs[].vintage: as_registered`는 `<registered_commit>:blog/.../data/<file>.csv`를 가리키면 되고, validator가 그 값을 실제로 읽어 대조할 수 있다(§4 V5 강화). ALFRED는 이 스냅샷이 없는 미래 지표에만 필요하다.

세 번째 행이 핵심이다. **"모든 입력에 first print"를 기계적으로 적용하면 5월값으로 6월 26일 발표치를 써야 하는데, 그건 예측자가 7월 28일에 보고 있던 숫자가 아니다.** 예측은 "3.41에서 안 내려온다"였다. 그러니 기준값의 올바른 빈티지는 first print가 아니라 **`as_registered`** 다.

즉 **"first print로 통일"이라는 단순 규칙은 틀렸다.** 관측치는 first print, 기준값은 as_registered — 역할별로 다르다. 이것이 `inputs[].role`과 `inputs[].vintage`를 분리하는 이유다.

세 방식 모두 판정은 **적중**으로 같다(§4 V9 통과). 그러나 기준선까지의 여유가 0.015~0.03%p로 갈리므로, 어느 숫자를 본문에 적는지는 정직성의 문제다.

**같은 문제가 P8에도 있다.** `NILFWJN YoY = 2026-07(5,920) − 2025-07(6,186)`인데, 그 사이에 **2026년 1월 인구통제 재기준화**가 끼어 있다(원글 6장이 인구설 기여율을 뺀 바로 그 이유). 전년 값이 재기준화 후 계열이면 YoY 자체가 단절을 건너뛴다. → §6 미결 3.

---

## 4. 검증 기준 (validator가 실패시켜야 하는 것)

| ID | 규칙 | 실패 시 |
|---|---|---|
| **V1** | Pydantic 타입·enum·필수 필드 | ERROR |
| **V2** | 등록 묶음 6필드가 `git show <registered_commit>:<source_csv>`의 값과 일치 | ERROR (단, 대응하는 `corrections[]` 항목이 있으면 WARN) |
| **V3** | `registered_at < release.actual_at <= scored_at`, 전부 tz-aware | ERROR |
| **V4** | `verdict`가 있으면 `release.actual_at`이 반드시 있음 — **`resolve_on <= today`로 검사하지 않는다** (발표가 당겨지거나 예정일이 틀리면 옳은 채점을 거부하므로) | ERROR |
| **V5** | `vintage_policy`가 요구하는 `inputs[]`가 모두 있고 각 입력에 `series`·`observation_period`·`vintage` 존재 | ERROR |
| **V6** | `actual_current`가 있을 때, 그 값으로 재판정하면 verdict가 바뀌는 경우 `vintage_divergence: true`가 있어야 하고 본문 표에 두 값 모두 표시 | ERROR |
| **V7** | `judgment: mechanical`이면 `criterion_hit`이 `actual_value`로 기계 평가 가능 / `manual`이면 `note` 필수 | ERROR |
| **V8** | `release.scheduled_at ≠ release.actual_at`이면 `schedule_error_days` 기록 | WARN |
| **V9** | **마이그레이션 전용.** 기존 9건을 새 정책으로 재판정했을 때 verdict가 하나라도 바뀌면 마이그레이션 중단 | ABORT |
| **V10** | `id` 유일성, 15건 고정, `verdict ∈ {적중, 빗나감, 판정불가, 미도래}` | ERROR |

`margin_to_threshold`는 검증이 아니라 **계산 출력**이다. 값이 작으면 본문에 자동으로 "여유 N" 표기를 넣을 근거가 된다.

---

## 5. 변경 파일

| 파일 | 상태 | 내용 |
|---|---|---|
| `blog/posts/2026-08_war_two_inflation_followup/data/scorecard.yaml` | **신규** | 작업용 정본 |
| `.../data/scorecard.csv` | **동결** | 등록 커밋 상태 유지. 감사물. 이후 수정 금지 |
| `blog/tools/scorecard_schema.py` | 신규 | `ScoreItem`·`Correction`·`ReleaseInfo`·`Input` Pydantic 모델 |
| `blog/tools/validate_scorecard.py` | 신규 | V1~V8·V10. 종료코드로 CI 연결 가능 |
| `blog/tools/migrate_scorecard_v1.py` | 신규(일회성) | CSV 15행 → YAML. V9 포함. **`--dry-run` 기본** |
| `blog/tools/export_scorecard_table.py` | 신규 | YAML → 본문 markdown 표. 손으로 표를 고치지 않게 된다 |
| `tests/unit/test_scorecard_schema.py` | 신규 | 저장소 첫 블로그 테스트. 최소 3건: 열 밀림 재현 케이스, V3 시간 역전, V6 빈티지 분기 |
| `blog/posts/2026-08_war_two_inflation_followup/post.md` | 수정 | 1장 표를 생성물로 표시(주석). 본문 텍스트는 무변경 |
| `notes/codex_handoffs/2026-08-07_scoreitem_provenance_design.md` | 신규 | 이 문서 |

**패키지에는 넣지 않는다.** `blog/tools/`는 독립 스크립트로 두고 `macro_risk_monitor`를 import하지 않는다 — 피드백 §2-1번의 "통합하지 말 것"과 일치. 다만 `pyproject.toml`에 ruff/pytest 경로만 추가할지는 §6 미결 2.

---

## 6. 마이그레이션 절차

1. `registered_commit` **확정됨** — `66fd5e08` (2026-07-28, "blog: 글 B 개정 — 노동 '완충' 해석 정정, 차트 S10·S11 추가, 사후검증 글 스켈레톤"). `scorecard.csv`가 저장소에 처음 들어온 커밋이고, 등록일 2026-07-28과 일치한다. **등록이 결과 발표(7/29 FOMC)보다 앞섰다는 사실이 이 커밋으로 증명된다** — 사전등록 주장의 실제 증거는 CSV의 `registered_on` 열이 아니라 이 해시다.
2. `--dry-run`으로 15행 변환, 9건 재판정, **V9 확인.** 판정 변화 0건이어야 진행.
3. 발표 provenance 수집 — 이미 확보된 것: P1·P2 = 2026-07-29 14:00 EDT(연준), P3·P4 = 2026-07-30 08:30 EDT(BEA), P5~P9 = 2026-08-07 08:30 EDT(BLS). `scheduled_at`은 등록 당시 `resolve_on` 값을 그대로 넣어 **오차가 남도록** 한다(P3·P4가 −1일).
4. `scored_at` — 커밋 시각을 그대로 쓴다. P1~P4 = `2026-08-01T11:20:18Z` (`70e8238`), P5~P9 = `2026-08-07T19:54:33Z` (`92a8b15`). 자기신고 날짜가 아니라 커밋 시각이라 V3(`registered_at < released_at < scored_at`)을 외부에서 검증할 수 있다.
5. `actual` 산문을 `actual_value`/`actual_unit`/`actual_display`로 분해. **`actual_display`에 기존 문자열을 그대로 보존**해 정보 손실 0.
6. 미도래 6건(P10~P15)은 등록 묶음만 채우고 나머지 null.
7. validator 통과 후 커밋. CSV는 건드리지 않는다.

---

## 7. 승인이 필요한 미결 사항

1. **결정 A — YAML 전환 vs CSV 24열.** 권고는 YAML. 반대라면 파생 입력 provenance(§3)를 포기해야 하고, 그러면 P4·P8을 정확히 기록할 방법이 없다.
2. **`blog/tools/`를 CI(`ruff` + `pytest`)에 물릴 것인가.** 물리면 블로그 데이터 오류가 push 시점에 잡힌다. 대신 블로그 작업이 저장소 CI를 깨뜨릴 수 있다.
3. **P8의 인구통제 단절.** 2026-01 재기준화를 건너뛰는 YoY를 (ㄱ) 그대로 두되 `note`에 단절 표기, (ㄴ) `판정불가`로 강등, (ㄷ) 재기준화 전후를 각각 계산해 병기 — 어느 쪽인가. **이건 판정을 바꿀 수 있으므로 결과를 본 뒤 고르면 안 된다.** 지금 정하면 소급 선택이 되므로, v1은 (ㄱ)로 두고 v2부터 규칙화하는 쪽을 권고한다.
4. **소급 적용 표기를 본문에 실을 것인가.** `policy_assigned: retroactive`는 데이터에는 남는다. 채점 글 4-3에 "v1 15건의 빈티지 정책은 사후에 일괄 지정했다"를 한 문장 넣을지는 별개 결정.

---

## 8. 이 설계가 아직 안 다루는 것

#4(관측 예측 / 메커니즘 주장 / 논지 전환 규칙 분리, `dependency_group`)와 #5(수치 verifier)는 범위 밖이다. 다만 스키마에 `dependency_group`·`supports_claim` 슬롯을 **지금 비워서라도 넣어둘지**는 검토 가치가 있다 — 나중에 넣으면 또 한 번 마이그레이션이다. 권고: 슬롯만 예약하고 값은 v2부터.
