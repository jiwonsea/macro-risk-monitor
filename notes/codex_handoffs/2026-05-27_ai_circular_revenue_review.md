# Codex review handoff - ai_circular_revenue

**Date**: 2026-05-27
**Project**: `F:\dev\Portfolio\macro-risk-monitor`
**Thesis**: `ai_circular_revenue`
**Override file**: `F:\dev\Portfolio\macro-risk-monitor\data\manual_override\ai_circular_revenue.yaml`

---

## 0. Purpose

Review this thesis' trigger design for data existence, retail accessibility, cadence, threshold quality, category fit, and falsifiability. Flag uncertain historical claims as `UNVERIFIED: <reason>`.

## 1. Context

- Title: AI 밸류체인 closed-loop revenue 가설
- Decision rule: `rule_of_three`
- Critical windows: `2026-05-28`, `2026-06-01`, `2026-07-25`, `2026-08-28`
## 2. Hypothesis

하단(메모리: Micron·SK하이닉스·Samsung) - 중간(NVIDIA) - 상단(OpenAI·Oracle·MS)
사이의 다년 LTA·equity 투자·compute commitment가 외부 end demand의 검증보다 빠르게
매출로 인식되며 valuation에 반영되고 있다. 검증 시점(OpenAI 차기 펀딩 또는
hyperscaler capex 가이던스)이 가격 inflection의 분기점이 될 수 있다.


## 3. Trigger Table

| # | id | series | source | category | threshold |
|---|---|---|---|---|---|
| 1 | `openai_implied_valuation_discount` | `openai_implied_valuation_discount_pct` | `manual_override` | `leading` | red=`<= -10`, yellow=`<= -5`, green=`>= 10` |
| 2 | `oracle_bond_spread_5y` | `oracle_bond_spread_5y_zscore` | `manual_override` | `leading` | red=`> 2`, yellow=`> 1`, green=`< 0.5` |
| 3 | `hyperscaler_capex_tone` | `capex_efficiency_terms` | `earnings_transcript_nlp` | `coincident` | red=`2개사 동시 'rationalize' OR 'efficiency'`, yellow=`1개사`, green=`0개사 (compute-constrained 유지)` |
| 4 | `dram_spot_price_mom` | `dram_spot_ddr5_mom_pct` | `manual_override` | `coincident` | red=`<= -5`, yellow=`<= -2`, green=`>= 0` |
| 5 | `nvda_customer_concentration` | `nvda_top_customer_revenue_pct` | `manual_override` | `coincident` | red=`>= 25`, yellow=`>= 15`, green=`< 10` |
| 6 | `nvda_data_center_qoq` | `nvda_dc_segment_revenue_qoq_pct` | `sec_edgar` | `lagging` | red=`<= 0`, yellow=`<= 5`, green=`> 10` |

## 4. Manual Override Entries

```yaml
openai_implied_valuation_discount_pct:
  value: None
  as_of: 2026-05-27
  source_url: https://www.hiive.com/companies/openai
oracle_bond_spread_5y_zscore:
  value: None
  as_of: 2026-05-27
  source_url: https://www.finra.org/finra-data/fixed-income
dram_spot_ddr5_mom_pct:
  value: None
  as_of: 2026-05-27
  source_url: https://www.dramexchange.com/
nvda_top_customer_revenue_pct:
  value: None
  as_of: 2026-05-27
  source_url: https://investor.nvidia.com/financial-info/sec-filings/
```

## 5. Review Dimensions

For each trigger, evaluate:

1. Data existence: does the series actually exist?
2. Access: `free`, `signup_free`, `paid_individual`, `paid_institutional`, `private`, or `unknown`.
3. Cadence: does the data update cadence fit monthly manual operation?
4. Threshold quality: is it historically defensible or cherry-picked?
5. Category fit: leading/coincident/lagging.
6. Better source: propose retail-accessible alternatives where needed.
7. Verdict: `KEEP`, `MODIFY-source`, `MODIFY-threshold`, `MODIFY-category`, `REPLACE`, or `ADD`.

## 6. Required Output

First provide a concise markdown verdict table. Then include this fenced JSON block exactly so `macro-risk apply-review` can parse it:

```patch
{
  "thesis_name": "ai_circular_revenue",
  "reviewer": "codex",
  "review_date": "2026-05-27",
  "entries": [
    {
      "target_id": "existing_trigger_id",
      "action": "MODIFY-threshold",
      "new_threshold": {"red": ">= 1", "yellow": ">= 0.5", "green": "< 0.5"},
      "rationale": "short reason",
      "unverified": false
    }
  ]
}
```

Use `ADD` with `target_id` set to the new trigger id. For `REPLACE`, set `target_id` to the existing id and `new_id` to the replacement id.

## 7. Notes

- Prefer retail-accessible sources.
- Do not reject the thesis itself; focus on trigger design.
- If a trigger cannot be validated, mark it `unverified: true` instead of inventing a number.