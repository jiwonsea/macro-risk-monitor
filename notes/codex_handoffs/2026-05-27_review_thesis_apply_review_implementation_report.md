# review-thesis / apply-review implementation report

Date: 2026-05-27
Project: F:\dev\Portfolio\macro-risk-monitor

## Summary

Implemented the approved `review-thesis` and `apply-review` flow:

- Added ReviewPatch data models.
- Added review handoff renderer.
- Added feedback parser with fenced JSON parsing, deterministic markdown fallback, and Anthropic fallback.
- Added ruamel.yaml-based staged patch/diff/apply support.
- Added CLI commands:
  - `macro-risk review-thesis <name>`
  - `macro-risk apply-review <name> --feedback <path>`
  - `macro-risk apply-review <name> --patch <path> --apply`
- Added focused unit tests and fixture.
- Ran `graphify update .` after code changes.

## Verification

### 1. pytest tests/

Command:

```powershell
python -m pytest tests/
```

Result:

```text
42 passed in 1.44s
```

### 2. macro-risk review-thesis ai_circular_revenue

Command:

```powershell
macro-risk review-thesis ai_circular_revenue
```

Result:

```text
Generated: notes\codex_handoffs\2026-05-27_ai_circular_revenue_review.md
Next: paste this file to Codex, save reply as
      notes/codex_handoffs/2026-05-27_ai_circular_revenue_review_feedback.md
```

Generated markdown:

```text
F:\dev\Portfolio\macro-risk-monitor\notes\codex_handoffs\2026-05-27_ai_circular_revenue_review.md
```

### 3. macro-risk apply-review dry-run

Command:

```powershell
macro-risk apply-review ai_circular_revenue --feedback notes/codex_handoffs/2026-05-27_trigger_validity_review_feedback.md
```

Result:

```text
=== diff: theses\ai_circular_revenue.yaml ===
(no changes)
=== diff: data\manual_override\ai_circular_revenue.yaml ===
(no changes)
Patch staged at: notes\codex_handoffs\2026-05-27_ai_circular_revenue_review_patch.yaml
Re-run with --apply to write changes.
```

Reason: the current YAML already reflects the reference feedback contents.

Staged patch:

```text
F:\dev\Portfolio\macro-risk-monitor\notes\codex_handoffs\2026-05-27_ai_circular_revenue_review_patch.yaml
```

### 4. graphify update

Command:

```powershell
graphify update .
```

Result:

```text
Re-extracting code files in . (no LLM needed)...
[graphify watch] Rebuilt: 257 nodes, 704 edges, 14 communities
[graphify watch] graph.json, graph.html and GRAPH_REPORT.md updated in F:\dev\Portfolio\macro-risk-monitor\graphify-out
Code graph updated. For doc/paper/image changes run /graphify --update in your AI assistant.
```

### 5. git diff --stat

Tracked diff:

```text
CLAUDE.md                                 |  4 +++
macro_risk_monitor/ai/prompt_templates.py | 41 ++++++++++++++++++++++
macro_risk_monitor/cli.py                 | 58 +++++++++++++++++++++++++++++++
macro_risk_monitor/schemas.py             | 31 +++++++++++++++++
pyproject.toml                            |  1 +
tests/unit/test_risk_parser.py            | 18 +++++-----
6 files changed, 144 insertions(+), 9 deletions(-)
```

New files include:

```text
macro_risk_monitor/ai/patch.py
macro_risk_monitor/ai/review_parser.py
macro_risk_monitor/ai/reviewer.py
macro_risk_monitor/templates/codex_review_handoff.md.j2
tests/fixtures/sample_feedback.md
tests/unit/test_patch.py
tests/unit/test_review_parser.py
tests/unit/test_reviewer.py
notes/codex_handoffs/2026-05-27_ai_circular_revenue_review.md
notes/codex_handoffs/2026-05-27_ai_circular_revenue_review_patch.yaml
graphify-out/
```
