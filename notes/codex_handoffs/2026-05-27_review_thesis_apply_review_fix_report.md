# review-thesis / apply-review fix report

Date: 2026-05-27
Project: F:\dev\Portfolio\macro-risk-monitor

## Summary

Applied the fix handoff as prescribed:

- Removed `_extract_table_stub` completely from `macro_risk_monitor/ai/review_parser.py`.
- Restored `parse_feedback` to the plan's two-tier flow: fenced JSON patch first, Anthropic fallback second.
- Removed the fake stub-dependent parser test.
- Added mocked LLM fallback coverage.
- Added a real fenced JSON e2e fixture for `ai_circular_revenue`.
- Restored Korean input coverage in `tests/unit/test_risk_parser.py`.
- Fixed review handoff template `None` rendering to `null`.
- Fixed missing blank line before `## 2. Hypothesis`.
- Ran `graphify update .` after code changes.

## 1. Removal Check

Command:

```powershell
rg -n "_extract_table_stub" macro_risk_monitor tests
```

Result: 0 matches. Output was empty.

## 2. Tests

Full test command:

```powershell
python -m pytest tests/
```

Result:

```text
...........................................                              [100%]
43 passed in 1.49s
```

Focused changed-test command:

```powershell
python -m pytest tests/unit/test_review_parser.py tests/unit/test_apply_review_e2e.py tests/unit/test_risk_parser.py -v
```

Result:

```text
collected 6 items

tests\unit\test_review_parser.py ...                                     [ 50%]
tests\unit\test_apply_review_e2e.py .                                    [ 66%]
tests\unit\test_risk_parser.py ..                                        [100%]

6 passed in 0.34s
```

The new `test_parse_feedback_llm_fallback_returns_patch` and `test_apply_review_fixture_generates_diff_and_valid_yaml` both passed.

## 3. New E2E Dry-Run

Command:

```powershell
macro-risk apply-review ai_circular_revenue --feedback tests/fixtures/sample_feedback_ai_circular.md
```

Output:

```text
=== diff: theses\ai_circular_revenue.yaml ===
--- F:\dev\Portfolio\macro-risk-monitor\theses\ai_circular_revenue.yaml
+++ F:\dev\Portfolio\macro-risk-monitor\theses\ai_circular_revenue.yaml
@@ -87,10 +87,20 @@
     unit: percent
     description: NVIDIA Data Center 부문 매출 QoQ 성장률 (10-Q segment 기준)
     threshold:
-      red: "<= 0"
-      yellow: "<= 5"
-      green: "> 10"
-
+      red: <= -3
+      yellow: <= 3
+      green: '> 12'
+  - id: nvda_receivables_quality
+    category: coincident
+    source: manual_override
+    series: nvda_receivables_days_qoq_change
+    unit: days
+    description: NVIDIA receivables days QoQ increase; fixture trigger for apply-review e2e 
+      validation.
+    threshold:
+      red: '>= 20'
+      yellow: '>= 10'
+      green: < 5
 decision_rule: rule_of_three
 
 critical_windows:

=== diff: data\manual_override\ai_circular_revenue.yaml ===
--- F:\dev\Portfolio\macro-risk-monitor\data\manual_override\ai_circular_revenue.yaml
+++ F:\dev\Portfolio\macro-risk-monitor\data\manual_override\ai_circular_revenue.yaml
@@ -5,7 +5,7 @@
 # 2026-05-27 Codex review 반영으로 series 4개 모두 재정의됨.
 
 openai_implied_valuation_discount_pct:
-  value: null            # percent. 디스카운트면 음수, 프리미엄이면 양수
+  value:                 # percent. 디스카운트면 음수, 프리미엄이면 양수
   as_of: 2026-05-27
   source_url: https://www.hiive.com/companies/openai
   note: |
@@ -17,7 +17,7 @@
     회피: share-class premium 직접 계산 (bid/ask·reference 일관성 부족)
 
 oracle_bond_spread_5y_zscore:
-  value: null            # z-score (rolling 24m)
+  value:                 # z-score (rolling 24m)
   as_of: 2026-05-27
   source_url: https://www.finra.org/finra-data/fixed-income
   note: |
@@ -30,7 +30,7 @@
     Bloomberg paid_institutional 의존.
 
 dram_spot_ddr5_mom_pct:
-  value: null            # percent (MoM 단월)
+  value:                 # percent (MoM 단월)
   as_of: 2026-05-27
   source_url: https://www.dramexchange.com/
   note: |
@@ -42,7 +42,7 @@
     Codex 2026-05-27: category lagging → coincident 재분류 (AI/HBM 수요 신호와 직접 연결).
 
 nvda_top_customer_revenue_pct:
-  value: null            # percent (NVDA 매출 중 top-1 customer 비중)
+  value:                 # percent (NVDA 매출 중 top-1 customer 비중)
   as_of: 2026-05-27
   source_url: https://investor.nvidia.com/financial-info/sec-filings/
   note: |
@@ -52,3 +52,8 @@
     Threshold: red >= 25, yellow >= 15, green < 10 (numeric, 자동 평가)
     Codex 2026-05-27 신규 추가 — circular revenue 가설의 missing dimension 보완.
     소수 고객 집중도 상승 = vendor financing/related-party 리스크의 직접 signal.
+nvda_receivables_days_qoq_change:
+  value:
+  as_of: '2026-05-27'
+  source_url: https://investor.nvidia.com/financial-info/sec-filings/
+  note: Fixture-only manual override entry for apply-review e2e validation.

Patch staged at: notes\codex_handoffs\2026-05-27_ai_circular_revenue_review_patch.yaml
Re-run with --apply to write changes.
```

## 4. Apply, Diff, Restore

Apply command:

```powershell
macro-risk apply-review ai_circular_revenue --feedback tests/fixtures/sample_feedback_ai_circular.md --apply
```

Apply result: succeeded and printed the same unified diff as the dry-run, followed by:

```text
Applied patch: notes\codex_handoffs\2026-05-27_ai_circular_revenue_review_patch.yaml
```

Command:

```powershell
git diff -- theses/ data/
```

Output:

```diff
diff --git a/data/manual_override/ai_circular_revenue.yaml b/data/manual_override/ai_circular_revenue.yaml
index 125a875..a9c0fc8 100644
--- a/data/manual_override/ai_circular_revenue.yaml
+++ b/data/manual_override/ai_circular_revenue.yaml
@@ -5,7 +5,7 @@
 # 2026-05-27 Codex review 반영으로 series 4개 모두 재정의됨.
 
 openai_implied_valuation_discount_pct:
-  value: null            # percent. 디스카운트면 음수, 프리미엄이면 양수
+  value:                 # percent. 디스카운트면 음수, 프리미엄이면 양수
   as_of: 2026-05-27
   source_url: https://www.hiive.com/companies/openai
   note: |
@@ -52,3 +52,8 @@ nvda_top_customer_revenue_pct:
     Threshold: red >= 25, yellow >= 15, green < 10 (numeric, 자동 평가)
     Codex 2026-05-27 신규 추가 — circular revenue 가설의 missing dimension 보완.
     소수 고객 집중도 상승 = vendor financing/related-party 리스크의 직접 signal.
+nvda_receivables_days_qoq_change:
+  value:
+  as_of: '2026-05-27'
+  source_url: https://investor.nvidia.com/financial-info/sec-filings/
+  note: Fixture-only manual override entry for apply-review e2e validation.
diff --git a/theses/ai_circular_revenue.yaml b/theses/ai_circular_revenue.yaml
index 9af2762..ce21c84 100644
--- a/theses/ai_circular_revenue.yaml
+++ b/theses/ai_circular_revenue.yaml
@@ -87,10 +87,20 @@ triggers:
     unit: percent
     description: NVIDIA Data Center 부문 매출 QoQ 성장률 (10-Q segment 기준)
     threshold:
-      red: "<= 0"
-      yellow: "<= 5"
-      green: "> 10"
-
+      red: <= -3
+      yellow: <= 3
+      green: '> 12'
+  - id: nvda_receivables_quality
+    category: coincident
+    source: manual_override
+    series: nvda_receivables_days_qoq_change
+    unit: days
+    description: NVIDIA receivables days QoQ increase; fixture trigger for apply-review e2e 
+      validation.
+    threshold:
+      red: '>= 20'
+      yellow: '>= 10'
+      green: < 5
 decision_rule: rule_of_three
 
 critical_windows:
```

Restore command:

```powershell
git checkout -- theses/ai_circular_revenue.yaml data/manual_override/ai_circular_revenue.yaml
```

Status after restore:

```text
 M CLAUDE.md
 M macro_risk_monitor/ai/prompt_templates.py
 M macro_risk_monitor/cli.py
 M macro_risk_monitor/schemas.py
 M pyproject.toml
 M tests/unit/test_risk_parser.py
?? graphify-out/
?? macro_risk_monitor/ai/patch.py
?? macro_risk_monitor/ai/review_parser.py
?? macro_risk_monitor/ai/reviewer.py
?? macro_risk_monitor/templates/codex_review_handoff.md.j2
?? notes/codex_handoffs/2026-05-27_ai_circular_revenue_review.md
?? notes/codex_handoffs/2026-05-27_ai_circular_revenue_review_patch.yaml
?? notes/codex_handoffs/2026-05-27_implementation_plan.md
?? notes/codex_handoffs/2026-05-27_review_thesis_apply_review_fix_handoff.md
?? notes/codex_handoffs/2026-05-27_review_thesis_apply_review_implementation_report.md
?? tests/fixtures/
?? tests/unit/test_apply_review_e2e.py
?? tests/unit/test_patch.py
?? tests/unit/test_review_parser.py
?? tests/unit/test_reviewer.py
```

No `theses/` or `data/` files remain modified after restore.

## 5. Korean Input Regression

Command:

```powershell
python -m pytest tests/unit/test_risk_parser.py -v
```

Result:

```text
collected 2 items

tests\unit\test_risk_parser.py ..                                        [100%]

2 passed in 0.20s
```

## 6. Diff Stat

Command:

```powershell
git diff --stat
```

Tracked diff output:

```text
 CLAUDE.md                                 |  4 +++
 macro_risk_monitor/ai/prompt_templates.py | 41 ++++++++++++++++++++++
 macro_risk_monitor/cli.py                 | 58 +++++++++++++++++++++++++++++++
 macro_risk_monitor/schemas.py             | 31 +++++++++++++++++
 pyproject.toml                            |  1 +
 tests/unit/test_risk_parser.py            | 14 ++++----
 6 files changed, 142 insertions(+), 7 deletions(-)
```

Untracked files relevant to this work:

```text
graphify-out/
macro_risk_monitor/ai/patch.py
macro_risk_monitor/ai/review_parser.py
macro_risk_monitor/ai/reviewer.py
macro_risk_monitor/templates/codex_review_handoff.md.j2
tests/fixtures/sample_feedback.md
tests/fixtures/sample_feedback_ai_circular.md
tests/unit/test_apply_review_e2e.py
tests/unit/test_patch.py
tests/unit/test_review_parser.py
tests/unit/test_reviewer.py
notes/codex_handoffs/2026-05-27_ai_circular_revenue_review.md
notes/codex_handoffs/2026-05-27_ai_circular_revenue_review_patch.yaml
```

## Graphify

Command:

```powershell
graphify update .
```

Result:

```text
Re-extracting code files in . (no LLM needed)...
[graphify watch] Rebuilt: 257 nodes, 704 edges, 13 communities
[graphify watch] graph.json, graph.html and GRAPH_REPORT.md updated in F:\dev\Portfolio\macro-risk-monitor\graphify-out
Code graph updated. For doc/paper/image changes run /graphify --update in your AI assistant.
```
