# Codex review handoff - kr_us_tightening_spillover

**Date**: 2026-10-05
**Project**: `F:/dev/Portfolio/macro-risk-monitor`
**Thesis**: `kr_us_tightening_spillover`
**Override file**: none — all triggers auto-fetched

---

## 0. Purpose

Review this thesis' trigger design for data existence, retail accessibility, cadence, threshold quality, category fit, and falsifiability. Flag uncertain historical claims as `UNVERIFIED: <reason>`.

## 1. Context

- Title: 한·미 동반 긴축기 장기금리 동조화와 국내 spillover 가설
- Decision rule: `rule_of_three`
- Critical windows: `2026-10-28`

## 2. Hypothesis

연준(2026-09 인상, 상단 4.00%)과 한국은행(2026-07·08 연속 인상, 3.00%)이 함께 긴축하는 국면에서
미국 장기금리(10년물 5%대)가 한 단계 더 오르면, 한·미 장기금리 동조화를 통해 국고채 금리가 따라 오르고
한·미 금리차 확대 → 원/달러 상승 → 국내 크레딧 스프레드 확대 순으로 국내 자금시장에 전이된다.
다만 2024년 이후 국고채의 미 금리 민감도가 낮아졌다면, 전이는 금리보다 환율·크레딧 경로로 나타날 수 있다.


## 3. Trigger Table

| # | id | series | source | category | threshold |
|---|---|---|---|---|---|
| 1 | `ust_10y_yield` | `DGS10` | `fred` | `leading` | red=`>= 5.0`, yellow=`>= 4.6`, green=`< 4.6` |
| 2 | `us_kr_policy_gap` | `fred:DFEDTARU - ecos:722Y001/M/0101000` | `derived` | `leading` | red=`>= 1.75`, yellow=`>= 1.25`, green=`< 1.25` |
| 3 | `ktb_ust_10y_gap` | `ecos:817Y002/D/010210000 - fred:DGS10` | `derived` | `coincident` | red=`<= -1.0`, yellow=`<= -0.6`, green=`> -0.6` |
| 4 | `usdkrw` | `731Y001/D/0000001` | `ecos` | `coincident` | red=`>= 1450`, yellow=`>= 1400`, green=`< 1400` |
| 5 | `kr_credit_spread` | `ecos:817Y002/D/010300000 - ecos:817Y002/D/010200000` | `derived` | `lagging` | red=`>= 1.0`, yellow=`>= 0.75`, green=`< 0.75` |
| 6 | `vix` | `VIXCLS` | `fred` | `lagging` | red=`>= 25`, yellow=`>= 20`, green=`< 20` |

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
  "thesis_name": "kr_us_tightening_spillover",
  "reviewer": "codex",
  "review_date": "2026-10-05",
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