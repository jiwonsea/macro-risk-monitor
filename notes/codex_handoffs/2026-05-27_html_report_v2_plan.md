# HTML report v2: summary clarity, unit conversion, FRED VIX, schema for critical windows, threshold lines on charts, richer LLM analysis

## Context

2026-05-27 첫 portfolio surface 데모로 `us_long_end_yield`·`ai_circular_revenue`·`_401k_pe_distribution` 세 가설의 HTML 리포트를 생성한 직후, 사용자가 us_long_end_yield 리포트에서 6개 결함을 지적했다:

1. **Summary 모호**: 트리거 2개가 RED인데 "한 카테고리 RED"로만 표시돼 사용자가 RED 카테고리/RED 트리거 구분을 못 한다.
2. **VIX fetch 실패**: yfinance가 한글 Windows path의 certifi cacert를 못 읽어 SSL 에러로 fail. 사용자는 "api key 문제"로 오해.
3. **단위 불일치 silent bug**: `ig_corp_spread`의 FRED `BAMLC0A0CM`는 percent 값(0.74)을 publish, 사용자 YAML은 bps 임계치(`>= 150`). engine이 unit-blind라 `0.74 >= 150` 평가가 항상 GREEN — 즉 RED 신호를 못 잡는 silent bug.
4. **LLM 분석 누락**: `--skip-llm` 명시했기 때문이지만, 사용자에게 가장 중요한 surface가 비어있음. prompt도 "가설 검증"이라는 사용자 의도에 정렬되지 않음.
5. **critical_windows 의미 없음**: 단순 date list 출력. 사용자가 YAML 코멘트(`# FOMC`, `# Treasury refunding`)로 적어둔 reason이 schema에서 버려져 HTML에 안 보임. 어떤 기준으로 선정됐는지도 분석 부재.
6. **차트 가독성**: threshold 라인이 없어 RED/YELLOW/GREEN 경계가 한눈에 안 보임.

이 작업은 portfolio 공개 surface로서의 HTML 리포트 품질을 끌어올린다. 공개 push 전 필수 fix이며, 사용자가 codex로 구현하기를 명시했다.

## Files

### MODIFY

- **`macro_risk_monitor/schemas.py`**
  - `CriticalWindow` 신규 모델: `date: date`, `event: str`, `rationale: str | None`.
  - `Risk.critical_windows: list[CriticalWindow]` (구 형식 backward-compat 위해 field_validator(mode="before")로 `date`만 들어온 항목은 `event="(미지정)"`, `rationale=None`으로 normalize).

- **`macro_risk_monitor/sources/fred.py`**
  - `_fetch_series()` (또는 동급 함수)가 FRED series metadata 의 `units_short`/`units`를 함께 fetch해 Reading.raw에 `fred_units` 키로 저장. metadata API 호출 1회 추가; 캐싱은 단순 module-level dict (`{series_id: units}`).
  - 폴백: API failure 시 `fred_units` 미설정 → 단위 변환 단계는 skip.

- **`macro_risk_monitor/engine/units.py`** (신규 헬퍼 모듈)
  - `convert(value: float, source: str, target: str) -> float`. 우선 percent ↔ bps만 지원. 그 외 동일 단위거나 unknown이면 그대로 반환.
  - `KNOWN_UNITS = {"percent", "pct", "%", "bps", "bp", "basis_points", "index", "usd", "count"}` — synonym normalize 헬퍼 `canonical_unit()`.

- **`macro_risk_monitor/engine/trigger.py`**
  - `evaluate()`가 verdict 만들기 직전에 `Reading.raw["fred_units"]` 와 `Trigger.unit` 을 비교, 다르면 `units.convert()`로 value 환산. 변환 결과를 Reading.value에 반영(혹은 새 Verdict.normalized_value 필드) — **단순화: Reading.value를 그 자리에서 덮어쓰지 말고, evaluate 내부 임시 변수로만 사용해 비교**. HTML 표시에 변환값을 노출하려면 별도 attribute(`Reading.display_value`)를 schemas에 추가하고 trigger.py에서 채움.
  - `_match()` 정규식·정성 비교 로직은 그대로 재사용.

- **`macro_risk_monitor/engine/rule_of_three.py`**
  - `apply_rule_of_three(verdicts)` 의 summary 텍스트 생성 부분을 보강:
    - 기존: `"한 카테고리 RED — 추가 모니터링 강화."`
    - 신규: `"RED 트리거 {n_red_triggers}개, RED 카테고리 {n_red_categories}개 ({카테고리 라벨})." + 기존 action 라벨` 형태.
  - Decision 모델은 변경 없음 (action/red_categories 그대로). 새 텍스트는 summary 필드에만 들어감.

- **`theses/us_long_end_yield.yaml`**
  - `vix` trigger: `source: fred`, `series: VIXCLS`로 변경. unit·threshold 그대로 (FRED VIXCLS도 index 단위).
  - `ig_corp_spread`: 코드 fix로 자동 변환되므로 YAML 수정 불필요 (`unit: bps`, `threshold: >= 150` 유지). 단위 변환이 작동하는지 e2e로 검증.
  - `critical_windows`: 단순 date list를 `{date, event, rationale}` 형식으로 보강. 사용자가 적어둔 코멘트(FOMC·Treasury refunding) 그대로 옮긴다.

- **`theses/ai_circular_revenue.yaml`, `theses/_401k_pe_distribution.yaml`**
  - `critical_windows`만 동일 schema로 마이그레이션. 다른 두 가설은 이번 작업 scope에서 데이터 fetch 변화 없음.

- **`macro_risk_monitor/output/charts.py`**
  - `render_trigger_bar()` signature를 `(verdicts, triggers)`로 변경. `triggers`는 `dict[str, Trigger]` (id → Trigger). caller가 risk.triggers를 dict로 변환해 넘김.
  - `matplotlib.pyplot.subplots(nrows=len(verdicts), ncols=1, sharex=False)`로 trigger마다 별도 sub-plot. 각 sub-plot에:
    - horizontal bar 1개 (value)
    - red/yellow/green threshold가 numeric이면 `axvline` 3개 (color-coded). 정성 threshold는 skip.
    - 우측 여백에 status pill text 표시 (선택).
  - 전체 figure 세로 길이는 trigger 수에 비례 (`figsize=(8.5, 1.6 * N + 0.8)`).

- **`macro_risk_monitor/output/html.py`**
  - `render_report()` 가 `render_trigger_bar()` 호출 시 `{t.id: t for t in report.risk.triggers}` 함께 전달.
  - `_build_table_rows()` 가 Reading의 `display_value`(있으면)와 `unit`을 결합해 HTML에 표시 — "0.74 bps" 대신 "74 bps".
  - critical_windows를 template에 dict 형태로 노출(`[{date, event, rationale}]`).

- **`macro_risk_monitor/templates/report.html.j2`**
  - Summary 섹션: 새 summary 문구가 그대로 노출되므로 template 변경 최소. RED categories 라벨 라인 유지.
  - Critical windows 섹션: 단순 `<ul>` → `<table>` 또는 `<dl>` 형식. 각 항목에 date + event(굵게) + rationale(회색 보조 텍스트).

- **`macro_risk_monitor/ai/prompt_templates.py`**
  - `ANALYZER_SYSTEM`의 섹션 헤더 5개는 유지하되, 추가 지시 두 줄:
    - "트리거 reading과 가설 메커니즘의 **인과관계**를 명시: 트리거가 가설을 어떤 방식으로 verify/falsify하는가."
    - "critical_windows 항목별로 reason과 그 날짜가 가설 관점에서 의미하는 바를 분석. (단순 캘린더 나열 금지)"
  - `build_analyzer_user_message()` JSON payload에 `critical_windows`의 event·rationale 필드 추가.

- **`macro_risk_monitor/pipeline/orchestrator.py`**
  - `skip_llm=True`일 때 fallback 텍스트를 더 명확하게: `"(LLM 분석 생략됨 — 정량 평가만 표시. ANTHROPIC_API_KEY 설정 후 --skip-llm 제거하면 분석이 포함됩니다.)"`. 동작 변화 없음, UX 메시지만.

### NEW

- **`macro_risk_monitor/engine/units.py`** — 위에 명시.

### Tests (new + update)

- **`tests/unit/test_units.py`** (신규): `convert(74, "percent", "bps") == ?` (= 7400 — 함정. 실제 의도는 FRED는 percent를 0.74로 publish하니까 0.74 percent → 74 bps. **rule: percent → bps × 100, bps → percent ÷ 100**). 정상 케이스 + 동일 단위 no-op + unknown 단위 raise/skip.
- **`tests/unit/test_trigger.py`** (보강): Trigger.unit="bps" + Reading.raw["fred_units"]="percent" + Reading.value=0.74 → 비교 시 74로 환산되어 `>= 150` 평가가 정상 GREEN, `>= 0.5` 평가가 RED (잘못된 임계치)인지 확인. UNKNOWN fred_units면 변환 skip.
- **`tests/unit/test_rule_of_three.py`** (보강): 같은 카테고리 RED 트리거 2개일 때 summary가 "RED 트리거 2개, RED 카테고리 1개" 표현인지 assert.
- **`tests/unit/test_schemas.py`** (보강): `critical_windows` backward-compat — simple `date` list로 들어와도 CriticalWindow로 normalize. event/rationale 포함 dict도 정상 파싱.
- **`tests/unit/test_charts.py`** (신규 가벼운 smoke): `render_trigger_bar(verdicts, triggers)`이 None 아닌 base64/path 반환, sub-plot 개수가 trigger 개수와 일치. matplotlib backend non-interactive(Agg) 강제.
- **`tests/unit/test_hypothesis_loader.py`** (기존): 세 가설 YAML 모두 새 schema로 로드 성공.

## Reused existing code

- `engine/trigger.py:_match()` 정규식·정성 비교 — 변환된 value를 그대로 넘겨 재사용.
- `sources/fred.py`의 requests.get 패턴 — metadata API 호출에 동일 client.
- `engine/rule_of_three.py`의 action ladder (no_signal/monitor/hedge_increase/defensive_position) — 로직 변경 없음, summary 텍스트만.
- `output/html.py:_build_table_rows()` — `display_value` 사용 분기만 추가.
- `ai/analyzer.py` 호출 흐름 — prompt만 보강.
- Jinja2 `report.html.j2` — 기존 섹션 구조 유지.

## Decision summary (사용자 confirm)

- 단위: **engine-level 자동 변환** (Trigger.unit ↔ FRED source units, percent↔bps만 우선)
- 차트: **trigger별 sub-plot, 각자 red/yellow/green axvline**
- VIX: **FRED VIXCLS로 source 변경** (yfinance dep는 유지하되 사용처 줄음)

## Verification

1. **단위 회귀**: `pytest tests/unit/test_units.py tests/unit/test_trigger.py -v`. ig_corp_spread 시뮬 케이스가 정상 평가되는지.
2. **전체 회귀**: `pytest tests/`. 기존 43 + 신규 테스트 모두 PASS.
3. **e2e 실행**: `python -m macro_risk_monitor.cli run theses/us_long_end_yield.yaml` (LLM 호출 포함, `.env`의 ANTHROPIC_API_KEY 필요). 출력 확인:
   - Summary: `"RED 트리거 N개, RED 카테고리 M개 (...)"` 형식
   - VIX trigger: FRED VIXCLS로 fetch 성공 (SSL 에러 사라짐)
   - ig_corp_spread: HTML 표시값이 `74 bps` (또는 변환값), 임계치 비교 정상
   - LLM 분석 섹션: 메커니즘·인과관계·critical_windows reason 포함
   - critical_windows 표시: date + event + rationale
   - 차트: trigger별 sub-plot에 red/yellow/green axvline 보임
4. **다른 가설 회귀**: `_401k_pe_distribution`·`ai_circular_revenue`로 `run` — schema migration 깨지지 않는지. (manual_override 값이 null이라 데이터 부족 상태는 그대로 OK.)
5. **HTML 시각 검증**: 사용자에게 us_long_end_yield HTML 다시 보여드려 6개 피드백 모두 해소됐는지 확인.

## Open caveats

- **단위 변환 범위**: percent ↔ bps만. yield curve point↔bps, MoM↔YoY 같은 케이스는 이번 scope 외.
- **FRED metadata fetch 비용**: 가설당 series 4~5개 × metadata 호출 1회 추가 → 분당 50 호출 한도 내 무관. 캐싱은 module-level dict로 충분.
- **차트 세로 길이**: trigger 7개 이상 가설은 sub-plot 7개 그려져 차트가 매우 길어짐. 우선 절대 길이로 진행, 사용자 피드백 받아 grouping 도입 여부 결정.
- **critical_windows backward-compat**: 기존 simple date list YAML도 깨지지 않게 validator로 normalize. 단, HTML에는 event="(미지정)"이 그대로 보이므로 사용자가 점진적으로 reason을 채워야 함.
- **VIX FRED 대체 후 yfinance dep**: 즉시 제거하지 않음. Phase 2에서 다른 yfinance 사용처 검토 후 결정.
- **summary 다국어 처리**: 새 summary 문구는 한국어. portfolio 공개를 영어로 할 계획이면 i18n 검토 필요 (이번 scope 외).
