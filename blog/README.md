# blog/ — 발행 글 아카이브

이 레포의 **콘텐츠 레이어**다. `macro_risk_monitor/`의 4계층 파이프라인(Risk → Reading → Verdict → Decision → Report)과는 분리되어 있으며, 엔진이 이 폴더를 참조하지 않는다. 링크는 **글 → thesis 단방향**이다(각 글의 front-matter `theses`).

## 규칙

- 글 하나 = 폴더 하나: `posts/<YYYY-MM>_<slug>/`
- 그 글의 **데이터·차트·스크립트·산출물이 모두 그 폴더 안에** 있다. 폴더 밖을 참조하지 않는다.
- 모든 스크립트 경로는 `Path(__file__).resolve().parent` 기준. **어느 CWD에서 실행해도 동일하게 동작**한다.
- 차트 번호(`S1..S9`, `c2-1..c2-5`)는 PNG 파일명 · 본문 차트 마커 · 엑셀 시트명이 공유하는 계약이다. 바꾸지 않는다.
- 재생성이 보장되지 않으므로(수집이 네트워크·upstream 개정에 의존) **CSV·PNG·xlsx를 모두 커밋한다.** 제외 대상은 `__pycache__/`와 엑셀 락파일(`~$*.xlsx`)뿐이다.
- 발행본 스냅샷이 필요하면 `_published/` 같은 별도 폴더가 아니라 **git tag**를 쓴다. 본문·CSV·차트·스크립트가 함께 고정되어야 의미가 있기 때문이다.

## 폴더 구조

```
blog/
├── README.md                   ← 이 파일 (인덱스)
├── naver_blog_plan.md          ← 3부작 시리즈 공통 plan (글 단위가 아니라 시리즈 단위)
└── posts/
    └── <YYYY-MM>_<slug>/
        ├── post.md             본문 (front-matter + 차트 마커)
        ├── collect.py          원출처 수집 → data/ (네트워크 필요, 글에 따라 없을 수 있음)
        ├── charts.py           data/ → charts/*.png
        ├── workbook.py         data/ → out/*.xlsx (글에 따라 없을 수 있음)
        ├── data/               CSV + annotations.json + manifest.json
        ├── charts/             네이버 업로드용 PNG
        └── out/                엑셀 등 부가 산출물
```

## 글 목록

| 발행 | slug | 제목 | 차트 | 데이터 기준 | 상태 |
|---|---|---|---|---|---|
| 2026-07-28 | [`2026-07_war_two_inflation`](posts/2026-07_war_two_inflation/post.md) | 골드만은 '전쟁'을 말했다 — 나는 두 개의 인플레이션을 본다 | S1~S9 (9장) + xlsx | 2026-07-28 | **발행됨 / 갱신 예정** |
| 미상 | [`2026-07_labor_health`](posts/2026-07_labor_health/post.md) | "고용 불안 완화"라는 착시 — 노동시장 건전성을 뜯어보다 | c2-1~c2-5 (5장) | 2026-07-09 | legacy (재렌더링 안 함) |

`2026-07_labor_health`는 발행 증거가 없어 날짜를 발명하지 않고 월 단위 slug만 유지한다. 네이버 발행본 이미지와 로컬 PNG의 대응을 유지하기 위해 팔레트·폰트를 글 B와 통일하지 않는다.

## 갱신 사이클 (글 B)

`2026-07_war_two_inflation`은 본문 결론의 관찰 캘린더에 따라 갱신된다. 절차는 [`notes/codex_handoffs/2026-07-28_blog_monitoring_refresh_handoff.md`](../notes/codex_handoffs/2026-07-28_blog_monitoring_refresh_handoff.md).

| 날짜 | 릴리즈 | 영향 |
|---|---|---|
| 7/29 | FOMC | S1 |
| 7/31 | 6월 Core PCE | S2, S9 |
| 8월 초 | 7월 고용 | S7, S9 (도미노 트리거) |
| 8월 중순 | 7월 CPI | S2, S9 |
| 상시 | 장기 앵커(T5YIFR·SCE) | S5, S9 |

## 구조 결정 근거

`blog/`가 flat 구조에서 `posts/<slug>/`로 이동한 경위와 기각된 대안(스냅샷 폴더, export 계층, 광범위 `_lib/`)은 다음 3개 문서에 있다.

- [`2026-07-28_blog_repo_layout_review.md`](../notes/codex_handoffs/2026-07-28_blog_repo_layout_review.md) — Claude 제안
- [`2026-07-28_blog_repo_layout_review_feedback.md`](../notes/codex_handoffs/2026-07-28_blog_repo_layout_review_feedback.md) — Codex 반박
- [`2026-07-28_blog_repo_layout_synthesis.md`](../notes/codex_handoffs/2026-07-28_blog_repo_layout_synthesis.md) — 종합 (C-lite hybrid 채택)

공용 모듈 `_lib/`은 **만들지 않기로 결정**했다([핸드오프](../notes/codex_handoffs/2026-07-28_blog_lib_decision_handoff.md) · [Codex 판정](../notes/codex_handoffs/2026-07-28_blog_lib_decision_handoff_feedback.md)). 활성 chart builder는 글 B 하나뿐이라 rule of three가 성립하지 않고, 실제 문제였던 폰트 경로 하드코딩은 글 B 안에서 후보 순회로 고쳤다. **재검토 트리거**: 새 글의 활성 chart builder가 글 B의 폰트 탐색 또는 Okabe-Ito/base rcParams를 실제로 복사해야 할 때, 중복된 최소 책임만 추출한다.
