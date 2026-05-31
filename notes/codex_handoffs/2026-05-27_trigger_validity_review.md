# Codex 핸드오프 — manual_override 트리거 8개 유효성 검토

**작성일**: 2026-05-27
**Claude 세션**: ai_circular_revenue·_401k_pe_distribution 가설 manual_override 채움 작업의 후속 검증
**Codex 역할**: 독립 reviewer (Claude의 source/threshold 결정에 대한 cross-check)
**예상 소요**: 15~30분

---

## 0. 이 핸드오프의 목적

Claude가 두 가설(`ai_circular_revenue`, `_401k_pe_distribution`)의 8개 `source: manual_override` 트리거를 정의했음. 사용자(retail investor, 한국)가 매월 데이터를 직접 입력하는 운영 모델. 그런데 Claude의 source 선택·threshold 설정·category 분류가 **실제로 유효한가**라는 의심이 있다.

특히:
- 사용자가 정말 매월 그 데이터를 구할 수 있는가? (paywall, login-walled, anti-bot)
- threshold가 2020~2026 historical pattern 대비 cherry-picked 아닌가?
- leading/coincident/lagging 분류가 정확한가?
- 8개가 합쳐서 가설을 **falsify**할 수 있는 구조인가, 아니면 confirmation bias 트리거뿐인가?

Codex의 사전 학습 지식·일반적인 시장 상식 기준으로 평가. **확신 없는 historical figure는 `UNVERIFIED: [이유]` 플래그**를 붙여서 사용자가 직접 검증할 수 있게 표시.

---

## 1. Context

- **프로젝트**: macro-risk-monitor (Phase 1 MVP)
- **경로**: `F:/dev/Portfolio/macro-risk-monitor`
- **사용자**: 한국 retail investor. Bloomberg·FactSet 등 유료 터미널 access 없음. 무료/가입 무료 source 위주.
- **운영 cadence**: 매월 1회 30~60분에 모든 manual_override 갱신 목표.
- **현재 날짜**: 2026-05-27
- **decision_rule**: `rule_of_three` — 같은 category(leading/coincident/lagging) 안에서 RED 카운트가 누적되면 단계적 액션(monitor → hedge_increase → defensive_position).
- **자동화 상태**: 8개 중 0개 자동화. Phase 2에서 `federal_register` API(dol_safe_harbor)·LLM-assisted CLI(나머지 6개) 도입 예정. Nasdaq Index News는 Imperva CDN으로 자동화 불가 판정.

---

## 2. 검토 대상 — 8개 트리거 전수

### 2.1 `theses/ai_circular_revenue.yaml` (트리거 3개 + 다른 source 2개)

**가설**: AI 밸류체인(메모리 → NVIDIA → OpenAI/MS/Oracle)이 외부 end demand 검증보다 빠르게 매출을 인식. 1999 Cisco vendor financing 유추.

| # | id | series | source | category | threshold |
|---|---|---|---|---|---|
| 1 | `openai_secondary_premium` | `openai_secondary_premium_pct` | manual_override | leading | red <= -10, yellow <= -5, green >= 10 (percent) |
| 2 | `oracle_cds_5y` | `oracle_cds_5y_bps` | manual_override | leading | red > 139, yellow > 100, green < 100 (bps) |
| 3 | `dram_spot_price` | `dram_spot_index` | manual_override | lagging | qualitative ("2개월 연속 하락") |

### 2.2 `theses/_401k_pe_distribution.yaml` (트리거 5개)

**가설**: PE 전통 exit 채널이 좁아진 국면에서 401K(약 $12T)의 PE 편입 허용은 marginal buyer로의 정치적 동원. NDX/CRSP fast-entry는 pre-IPO holder의 카운터파티를 인덱스 펀드로 만든다.

| # | id | series | source | category | threshold |
|---|---|---|---|---|---|
| 4 | `dol_safe_harbor_rule` | `dol_pe_safe_harbor_status` | manual_override | leading | qualitative (final/effective/proposed/not_yet) |
| 5 | `pe_secondary_discount` | `pe_secondary_discount_pct` | manual_override | leading | red <= -25, yellow <= -15, green >= -10 (percent, NAV 대비) |
| 6 | `ndx_fast_entry_additions` | `ndx_fast_entry_count_ttm` | manual_override | coincident | red >= 5, yellow >= 2, green "0" |
| 7 | `ipo_count_global` | `global_ipo_count_ttm` | manual_override | lagging | qualitative ("10년 최저권") |
| 8 | `pe_dpi_vintage_2020` | `pe_dpi_vintage_2020` | manual_override | lagging | red < 0.3, yellow < 0.5, green >= 0.7 (ratio) |

---

## 3. 읽어야 할 파일

```
@theses/ai_circular_revenue.yaml
@theses/_401k_pe_distribution.yaml
@data/manual_override/ai_circular_revenue.yaml
@data/manual_override/_401k_pe_distribution.yaml
@macro_risk_monitor/engine/decision.py
@macro_risk_monitor/schemas.py
@CLAUDE.md
```

특히 manual_override yaml의 `note:` 필드에 Claude가 적은 source URL·cadence·부호 규칙이 모두 들어있다. Codex는 이 note를 그대로 신뢰하지 말고 사전 학습 지식 기준으로 재검증할 것.

---

## 4. 트리거별 평가 차원 (각 7개 항목)

각 트리거(1~8)에 대해 다음 7개를 평가:

1. **데이터 존재성**: 해당 series가 실제로 published 되는 데이터인가? (paywall이어도 존재하면 OK. 비공개·유추 데이터는 FAIL.)
   - 예: "openai_secondary_premium_pct"가 Hiive/Forge에 실시간 quote 있는가? Series F 1차 평가가 reference price가 공개되어 있는가?

2. **Access**: `free` / `signup_free` / `paid_individual` / `paid_institutional` / `paywall_no_individual_option` / `private`
   - 사용자 retail tier에서 access 가능한 등급만 OK.

3. **Cadence**: 사용자 갱신 cadence와 데이터 발표 cadence가 맞는가?
   - 일별/주별/월별/분기별/반기별/연간/이벤트
   - 사용자가 월 1회 routine에 통합 가능한가?

4. **Threshold 합리성**: 사용자가 적은 임계치가 2020~2026 historical range 대비 합리적인가?
   - 예: `oracle_cds_5y > 139 bps`는 "2025-12 고점 갱신" 의도. 정말 2025-12에 139bps가 고점이었는가? cherry-picked 단일점?
   - 예: `pe_dpi_vintage_2020 < 0.3`은 5년차 DPI 평균을 알아야 평가 가능. 일반적인 5년차 vintage DPI 범위?
   - 이 차원이 **가장 중요**. cherry-pick은 false signal의 주된 원인.

5. **Category 정확성**: leading/coincident/lagging 분류 적절한가?
   - 예: `dram_spot_price`가 정말 lagging인가? AI capex sentiment의 leading일 수도?
   - 예: `dol_safe_harbor_rule`이 leading? 정책은 보통 시장 condition을 반영하는 coincident에 가까울 수도.

6. **대안 source**: 부적절하면 더 나은 무료/가입 무료 source는?
   - 예: oracle CDS는 Bloomberg/ICE 유료. 대안으로 Oracle bond OAS (FRED HQM yield curve), 5y bond yield - 10y treasury spread 등.

7. **Verdict**: `KEEP` / `MODIFY-source` / `MODIFY-threshold` / `MODIFY-category` / `DROP` / `REPLACE`
   - REPLACE: 트리거 의도는 유지하되 series·source·threshold 모두 교체

---

## 5. 가설 전체 수준 평가

각 가설(2개)에 대해 2~3문단:

a. **Falsifiability**: 5개 트리거(또는 3개)가 모두 GREEN으로 유지된다면, 가설은 어떤 조건에서 **반증**되는가? 반증 조건이 명확하지 않으면 unfalsifiable hypothesis 위험.

b. **Redundancy**: 5개 중 서로 같은 정보를 반복하는 트리거 쌍이 있는가? (예: openai_premium과 oracle_cds가 같은 'AI 자금조달 스트레스'를 측정한다면 정보 가치 중복)

c. **Missing dimension**: 가설을 검증하려면 있어야 하는데 빠진 트리거가 있는가?
   - 예: ai_circular_revenue에 'NVIDIA 매출 중 top 5 고객 집중도'가 빠짐. circular revenue 의심의 핵심 지표인데.
   - 예: _401k_pe_distribution에 '401K 운용사의 실제 PE allocation 비율'이 빠짐. safe harbor가 통과해도 운용사가 안 담으면 가설 무효.

d. **Rule-of-three 작동성**: 트리거 5개가 leading/coincident/lagging 각각 몇 개씩인가? 한 카테고리에 몰리면 rule_of_three가 의도대로 단계적 신호를 못 줌.

---

## 6. 출력 형식

### 6.1 트리거별 verdict table

```markdown
| # | id | data 존재성 | access | cadence | threshold | category | verdict | 대안 (있으면) |
|---|---|---|---|---|---|---|---|---|
| 1 | openai_secondary_premium | YES | signup_free (Hiive) | 일별 quote 갱신 | UNVERIFIED — Hiive의 1차 평가가 reference가 거래마다 update되는지 미확실 | 적합 (leading) | MODIFY-threshold | 또는 Caplight free trial |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |
```

각 행은 1~2 문장. UNVERIFIED 플래그는 가차없이 사용. Cherry-pick 의심은 명시.

### 6.2 가설별 종합 (가설 2개 각각 2~3문단)

- Falsifiability 평가
- Redundancy 평가
- Missing dimension
- Rule-of-three 작동성

### 6.3 우선순위 액션 리스트

전체 8개 + 가설 2개 검토 결과 중, 사용자가 **즉시 수정해야 할 항목 top 3** (verdict가 MODIFY/REPLACE/DROP인 것 중 가장 중요한 3개).

각 항목: `[# id] 무엇을 바꿔야 하는가 → 어떻게 바꿔야 하는가 (구체적 series·threshold·source 제안)`

---

## 7. 평가 시 유의사항

- **사용자는 retail tier**: Bloomberg/Refinitiv/FactSet 같은 유료 institutional 데이터 source를 대안으로 제시하지 말 것. FRED, Yahoo Finance, federal register, Renaissance Capital free tier, Wikipedia, 회사 IR site, SEC EDGAR 등 retail-accessible source만.
- **Historical figure는 UNVERIFIED 표시**: "2020 vintage PE DPI 5년차 평균은 약 0.X" 같은 진술은 Codex의 사전 학습 지식 기반 추정일 뿐. 단정하지 말고 `UNVERIFIED: [근거 출처 명시 못함]` 플래그.
- **가설 자체를 reject하지 말 것**: 사용자가 5/16~5/18 Claude 대화에서 직접 도출한 가설. Codex의 task는 **트리거 설계** 검토이지 가설 자체의 옳고 그름 평가가 아님. 다만 가설을 검증할 수 없는 트리거 구조라면 그 점은 명시.
- **합의보다 disagreement 환영**: Claude의 선택과 다른 판단이 있으면 그게 더 가치 있음. cross-model review의 목적.

---

## 8. 마지막 한 줄

이 핸드오프 자체에 빠진 차원이 있다고 판단되면, 출력 끝에 "## 핸드오프 자체에 대한 코멘트" 섹션으로 1~2 문장 첨부.
