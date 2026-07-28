# Feedback — `blog/_lib/` 생성 여부 단독 결정

## A1-a를 지지하는 가장 강한 근거

A1-a의 가장 강한 근거는 글 B가 7/29부터 네 번 재빌드될 **실재하는 활성 소비자**라는
점이다. 후보 폰트 경로를 순회하고 실패 원인을 명시하면, 현재 정상 동작하는 한
컨테이너의 특정 NanumGothic 경로가 바뀌어도 더 빨리 복구할 수 있다. 미래 글 C를
기다리지 않아도 이식성 개선의 효용은 즉시 발생한다.

이 근거는 폰트 탐색 수정은 정당화하지만 `_lib/`은 정당화하지 않는다. 같은 효과를 글
B의 `charts.py` 안에서 작은 함수 하나로 얻을 수 있기 때문이다. 글 A는 소비자가 될 수
없고, 글 B의 팔레트와 rcParams는 현재 다른 post가 공유하지 않는다. A1-a는 하나의
필요한 수정에 두 개의 아직 공유되지 않는 정책 묶음을 함께 추출한다.

따라서 A1-a의 이점은 A1-b + post B inline 수정에 완전히 포함되고, 추가 모듈 경계만
남는다. A1-a가 A1-b를 이기지 못한다.

## 결정

`lib_decision`은 **b**다. 이번 마이그레이션에서는 `_lib/`을 만들지 않는다.

다만 “순수 이동만”을 폰트 하드코딩 유지와 동일시할 필요는 없다. 구조 이동의 완료
조건인 상대 DATA/OUT 경로 수정은 이동 커밋에 포함하고, 폰트 후보 탐색은 글 B의
`charts.py` 내부에서 다음 별도 커밋으로 고친다. 이 구분은 `_lib/` 없이도 빌드 환경
잠금을 완화한다.

## Rule of three

현재는 충족하지 않는다.

- 폰트 등록은 두 구현뿐이며 후보 파일과 요구 글꼴이 다르다.
- 팔레트는 이름이 같은 `GREEN`조차 값이 다르고 정책 목적도 다르다.
- rcParams의 공통 부분은 `font.family`와 `axes.unicode_minus`뿐이다.
- 같은 이름의 `save(fig, name)`은 저장 정책과 출력 경로가 다르다.

즉 세 번 반복된 동일 책임이 없고, 두 구현 사이에서도 안정된 공용 계약을 식별할 수
없다. “색상 상수를 모듈 변수로 둔다”는 코딩 형태는 라이브러리 API가 아니다.

## 폰트 탐색 수정 위치

`font_lookup_fix_location`은 **post_b_inline**이다.

글 B의 `charts.py`에 다음 책임만 둔다.

1. 알려진 NanumGothic/Noto CJK 후보 경로 중 존재하는 파일을 찾는다.
2. 발견한 폰트를 `addfont`하고 family name을 반환한다.
3. 하나도 없으면 검사한 후보를 포함한 명시적 예외를 낸다.

팔레트와 rcParams는 그대로 둔다. 후보 경로 목록이 길어지거나 OS별 탐색 자체가 두 번째
활성 post에서 다시 필요해질 때 그 함수만 추출할 수 있다.

## 이동과 리팩터링

`mixing_move_and_refactor`는 **separate_commits**다.

비용 항목이 과장된 것은 아니다. 파일 이동과 import/설정 추출이 한 diff에 섞이면
7/29 재빌드 실패 시 새 경로 문제인지 폰트 초기화 문제인지 구분하기 어려워진다. 특히
현재 글 B의 `charts.py`와 `workbook.py`에는 이동 후에도 `/home/claude/blog/...` 절대
출력 경로가 남아 있으므로, 먼저 경로 수정과 이동 검증을 끝내야 한다.

권장 경계는 다음과 같다.

1. 커밋 1: post 폴더 이동, Markdown 링크, DATA/OUT 상대 경로, README/front matter,
   refresh handoff 경로만 수정하고 글 B 빌드를 검증한다.
2. 커밋 2: 글 B의 inline 폰트 후보 탐색만 추가하고 chart 빌드를 다시 검증한다.

두 커밋을 같은 날 연속으로 만드는 것은 괜찮다. “별도 커밋”은 일정 지연이 아니라
회귀 원인과 되돌림 단위를 분리하기 위한 것이다.

## 재검토 트리거

단순히 글 수가 세 편이 되는 것만으로 `_lib/`을 만들지 않는다. 다음 사건이 발생할 때
재검토한다.

> 새 글 C가 독립적인 `charts.py`를 갖고, 글 B와 동일한 폰트 탐색 또는 Okabe-Ito/base
> rcParams 중 하나를 실제로 복사해야 할 때, 두 post의 중복된 최소 책임만
> `blog/_lib/`으로 추출한다.

이 트리거는 세 번째 사례가 공용 계약을 보여 주기 전에 추상화를 만들지 않으면서,
복사본이 실제로 생기는 시점에는 결정을 놓치지 않는다. 글 C가 차트를 만들지 않거나
전혀 다른 렌더링 도구를 쓰면 재검토하지 않는다.

## Blocking issues

A1 결정 자체에 남은 blocker는 없다. `_lib/` 단계는 생략하고 마이그레이션을 계속할 수
있다. 폰트 inline 수정은 이동 완료 뒤 별도 커밋으로 수행하므로 오늘의 구조 이동을
막지 않는다.

현재 디스크에서 xlsx 락파일은 더 이상 발견되지 않았지만, 글 B의 `charts.py`와
`workbook.py` 절대 OUT 경로는 아직 남아 있다. 이는 A1 blocker가 아니라 이미 확정된
마이그레이션 3단계의 미완료 작업이다.

```verdict
{
  "lib_decision": "b",
  "lib_decision_c_detail": "",
  "rule_of_three_met": false,
  "rule_of_three_reason": "현재 구현은 두 개뿐이고 폰트 값·팔레트·rcParams·저장 정책이 달라 안정된 공용 계약이 없으며, 공통 폰트 등록 관용구는 post B 내부 수정으로 충분하다.",
  "font_lookup_fix_location": "post_b_inline",
  "mixing_move_and_refactor": "separate_commits",
  "revisit_trigger": "새 글 C의 활성 chart builder가 글 B의 폰트 탐색 또는 Okabe-Ito/base rcParams를 실제로 복사해야 할 때, 중복된 최소 책임만 추출한다.",
  "blocking_issues": []
}
```
