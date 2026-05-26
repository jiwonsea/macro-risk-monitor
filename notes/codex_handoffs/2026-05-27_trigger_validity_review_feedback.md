# Codex feedback - manual_override trigger validity review

Date: 2026-05-27
Project: `F:\dev\Portfolio\macro-risk-monitor`
Scope: Review 8 `manual_override` triggers in `ai_circular_revenue` and `_401k_pe_distribution`.

No code files were modified. `graphify update .` was not run because this file is a review note only.

## Trigger verdict table

| # | id | data existence | access | cadence | threshold | category | verdict | alternative |
|---|---|---|---|---|---|---|---|---|
| 1 | `openai_secondary_premium` | YES. Secondary market indicative price exists, and Premier/Prism-style pages expose OpenAI price or implied valuation. | `signup_free` to `paid_individual`; actual transaction access is accredited-investor constrained. | Daily/event-driven, but public screen stability is weak. | UNVERIFIED: It is unclear whether "Series F preferred / last primary valuation" can be compared monthly on the same share-class basis. | Leading is appropriate. | `MODIFY-source`, `MODIFY-threshold` | Use headline implied valuation from Prism/Premier/Forge/Hiive, but define stress as implied valuation discount versus last primary/tender valuation, or no executable bid / stale ask liquidity stress. |
| 2 | `oracle_cds_5y` | YES. Oracle 5Y CDS 139 bps was visible in Reuters/S&P-style market headlines. | Usually `paid_institutional`; retail users only see sporadic headlines. | CDS is daily, but retail operation is event-headline based. | 139 bps is a confirmed-style spike anchor, but using one late-2025 high is cherry-pick prone. | Leading is plausible. | `REPLACE` | Replace with ORCL bond spread proxy: FINRA TRACE/Yahoo bond yield minus matched Treasury, or Oracle benchmark bond spread rolling z-score. |
| 3 | `dram_spot_price` | YES. DRAMeXchange publishes spot/module price screens with update timestamps. | `free` / `signup_free` | Daily/weekly, monthly close input is feasible. | "Two consecutive monthly declines" is workable, but too qualitative and weakly tied to HBM/AI demand. | Better as `coincident`, not `lagging`. | `MODIFY-category`, `MODIFY-threshold` | Use numeric `DDR5 16Gb spot average MoM <= -5% for 2 months`. |
| 4 | `dol_safe_harbor_rule` | YES. 2026-03-31 Federal Register proposed rule exists. | `free` | Event-driven; monthly check works. | proposed/final/effective state is appropriate, but final rule alone does not prove allocation adoption. | Leading is appropriate. | `KEEP`, with support trigger | Keep Federal Register / EBSA. Add adoption trigger later. |
| 5 | `pe_secondary_discount` | YES. Jefferies/Lazard secondary market reports are public enough for review use. | `free` | Semiannual/annual; stale for monthly routine. | Red `<= -25` is too extreme. Jefferies 2025 average LP portfolio pricing near 87% NAV implies about -13%. | Leading is appropriate. | `MODIFY-threshold` | Use red `<= -18` or `<= -20`, yellow `<= -13`, green `>= -8` to `>= -10`. |
| 6 | `ndx_fast_entry_additions` | YES. Nasdaq fast-entry pathway effective 2026-05-01. | `free` | Event/quarterly. | Red `>= 5` is likely too high given mega-cap IPO rarity; it may never fire. | Coincident is appropriate. | `MODIFY-threshold` | Use red `>= 2 TTM`, or red for one $200B+ IPO fast-entry; yellow for one smaller qualifying addition. |
| 7 | `ipo_count_global` | PARTIAL. Current Renaissance URL is closer to US IPO stats than global IPO count. | `free`, with some IPO Pro paid features. | YTD/monthly/quarterly possible. | "Global 10-year low" does not match the listed source cleanly. | Lagging is appropriate. | `REPLACE` | Use `us_ipo_count_ttm` and `us_ipo_proceeds_ttm` from Renaissance or StockAnalysis, with explicit percentile/z-score thresholds. |
| 8 | `pe_dpi_vintage_2020` | PARTIAL. Cambridge/PitchBook/Burgiss benchmarks exist, but detailed DPI is generally paid or restricted. Bain gives broader free distribution stress. | Mostly `paid_institutional`; limited public snippets. | Semiannual/annual. | UNVERIFIED: I cannot substantiate whether 2020 vintage 5-year DPI `<0.3` is red or `>=0.7` is green. | Lagging is appropriate. | `REPLACE` or `MODIFY-source` | Replace with Bain-style aggregate distributions as % NAV, or use vintage DPI only when a public benchmark percentile is available. |

## `ai_circular_revenue` assessment

The three manual triggers mostly measure AI-chain financing stress and memory-cycle pressure. They do not directly measure the central circular-revenue risk: customer concentration, vendor financing, related-party-like commitments, compute utilization, or whether recognized revenue is backed by independent end demand.

The hypothesis becomes falsifiable if these conditions stay green together: OpenAI/private AI implied valuations are stable or rising, Oracle credit spread does not widen versus peers, DRAM prices do not roll over, hyperscaler capex remains demand-led rather than efficiency/rationalization-led, and NVIDIA customer concentration or receivable/commitment quality does not deteriorate. The YAML currently captures only part of that falsification path.

There is some redundancy between `openai_secondary_premium` and `oracle_cds_5y`: both are financing-stress indicators in the AI chain. They are not identical, but two leading signals can move together and leave the rule-of-three too dependent on one stress dimension. Moving `dram_spot_price` to `coincident` would improve category balance.

Missing dimension: add a customer-quality trigger. A practical retail-accessible version could be `nvda_customer_concentration_risk`, based on 10-K/10-Q customer concentration disclosure, accounts receivable concentration, or management disclosure around large customers and purchase commitments.

## `_401k_pe_distribution` assessment

The current structure covers regulation, secondary-market stress, index-entry mechanics, IPO stress, and DPI stress. It still misses the key adoption question: whether major recordkeepers, target-date funds, managed accounts, or large DC plans actually allocate to private equity after a safe harbor rule.

The hypothesis is falsified if safe harbor progresses but actual plan adoption remains negligible, PE secondary discounts normalize, IPO/M&A exits reopen, and distributions recover without needing retail DC demand. Without an adoption/flow trigger, a final rule could turn red even if the distribution channel never becomes economically meaningful.

Rule-of-three coverage is superficially balanced: leading 2, coincident 1, lagging 2. Operationally, however, `ipo_count_global` and `pe_dpi_vintage_2020` are weak because of source-definition and access issues. If they stay UNKNOWN, the lagging category will not work as intended.

Missing dimension: add `401k_pe_product_adoption`, such as count of major recordkeepers/TDF suites announcing PE allocation, or number of large DC plans adding private-market sleeves. This should be a coincident trigger and would be more thesis-specific than generic DPI.

## Priority actions

1. `[#2 oracle_cds_5y]` Replace the CDS trigger with a retail-operable Oracle bond-spread proxy. Use ORCL bond yield minus matched Treasury or a rolling z-score rather than a single 139 bps CDS spike.

2. `[#8 pe_dpi_vintage_2020]` Drop the absolute vintage DPI threshold unless a public benchmark percentile can be cited. Prefer a free aggregate distribution-stress indicator from Bain or similar public PE reports.

3. `[#1 openai_secondary_premium]` Redefine the series as implied valuation discount versus last primary/tender valuation, or a liquidity-stress flag. Avoid share-class premium math unless the source consistently exposes comparable bid/ask and reference valuation data.

## Handoff comment

The handoff should add an "actual adoption / flow" review dimension. This matters most for `_401k_pe_distribution`: regulatory permission is not the same as capital actually entering PE through 401K channels.
