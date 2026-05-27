# HTML report v2 implementation report

Date: 2026-05-27
Project: `F:\dev\Portfolio\macro-risk-monitor`

## Implemented fixes

- Summary now distinguishes RED trigger count from RED category count.
- VIX migrated from `yfinance:^VIX` to `fred:VIXCLS`.
- FRED percent-to-bps conversion added at engine evaluation time. `BAMLC0A0CM` raw `0.74 percent` displays/evaluates as `74 bps`; raw `Reading.value` remains unchanged and converted value is stored in `Reading.display_value`.
- Analyzer prompt now requires trigger-to-thesis causal analysis and critical-window rationale, and forbids unsupported derived/external numbers.
- `critical_windows` schema expanded to `{date, event, rationale}` with backward compatibility for legacy date lists.
- Trigger chart now renders one subplot per numeric trigger and draws numeric red/yellow/green threshold `axvline`s.

## Tests

Command:

```powershell
python -m pytest tests/ -v
```

Result:

```text
collected 54 items
tests\integration\test_end_to_end.py .                                   [  1%]
...
tests\unit\test_verifier.py .....                                        [100%]
54 passed in 2.11s
```

New/updated coverage includes:

- `tests/unit/test_units.py`: percent <-> bps conversion, including `0.74 percent -> 74 bps`.
- `tests/unit/test_trigger.py`: FRED `fred_units=percent` converted for bps thresholds without overwriting raw value.
- `tests/unit/test_schemas.py`: legacy and expanded `critical_windows`.
- `tests/unit/test_charts.py`: chart smoke test and subplot count.
- `tests/unit/test_sources_mock.py`: FRED metadata `units_short`.
- `tests/unit/test_verifier.py`: threshold numerics cited with units in LLM markdown.

## E2E: us_long_end_yield with LLM

Command:

```powershell
python -m macro_risk_monitor.cli run theses/us_long_end_yield.yaml
```

Result:

```text
action: monitor
summary: RED triggers 2; RED categories 1 (leading). Additional monitoring.
Anthropic analyze model=claude-sonnet-4-6 tokens_max=4096
report ready: F:\dev\Portfolio\macro-risk-monitor\reports\html\2026-05-27-us_long_end_yield.html (action=monitor)
```

The final run completed without citation-check warnings. HTML footer shows:

```text
Citation check: PASS (27 grounded references)
```

## Other hypothesis regressions

Command:

```powershell
python -m macro_risk_monitor.cli run theses/ai_circular_revenue.yaml --skip-llm
```

Result:

```text
action: no_signal
summary: RED triggers 0; no active warning signal.
report ready: F:\dev\Portfolio\macro-risk-monitor\reports\html\2026-05-27-ai_circular_revenue.html (action=no_signal)
```

Expected Phase 1 source limitations still appear for `earnings_transcript_nlp` and one SEC-EDGAR series format; schema/runtime did not break.

Command:

```powershell
python -m macro_risk_monitor.cli run theses/_401k_pe_distribution.yaml --skip-llm
```

Result:

```text
action: no_signal
summary: RED triggers 0; no active warning signal.
report ready: F:\dev\Portfolio\macro-risk-monitor\reports\html\2026-05-27-_401k_pe_distribution.html (action=no_signal)
```

## HTML grep excerpts

File: `reports/html/2026-05-27-us_long_end_yield.html`

```text
summary: RED triggers 2; RED categories 1 (leading). Additional monitoring.
ig_corp_spread row: <td>74 bps</td>
VIX row: CBOE VIX volatility index (FRED VIXCLS)
VIX source link: https://fred.stlouisfed.org/series/VIXCLS">fred</a>
chart: <div class="chart" data-subplots="5">
critical_windows: FOMC / FOMC / Treasury refunding announcement
critical_windows rationale: Policy guidance can reset term-premium and duration-risk pricing.
critical_windows rationale: Coupon issuance mix can directly affect long-end supply and spillover risk.
footer: <span class="citation-ok">PASS</span> (27 grounded references)
```

## Generated HTML

```text
reports/html/2026-05-27-us_long_end_yield.html
reports/html/2026-05-27-ai_circular_revenue.html
reports/html/2026-05-27-_401k_pe_distribution.html
```

## Diff stat

```text
19 files changed, 350 insertions(+), 77 deletions(-)
```

New files:

```text
macro_risk_monitor/engine/units.py
tests/unit/test_charts.py
tests/unit/test_schemas.py
tests/unit/test_units.py
```

## Graphify

Command:

```powershell
graphify update .
```

Result:

```text
Re-extracting code files in . (no LLM needed)...
[graphify watch] Rebuilt: 293 nodes, 803 edges, 18 communities
graph.json, graph.html and GRAPH_REPORT.md updated in F:\dev\Portfolio\macro-risk-monitor\graphify-out
Code graph updated.
```
