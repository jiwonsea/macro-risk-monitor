# 인계 메모 — 두 개의 인플레이션 채점 작업 (2026-08-07 기준)

새 세션에서 이 작업을 이어받을 때 **이 파일 하나만 읽으면 시작할 수 있게** 쓴 메모다.
저장소는 `F:\dev\Portfolio\macro-risk-monitor` (git, 브랜치 `main`).

---

## 1. 지금까지의 커밋

| 해시 | 내용 |
|---|---|
| `752da3a` | 2차 개정 — Codex 전면 리뷰(39/60) 반영 |
| `f472d9e` | 4장 귀속 모순·인과 단정 2건 정정 |
| `70e8238` | P1~P4 채점 기입 (7/29 FOMC, 6월 Core PCE) |
| `6c325c3` | **개정 기록을 본문에서 분리 — 완성본만 발행** |
| `46e2589` | 계절조정 각주 삭제, 0.05%p 대조만 웨지 문단으로 이동 |
| (이번) | P5~P9 채점 기입 (7월 고용상황) |

---

## 2. 파일 지도

```
blog/posts/2026-07_war_two_inflation/          # 원글 (발행됨, 재업로드 대기)
  post.md                    23.4KB. 개정 기록 없음. 완성본만.
  naver_repost_2026-08-01.md 유효한 업로드 지시서 (전체 교체 방식)
  naver_repost_2026-07-{28,31}.md  폐기됨. 배너 붙어 있음.
  charts/S1..S11_*.png       차트 11장. 번호는 파일명·엑셀 시트명과 묶인 고정 식별자.
  collect.py                 읽기 전용. 네트워크 필요.
  charts.py / workbook.py    HERE = Path(__file__).parent — 다른 데 복사하면 깨진다.
  data/*.csv

blog/posts/2026-08_war_two_inflation_followup/ # 사후검증(채점) 글, 미발행
  post.md                    status: scoring
  data/scorecard.csv         ★ 기준 열 동결. actual·verdict·note만 채운다.
  data/scorecard_criteria_v2.csv  다음 글부터 적용할 엄격한 기준.

notes/codex_handoffs/        검증·개정 기록의 보관처
```

---

## 3. 절대 어기면 안 되는 규칙

1. **`data/scorecard.csv`의 `criterion_hit`·`criterion_miss`·`registered_on`·`resolve_on`은 손대지 않는다.** 2026-07-28에 결과를 보기 전 등록한 값이다. 결과를 본 뒤 기준을 고치면 채점 자체가 무의미해진다. 채우는 건 `actual`·`verdict`·`note` 세 열뿐이고, 커밋 전 `git diff`로 앞 네 열이 안 바뀌었는지 확인한다.
2. **P13은 논리식이 뒤집혀 있지만 이번 라운드에서 고치지 않는다.** v2에 바로잡아 등록해뒀고 다음 글부터 적용한다.
3. **원글 본문에 개정 과정을 다시 넣지 않는다.** 완성된 판단만 싣는다. 예외는 5장 검증 기록 — 이건 글을 고친 과정이 아니라 숫자를 검증한 과정이라 남긴다.
4. **차트 번호(①~⑪, S1~S11)는 절대 다시 매기지 않는다.** 본문 순서와 어긋나는 건 의도된 것이다.

---

## 4. 채점 현황 (9/15 확정)

| | 해소일 | 결과 |
|---|---|---|
| P1 P2 | 7/29 | 적중 — 3.50–3.75% 동결(9-3, **반대 3표가 모두 25bp 인상**) |
| P3 P4 | 7/30 | 적중 — 6월 Core PCE **3.29%**, 5월 대비 **−0.135%p**(기준선까지 0.015%p) |
| P5~P9 | 8/7 | 적중 — EMRATIO **58.9**, CIVPART **61.4**, UNRATE **4.1**, NILFWJN YoY **−266k**, AHE YoY **3.2%** |
| P10 P14 | 8/12~13 | 미도래 (7월 CPI) |
| P11 P12 P13 P15 | 8/31 | 미도래 |

**9적중 0빗나감이지만 논지는 흔들렸다.** 8/7에 비농업 고용이 **−23k**로 돌아섰고 5월 129k→63k, 6월 57k→20k로 하향 개정됐다(합계 −103k). 원글 6장이 tail과 base를 가른 근거는 "해고가 아니라 노동공급 축소"였는데, 그 구분이 이번 달 데이터로는 유지되기 어렵다. 그런데 P5~P9는 전부 "수준이 이 선 아래인가"만 물어서 이 사실을 한 칸도 잡지 못했다. **다음 세션의 핵심 논점이 이것이다.**

원글 6장의 고용 시퀀스는 개정으로 `214k → 148k → 63k → 20k → −23k`가 됐다. 원글 본문은 발표 시점 값을 그대로 두고, 개정분은 채점 글에서 다룬다.

---

## 4-b. 채점 체계 개선 — Codex 리뷰 완료 (반드시 먼저 읽을 것)

`notes/codex_handoffs/2026-08-07_project_improvement_synthesis.md` (핸드오프·피드백 원본은 같은 폴더).

**내가 틀렸던 것 3건 — 다시 제안하지 말 것.** (ㄱ) 블로그 채점을 본체 `engine/trigger.py`에 통합 — 대상이 다르다(연속 상태 vs 시점 예측). (ㄴ) v2 P13이 현재 데이터로 충족됐다 — 지표·임계·평가창이 미정의라 "재평가 게이트가 열렸다"까지만 말할 수 있다. (ㄷ) draft 두 개를 `theses/`로 승격 — 차단 사유가 percentile·gate·source 미지원이라 위치 문제가 아니다.

**리뷰가 지목한 진짜 병:** 한 CSV에 세 의미가 섞여 있다 — ①예측 사건이 발생했는가 ②그것이 논지를 지지하는가 ③논지가 tail→base로 바뀌었는가. 9적중과 논지 약화의 공존이 여기서 나온다.

**착수 순서 (리뷰 권고): 2 → 7 → 1 → 4 → 3 → 5 → 6. 하나만 한다면 2번.**

## 5. 남은 작업

- [ ] **8/7 고용지표 중간 글** — 원글이 "여기가 도미노의 트리거"라고 지목한 날이므로 별도 글로 다룰지 결정. 채점 글(8/13)과 중복되지 않으려면 *판단*(tail을 base로 바꾸는가)을 다루고, 채점 글은 *결산*을 다룬다.
- [ ] **8/12~13** — P10·P14 기입 후 채점 글 발행.
- [ ] **8/31** — P11·P12·P13·P15 추기.
- [ ] **네이버 재업로드** — `naver_repost_2026-08-01.md` 절차. 본문 전체 교체 + 이미지 11장(S7·S9·S10·S11만 필수 교체).
- [ ] 마이다스 지원서에서 후속글 링크.
- [ ] `fed_path_reaccel_risk` v3 · `uncertainty_stagflation_domino`를 DRAFT → `theses/`로 승격.
- [ ] `collect.py`에 `CPILFESL` 추가 (SA/NSA 대조를 `data/`만으로 재현할 수 있게).
- [ ] **[개선 2번 — 최우선]** `scorecard.csv`에 `observation_period`·`released_at`·`retrieved_at`·`vintage_policy`·`actual_first_print`·`actual_current` 추가하고 `actual`을 `actual_value`/`actual_unit`/`actual_display`로 분해. **적중률은 first print 고정, 논지 평가는 current vintage — 이중 장부.** 빈티지 정책은 지표별 사후 선택이 아니라 **예측 대상별 사전 선언**.
- [ ] **[개선 7번]** 공식 release URL·실제 발표 시각 기록 + `registered_at < released_at <= scored_at` 검사. (`resolve_on > today`인데 verdict 있으면 실패는 불충분 — 발표가 당겨지면 옳은 채점을 거부한다.)
- [ ] **[개선 1번]** `ScoreItem` Pydantic + `blog/tools/validate_scorecard.py`. 기준 동결은 별도 해시 대신 **`registered_commit` + `git show`** 대조. 오타는 원본 수정이 아니라 `correction_reason`/`corrected_on`/`supersedes` 추가로.
- [ ] **[개선 4번]** `supports_claim`·`evidence_direction`·`dependency_group`(P5·P6·P7은 같은 그룹)·`thesis_transition_rule`.
- [ ] **[개선 5번]** 숫자 검증 공용 코어 추출 + `value/unit/claim/source_url/as_of` 구조의 allowlist. `ai/verifier.py` 직접 재사용은 불가.
- [ ] **사용자가 직접 `F:\dev\Portfolio\macro-risk-monitor\_to_delete\` 삭제** (`gitlocks_*` 16개 이상).

---

## 6. 환경 주의사항 (클라우드 세션에서 작업할 때)

- **FRED 직접 호출이 막혀 있다.** `collect.py`는 프록시 403(`Tunnel connection failed`)으로 실패한다. 대신 **WebFetch로 `https://fred.stlouisfed.org/data/<SERIES_ID>`** (HTML 관측치 표)를 읽으면 된다. `fredgraph.csv`는 바이너리로 와서 안 된다. 프록시 우회는 시도하지 않는다.
- **`device_commit_files`의 `devicePath`는 윈도우 경로**(`F:\dev\...`)여야 한다. 리눅스 마운트 경로가 아니다. 흐름: 컨테이너에서 작업 → `SendUserFile`로 `file_uuid` 확보 → `device_commit_files`.
- **git 작업 때마다 lock 파일이 남는다.** 매번 앞뒤로 이렇게 치운다:
  ```
  mkdir -p _to_delete/gitlocks_X
  for f in .git/HEAD.lock .git/index.lock; do [ -e "$f" ] && mv "$f" _to_delete/gitlocks_X/; done
  ```
  `warning: unable to unlink '.git/objects/**/tmp_obj_*'`는 무시해도 커밋은 성공한다. **마지막 git 작업 뒤에도 반드시 한 번 더 치운다** — 안 그러면 사용자 로컬 git이 막힌다.
- **스테이징은 항상 경로를 명시한다.** 저장소에 무관한 dirty 파일이 있다: `CLAUDE.md`, 루트 `README.md`, `tests/unit/test_hypothesis_loader.py`. 절대 같이 커밋하지 않는다.
- `device_bash`는 파일을 지우지 못한다. 삭제 대신 `_to_delete/`로 `mv` 한다.

---

## 7. 이 글들의 성격 (톤 유지용)

개인 투자 기록이고, **틀린 것을 남기는 것이 목적**인 글이다. 유리한 재료라도 원인을 확정하지 못했으면 "증거로 쓰지 않는다"고 적고 감시 목록으로 내린다. 출처를 못 찾은 숫자는 지우지 말고 **미검증**으로 표시한다. 적중을 자랑으로 쓰지 않고 **적중의 난이도**를 같이 적는다. AI 검증은 순차 교차검증(Claude → Codex 반박)이며, 병렬이 아니다.
