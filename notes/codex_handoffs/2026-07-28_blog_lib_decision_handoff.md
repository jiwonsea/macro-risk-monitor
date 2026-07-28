# Handoff — `blog/_lib/` 생성 여부 단독 결정 (A1)

**Date**: 2026-07-28
**From**: Claude
**To**: Codex
**선행 문서**: `2026-07-28_blog_repo_layout_review.md`(Claude 제안) → `..._review_feedback.md`(Codex 반박) → `..._synthesis.md`(종합)
**범위**: **A1 하나만.** 구조(C-lite hybrid)·L3·L4·L5·L6은 이미 확정. 재론 금지.
**시점 제약**: 사용자가 A2를 승인해 **마이그레이션은 오늘 실행 중**이다. 이 문서는 실행 순서 6단계 하나만 막고 있다. 나머지 1~5, 7~9는 이 답을 기다리지 않고 진행한다.

---

## 0. 왜 이 결정만 따로 떼어냈나

Codex 피드백의 9단계 중 6단계는 `_lib/`(폰트 탐색·색상 상수·base rcParams)을 만들되 **글 A는 재렌더링하지 않는다**고 명시했고, **글 B 연결은 언급이 없었다.** 그대로 실행하면 소비자가 0인 모듈이 남는다. rule of three를 `_lib/`의 *내용*에만 적용하고 *존재*에는 적용하지 않은 것이다.

사용자는 이 건을 "codex 핸드오프로 결정"하라고 지정했다. 따라서 Claude가 임의로 A1-a/A1-b를 고르지 않는다.

---

## 1. 확인된 사실 (디스크 실측, 2026-07-28)

두 빌더의 실제 코드를 읽고 대조했다. 추정 아님.

| 항목 | 글 A `make_charts.py` | 글 B `build_charts.py` |
|---|---|---|
| 폰트 | `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc` | `/usr/share/fonts/truetype/nanum/NanumGothic{,Bold}.ttf` |
| 폰트 등록 | `addfont` 1개 + `FontProperties(...).get_name()` | `addfont` 2개 + `get_name()` |
| 팔레트 | RED `#C0392B` / YELLOW `#E1A100` / GREEN `#1E8449` / GREY `#7F8C8D` / DARK `#2C3E50` (5색) | Okabe-Ito BLUE `#0072B2` / ORANGE `#E69F00` / GREEN `#009E73` / VERM `#D55E00` / PURPLE `#CC79A7` / SKY `#56B4E9` + INK/SUB/MUT/GRID/SURF (11색) |
| rcParams | `font.family`, `axes.unicode_minus` (2개) | 위 2개 + facecolor 3종·edgecolor·linewidth·grid 4종·tick 2종·text.color·font.size·savefig 3종 (18개) |
| DPI | `DPI=112`, 폭 `W=12` 고정 | `savefig.dpi=165`, figsize는 차트별 개별 지정 |
| 데이터 로딩 | 표준 `csv.DictReader` | `pandas.read_csv` + `set_index(date)` |
| 저장 | `fig.savefig(f"charts/{name}", dpi, bbox_inches, facecolor)` — **CWD 상대경로** | `fig.savefig(OUT/name)` — rcParams가 dpi/bbox/facecolor를 이미 담당 |
| 제목 | `ax.set_title(...)` 축 내부 | `fig.text(...)` figure 상단 + 부제 별도 |
| 푸터 | `fig.text(0.01, 0.01, fontsize=8)` | `fig.text(0.012, 0.014, fontsize=11.5)` |
| 라벨 | `ax.text` 인라인 | `ax.annotate` + offset points 헬퍼(`dlabel`) |
| 산출물 | PNG 5개 (`c2-*`) | PNG 9개 (`S1..S9`) + xlsx 1개 |
| 향후 재빌드 | **없음** (발행 완료, 갱신 계획 없음) | **7/29·7/31·8월초·8월중순 4회 예정** |

**공통 형태만 남는 부분**: (a) 한글 폰트 파일을 `addfont`하고 `get_name()`으로 `font.family`에 넣는 3줄 관용구, (b) "색상 상수를 대문자 모듈변수로 둔다"는 관습, (c) `save(fig, name)`라는 이름의 함수가 있다는 사실.

**(a)만 값이 동일하지 않다** — 폰트 경로 자체가 다르다. (b)는 값이 겹치는 색이 하나도 없다(`GREEN`은 이름만 같고 `#1E8449` vs `#009E73`). (c)는 시그니처는 같으나 본문이 다르다.

## 2. 종합 문서에서 이미 확정돼 이 결정에 묶이는 제약

- **글 A 재렌더링 금지** (Codex L2, Claude 동의). 네이버 발행본 이미지와 로컬 PNG의 대응이 깨지므로 팔레트 통일·스타일 통일은 구조 이동이 아니라 별도 콘텐츠 개정이다.
- 따라서 `_lib/`을 만들어도 **글 A는 영원히 소비자가 아니다.** 후보 소비자는 글 B 하나뿐이고, 그 다음은 아직 존재하지 않는 글 C다.
- L5 재생성 신뢰성 근거 정정(종합 §4): 진짜 취약점은 "Windows 폰트 경로"가 아니라 **빌드가 Claude 컨테이너 단일 환경에 묶여 있다는 것**과 글 A의 `NotoSansCJK-Regular.ttc` **이름 해석 실패 이력**이다. `_lib/`의 폰트 탐색을 만든다면 목적은 "Windows 대응"이 아니라 **빌드 환경 잠금 해제**로 적어야 한다.

## 3. 선택지

- **A1-a** — `_lib/` 생성 + **글 B의 `charts.py`·`workbook.py`를 같은 패스에서 연결.**
  범위: 폰트 탐색(후보 경로 리스트 순회 + 실패 시 명시적 예외), Okabe-Ito 상수, base rcParams.
  근거: 글 B는 4회 재빌드하는 유일한 활성 소비자다. 폰트 탐색을 리스트 순회로 바꾸면 §2의 "단일 환경 잠금"이 실제로 완화된다.
  비용: 오늘 마이그레이션에 코드 변경이 얹힌다. 이동 + 리팩터가 한 커밋에 섞이면 7/29 갱신에서 문제가 났을 때 원인 분리가 어렵다.

- **A1-b** — 이번 라운드에서 `_lib/` **생성 안 함.** 순수 이동만. 글 C에서 실제 중복이 확인되면 그때 만든다.
  근거: §1대로 현재 두 빌더의 공유 가능 실체는 3줄 관용구 하나뿐이고 그 값조차 다르다. rule of three 미달.
  비용: 폰트 경로 하드코딩이 글 B에 남는다. 컨테이너가 바뀌면 글 B 재빌드가 깨진다 — 다만 이건 `_lib/` 없이 글 B 안에서 3줄로도 고칠 수 있다.

- **A1-c(제3안 허용)** — 위 둘이 모두 부적절하면 제시하라. 단 "빈 `_lib/` 생성"은 배제한다(양측 이미 합의).

## 4. Codex가 답해야 할 것

1. `lib_decision`: `a` / `b` / `c` 중 하나. c면 `lib_decision_c_detail`에 서술.
2. `rule_of_three_met`: §1 사실표를 근거로 현재 실제 중복이 rule of three를 충족하는가. true/false + 한 줄 근거.
3. `font_lookup_fix_location`: 글 B의 폰트 경로 하드코딩을 고칠 위치. `_lib` / `post_b_inline` / `no_fix_now`.
4. `mixing_move_and_refactor`: 이동과 리팩터를 같은 커밋에 넣어도 되는가. `same_commit` / `separate_commits` / `defer_refactor`.
5. `revisit_trigger`: A1-b라면 `_lib/`을 다시 검토할 구체적 트리거(글 수·사건).
6. `blocking_issues`: 오늘 실행을 막는 것이 남았는가.

## 5. 작성 요구

- 파일: `notes/codex_handoffs/2026-07-28_blog_lib_decision_handoff_feedback.md`
- 끝에 아래 스키마의 ```verdict 블록. 필드 누락 금지.

```verdict
{
  "lib_decision": "a|b|c",
  "lib_decision_c_detail": "",
  "rule_of_three_met": true,
  "rule_of_three_reason": "",
  "font_lookup_fix_location": "_lib|post_b_inline|no_fix_now",
  "mixing_move_and_refactor": "same_commit|separate_commits|defer_refactor",
  "revisit_trigger": "",
  "blocking_issues": []
}
```

**주의**: Claude는 A1-b 쪽으로 기울어 있다. 그 편향을 그대로 승인하지 말 것. §1의 사실표에서 **A1-a를 지지하는 가장 강한 근거 하나를 먼저 세운 뒤**, 그것이 A1-b를 이기는지 판정하는 순서로 쓸 것. §3의 비용 항목이 과장됐다고 보면 그것부터 반박하라.
