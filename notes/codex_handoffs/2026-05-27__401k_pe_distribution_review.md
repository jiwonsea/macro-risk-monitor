# Codex review handoff - _401k_pe_distribution

**Date**: 2026-05-27
**Project**: `F:\dev\Portfolio\macro-risk-monitor`
**Thesis**: `_401k_pe_distribution`
**Override file**: `F:\dev\Portfolio\macro-risk-monitor\data\manual_override\_401k_pe_distribution.yaml`

---

## 0. Purpose

Review this thesis' trigger design for data existence, retail accessibility, cadence, threshold quality, category fit, and falsifiability. Flag uncertain historical claims as `UNVERIFIED: <reason>`.

## 1. Context

- Title: 401K 대체자산 개방을 통한 PE retail distribution 가설
- Decision rule: `rule_of_three`
- Critical windows: `2026-03-31`, `2026-05-01`, `2026-04-27`

## 2. Hypothesis

PE의 전통 exit 채널(IPO·M&A·dividend recap·secondary)이 고금리로 동시에 좁아진
국면에서, 401K(약 $12T)의 PE·crypto 편입 허용은 우연이 아니라 마지막 marginal
buyer로의 정치적 동원이다. NDX·CRSP fast entry 룰 + float weighting 변경은
pre-IPO holder의 자연스러운 카운터파티를 인덱스 펀드로 만든다.


## 3. Trigger Table

| # | id | series | source | category | threshold |
|---|---|---|---|---|---|
| 1 | `dol_safe_harbor_rule` | `dol_pe_safe_harbor_status` | `manual_override` | `leading` | red=`final OR effective`, yellow=`proposed`, green=`not_yet` |
| 2 | `pe_secondary_discount` | `pe_secondary_discount_pct` | `manual_override` | `leading` | red=`<= -20`, yellow=`<= -13`, green=`>= -8` |
| 3 | `ndx_fast_entry_additions` | `ndx_fast_entry_count_ttm` | `manual_override` | `coincident` | red=`>= 2`, yellow=`>= 1`, green=`0` |
| 4 | `us_ipo_activity` | `us_ipo_count_ttm` | `manual_override` | `lagging` | red=`<= 75`, yellow=`<= 110`, green=`> 150` |
| 5 | `pe_aggregate_distributions` | `pe_aggregate_distributions_pct_nav` | `manual_override` | `lagging` | red=`< 5`, yellow=`< 8`, green=`>= 12` |
| 6 | `dc_plan_pe_adoption` | `dc_plan_pe_adoption_count_ttm` | `manual_override` | `coincident` | red=`>= 3`, yellow=`>= 1`, green=`0` |

## 4. Manual Override Entries

```yaml
dol_pe_safe_harbor_status:
  value: null
  as_of: 2026-05-27
  source_url: https://www.federalregister.gov/agencies/employee-benefits-security-administration
pe_secondary_discount_pct:
  value: null
  as_of: 2026-05-27
  source_url: https://www.jefferies.com/our-firm/news-and-research/
ndx_fast_entry_count_ttm:
  value: null
  as_of: 2026-05-27
  source_url: https://indexes.nasdaqomx.com/News
us_ipo_count_ttm:
  value: null
  as_of: 2026-05-27
  source_url: https://www.renaissancecapital.com/IPO-Center/Stats
pe_aggregate_distributions_pct_nav:
  value: null
  as_of: 2026-05-27
  source_url: https://www.bain.com/insights/topics/global-private-equity-report/
dc_plan_pe_adoption_count_ttm:
  value: null
  as_of: 2026-05-27
  source_url: https://www.pionline.com/topic/defined-contribution
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
  "thesis_name": "_401k_pe_distribution",
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