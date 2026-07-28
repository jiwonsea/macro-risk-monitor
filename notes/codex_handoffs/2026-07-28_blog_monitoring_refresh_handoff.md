# Handoff — 블로그 발행 후 관찰 캘린더 기반 데이터 갱신 (Codex/로컬)

**Date**: 2026-07-28
**전제**: 본문·차트·엑셀 발행본 완료. 데이터 기준일 2026-07-28.
**경로 갱신(2026-07-28)**: `blog/`가 flat → `blog/posts/<slug>/` 구조로 이동했다. 이 글의 모든 파일은 **`blog/posts/2026-07_war_two_inflation/`** 안에 있다. 스크립트 경로는 `Path(__file__).resolve().parent` 기준이므로 **어느 CWD에서 실행해도 된다.**
**목적**: 본문 결론의 "관찰 캘린더" 5개 체크포인트에 맞춰 릴리즈 때마다 `blog/posts/2026-07_war_two_inflation/data/*` 갱신 → Claude가 해당 차트·엑셀·본문 수치 재빌드.
**전제2**: `blog/posts/2026-07_war_two_inflation/collect.py`는 NSA CPI(CPIAUCNS/CPILFENS) 반영됨 — 그대로 재실행.

## 실행 원칙

- 각 체크포인트 **당일(또는 다음날)** `python blog/posts/2026-07_war_two_inflation/collect.py` 재실행(네트워크 필요, 스프레드시트 도구 불요).
- 변경 보고: 시리즈별 `old_latest → new_latest`. assertion 개정 시 값+주석 갱신 후 보고.
- 신규 이벤트는 `blog/posts/2026-07_war_two_inflation/data/annotations.json`에 date·label·**source URL** freeze.
- `blog/posts/2026-07_war_two_inflation/data/` 전체를 Claude에 전달 → Claude가 device_bash로 실제 디스크 재확인 후 빌드(마운트 캐시 stale 주의).

## 체크포인트 매핑 (릴리즈 → 갱신 시리즈 → 차트/본문)

| 날짜 | 릴리즈 | 갱신 시리즈(FRED/소스) | 영향 차트 | 본문 갱신 포인트 |
|---|---|---|---|---|
| **7/29** | FOMC 금리·성명 | DFEDTARU/DFEDTARL(변경 시), 성명 톤 | S1 | ① Fed 경로, 결론 캘린더 "7/29" 처리, 대시보드 정책금리 |
| **7/31** | 6월 Core PCE (BEA) | PCEPILFE → core_pce_yoy 6월 | S2, S9 | ② 인플레(Core PCE 6월), 대시보드, 본문 §1·§6 |
| **8월 초** | 7월 고용 (BLS) | UNRATE, PAYEMS 7월 | S7, S9 | ⑦ 노동, 결론 "도미노 트리거", 대시보드 |
| **8월 중순** | 7월 CPI (BLS) | CPIAUCNS/CPILFENS 7월 | S2, S9 | ② 인플레(헤드라인/core), 본문 §3·§4 |
| **상시** | 장기 앵커 | T5YIFR(일), NY Fed SCE(월) | S5, S9 | ④ 불확실성, 결론 "앵커 무너지면 base로" |

## 주의 사항

- **SEP는 9월 전까지 갱신 없음** — `sep_2026_yearend_median` 3.8% 유지(7/29 FOMC엔 새 SEP 없음).
- 7/29에 **금리 변경 시** S1 밴드가 자동 반영되고, 이때만 본문 "① 연준은 2026년 내내 동결" 제목·서술을 재검토(동결 깨지면 프레이밍 수정 필요 → Claude에 flag).
- 6월 PCE가 `core_pce_yoy`에 채워지면 S2·대시보드·본문의 "Core PCE 5월 3.4%"를 "6월 X%"로 갱신.
- 오일/SPR은 매 실행 시 최신 주간·일간분 자동 추가(공표지연 반영).
- 수치는 1차 소스·as-of 명시. 계획량↔실제량, SA/NSA, DRCCLACBS↔Equifax 혼동 금지.

## 이후 (Claude)

- 새 CSV → `blog/posts/2026-07_war_two_inflation/charts.py` + `blog/posts/2026-07_war_two_inflation/workbook.py` 재실행 → `blog/posts/2026-07_war_two_inflation/charts/*.png` · `blog/posts/2026-07_war_two_inflation/out/war_two_inflation_data.xlsx` 갱신.
- 본문 `blog/posts/2026-07_war_two_inflation/post.md`의 해당 수치·서술 + 관찰 캘린더 항목을 "발표됨(값)"으로 갱신.
- domino=tail 프레이밍 유지 여부 재검토(노동+앵커 동시 악화 시 결론 재작성 flag).
