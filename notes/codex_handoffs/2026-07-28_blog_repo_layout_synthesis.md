# Synthesis — blog/ 디렉터리 구조 재설계 (Claude × Codex)

**Date**: 2026-07-28
**입력**: `2026-07-28_blog_repo_layout_review.md`(Claude 제안) × `..._review_feedback.md`(Codex 반박)
**결론**: **C-lite hybrid 채택** + Claude 수정 2건(A1·A2)

---

## 1. Claude가 철회한 것

| # | Claude 원 주장 | Codex 반박 | 판정 |
|---|---|---|---|
| 1 | 글 폴더 = 발행본 불변 스냅샷 | 글 B는 관찰 캘린더대로 4회 갱신 예정. 폴더는 스냅샷 경계가 아니라 **변경되는 작업 단위**. 같은 파일명으로 다시 저장하면 flat과 똑같이 이전 상태가 소멸 | **철회** |
| 2 | (스냅샷이 필요하면) `charts/_published/<date>/` | PNG만 동결하면 본문·CSV·xlsx와 짝이 안 맞는 **불완전 스냅샷**. 필요해지면 **git tag / release commit**이 네 가지를 함께 고정하므로 우월 | **철회, Codex안 채택** |
| 3 | 마이그레이션 비용 ≈ 0 | git 히스토리 비용만 본 것. 글 A 상대링크 5개, 두 스크립트의 CWD 의존, 글 B 절대경로, refresh handoff의 실행 경로, xlsx 락 처리가 남음 | **정정: 낮지만 0 아님** |
| 4 | `_lib/`에 style/title/foot/dlabel/save 공용화 | 글 2편으로는 근거 부족. 글 A·B가 제목 크기·레이아웃·라벨 방식·DPI가 모두 다름 → 곧 옵션 지옥 | **철회 (rule of three 적용)** |
| 5 | 글 A 팔레트를 Okabe-Ito로 통일 | 발행본과 로컬의 대응이 깨짐. 색상 변경은 구조 이동이 아니라 **별도 콘텐츠 개정** | **철회** |
| 6 | export 계층 / slug 접두사 검토 | 업로드가 수동인데 동일 PNG 복제본을 관리할 가치 없음. 필요 시 그때 zip으로 slug 부여 | **철회** |

Claude가 제시한 근거 4개 중 **"불변 스냅샷"이 무너졌고**, 남은 유효 근거는 **① 글 단위 탐색·재현**, **② 파일명 충돌 방지** 둘이다. Codex 지적대로 **폴더 재배치가 코드 중복 제거를 강제하지는 않는다** — `_lib/`은 독립 결정이다.

## 2. Codex 결론 중 그대로 채택

- **구조**: `blog/posts/<slug>/{data,charts,out}` + 루트 `README.md` 인덱스. A(현행 유지)는 기각 — "5편까지 기다린다"는 문제를 검증하는 기간이 아니라 **이동량을 늘리는 기간**이다.
- **L3**: 레포 내부는 짧은 이름 유지, `S1..S9` 번호 유지(PNG·본문 차트번호·xlsx 시트명의 공통 계약).
- **L4**: post front-matter 단방향 링크. thesis 스키마 무변경 — 엔진이 산출물을 역참조하면 4-layer 분리가 깨진다.
- **L5**: `commit_all` (lock/cache 제외). 20편 ≈ 35MB는 일반 git으로 충분, LFS 불필요.
- **L6**: 글 A는 **이동 + 경로 수정까지만**. 발행일 증거가 없으므로 날짜를 발명하지 않고 월 단위 slug `2026-07_labor_health` 유지.
- **우선순위**: 두 draft thesis 작업보다 위로 올리지 않는다. 짧은 독립 정리로 끝낸다.

## 3. Claude 수정 2건

### A1. `_lib/`은 **글 B를 같은 패스에서 연결할 때만** 만든다

Codex 계획의 6단계는 `_lib/`(폰트 탐색·색상 상수·rcParams)을 추가하되 **글 A는 재렌더링하지 않는다**고 했고, 글 B 연결은 언급이 없다. 그러면 **아무도 쓰지 않는 `_lib/`이 남는다** — 추상화 비용만 지불하고 이득이 0인 최악의 상태다. rule of three는 `_lib/`의 *내용*뿐 아니라 *존재*에도 적용된다.

선택은 둘 중 하나여야 한다:

- **A1-a**: `_lib/` 생성 + **글 B의 `charts.py`·`workbook.py`를 즉시 연결**. 글 B는 어차피 7/29부터 4회 재빌드하므로 유일한 활성 소비자다. 글 A는 legacy로 그대로 둔다.
- **A1-b**: 이번 라운드에서 `_lib/` **생성 안 함**. 구조 이동만. 세 번째 글에서 실제 중복이 확인되면 그때 만든다.

**둘 다 정합적이며, 어느 쪽도 "빈 `_lib/`"보다 낫다.**

### A2. 실행 시점 — **7/29 FOMC 이전(오늘)**

Codex 피드백에 시점 논의가 없다. 그러나 내일 7/29 FOMC를 시작으로 8월 중순까지 **4회의 갱신이 정확히 이동 대상 파일들을 건드린다**. 마이그레이션이 갱신 사이클과 겹치면 "어느 경로가 최신인가"가 매번 흔들린다.

→ **오늘 이동을 끝내고, 첫 갱신(7/29)이 새 레이아웃에 착지하게 한다.** 오늘 못 하면 8월 중순 CPI 이후로 미루는 게 낫다(사이클 중간 이동 금지).

## 4. L5 재생성 신뢰성 — 정밀화

Codex의 `L5_regeneration_reliable: false`는 **결론은 맞지만 근거가 부분적으로 어긋난다.**

- Codex 근거: "현재 Windows 작업환경에서 Linux 폰트 경로 의존 → 재생성 불가."
- 실제 분업: **수집(네트워크)은 사용자 로컬/Codex, 차트·엑셀 빌드는 Claude의 Linux 컨테이너**다. 따라서 `NanumGothic.ttf` 경로는 오늘 기준 **정상 동작**한다(글 B는 이 경로로 방금 재빌드했다).
- 진짜 취약점은 다른 데 있다: ① 빌드가 Claude 컨테이너라는 **단일 환경에 묶여 있다** ② 글 A의 `NotoSansCJK-Regular.ttc`는 이 컨테이너에서도 **이름 해석 실패 이력**이 있다 ③ 수집이 네트워크·upstream 개정에 의존해 과거 값 복원이 보장되지 않는다.

→ 결론 `commit_all`은 유지(오히려 ①·③ 때문에 더 강한 근거다). 다만 `_lib/`의 폰트 탐색을 만든다면 목적은 "Windows 대응"이 아니라 **빌드 환경 잠금 해제**로 적어야 한다.

## 5. 확정 실행 순서

Codex 9단계를 채택하되 A1·A2를 반영:

1. 사용자가 `war_two_inflation_data.xlsx`를 저장·종료 → `~$` 락파일 소멸 확인 (락파일 강제 이동·삭제 금지)
2. `blog/posts/2026-07_labor_health/`, `blog/posts/2026-07_war_two_inflation/` 생성 후 파일 분류 이동
3. Markdown 이미지 링크, 각 스크립트의 `DATA`/`OUT`을 `Path(__file__).resolve().parent` 기준으로 수정 — **글 B의 `/home/claude/blog/...` 절대경로와 글 A의 CWD 의존은 구조 취향과 무관한 이식성 버그**
4. `2026-07-28_blog_monitoring_refresh_handoff.md`의 실행 경로 갱신
5. `blog/README.md` 인덱스 + post front-matter(`published`, `data_as_of`, `theses`)
6. **A1 선택에 따라**: (a) `_lib/` 생성 + 글 B 연결 / (b) 생략
7. 오프라인 검증 — 모든 로컬 링크·CSV/JSON 입력 경로
8. 글 B chart/workbook 빌드 실행 → 새 위치에만 산출되는지 확인 (네트워크 수집은 미실행)
9. `git status`로 lock/cache 제외 확인 후 커밋

## 6. 미결 (사용자 승인 필요)

- **A1-a / A1-b** 선택
- A2 시점 승인 (오늘 실행)
- xlsx 종료 (Codex가 지목한 실행 전 조건)

```verdict
{
  "recommended_option": "hybrid_C_lite",
  "claude_retracted": ["snapshot_boundary", "published_png_freeze", "migration_cost_zero", "wide_lib_scope", "unify_post_a_palette", "export_layer"],
  "codex_adopted": ["posts_slug_isolation", "readme_index", "short_names", "keep_S_numbering", "frontmatter_oneway_thesis_link", "commit_all", "post_a_move_only", "no_month_date_invention", "priority_below_draft_theses"],
  "claude_amendments": {
    "A1": "create _lib only if post B is wired to it in the same pass; otherwise skip until post 3",
    "A2": "execute migration today, before the 7/29 FOMC refresh; otherwise defer past mid-Aug CPI"
  },
  "L5_refinement": "regeneration is unreliable because the build is pinned to a single Claude container and post A's font name fails there — not because of Windows; commit_all stands with stronger grounds",
  "pending_user_decisions": ["A1-a or A1-b", "approve today execution", "close open xlsx"],
  "ready_to_implement": false
}
```
