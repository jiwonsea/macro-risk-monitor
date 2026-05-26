# Codex review handoff - us_long_end_yield

**Date**: 2026-05-27
**Project**: `F:\dev\Portfolio\macro-risk-monitor`
**Thesis**: `us_long_end_yield`
**Override file**: none — all triggers auto-fetched

---

## 0. Purpose

Review this thesis' trigger design for data existence, retail accessibility, cadence, threshold quality, category fit, and falsifiability. Flag uncertain historical claims as `UNVERIFIED: <reason>`.

## 1. Context

- Title: 미국 장기국채 수익률 상승의 capital market spillover 가설
- Decision rule: `rule_of_three`
- Critical windows: `2026-06-12`, `2026-07-30`, `2026-08-15`

## 2. Hypothesis

이란 갈등 장기화에 따른 유가·인플레이션 압력 + 영국 길트 spillover로
US 10Y 4.5%, 30Y 5%대가 정착하면, 모기지·IG 회사채 spillover로 가계·기업
자본 조달 비용이 상승해 자본시장 전반에 유동성 제약·하방 압력이 작용한다.
Term premium 재가격이 본질이며 지정학·정치 이벤트는 catalyst.


## 3. Trigger Table

| # | id | series | source | category | threshold |
|---|---|---|---|---|---|
| 1 | `ust_10y_yield` | `DGS10` | `fred` | `leading` | red=`>= 4.5`, yellow=`>= 4.2`, green=`< 4.0` |
| 2 | `ust_30y_yield` | `DGS30` | `fred` | `leading` | red=`>= 5.0`, yellow=`>= 4.7`, green=`< 4.5` |
| 3 | `mortgage_30y_rate` | `MORTGAGE30US` | `fred` | `coincident` | red=`>= 7.5`, yellow=`>= 7.0`, green=`< 6.5` |
| 4 | `ig_corp_spread` | `BAMLC0A0CM` | `fred` | `coincident` | red=`>= 150`, yellow=`>= 120`, green=`< 100` |
| 5 | `vix` | `^VIX` | `yfinance` | `lagging` | red=`>= 25`, yellow=`>= 20`, green=`< 18` |

## 4. Manual Override Entries

None — every trigger above is fetched automatically (fred / yfinance / sec_edgar). The reviewer should focus on threshold realism, category fit, and falsifiability rather than data accessibility.

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
  "thesis_name": "us_long_end_yield",
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