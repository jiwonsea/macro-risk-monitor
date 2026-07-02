# macro-risk-monitor

거시 리스크 가설(또는 자연어 한 줄)을 입력하면 공개 데이터·뉴스를 자동 수집해 트리거별 임계 위반을 평가하고, LLM 분석을 곁들여 HTML/PDF 리포트로 출력하는 파이프라인입니다.

## 동기

밸류에이션 도구([business-valuation-tool](https://github.com/jiwonsea/business-valuation-tool))와 거시 시계열 도구([fx-reserves-analyzer](https://github.com/jiwonsea/fx-reserves-analyzer))를 만든 뒤, 정작 가장 자주 하는 작업이 **"이 리스크가 시장에 어떻게 작용할지"** 를 LLM과 4~5번 핑퐁하며 정리하는 일임을 깨달았습니다. 매번 수동으로 같은 패턴(사실관계 검증 → 가설 분해 → 역사적 비교 → 트리거 모니터링)을 반복하는 대신, 가설을 YAML로 인코딩해두면 매일·매주 자동으로 데이터를 fetch하고 임계 위반을 보고서로 받을 수 있습니다.

## 주요 기능

| 모드 | 입력 | 출력 |
|---|---|---|
| `run` | `theses/*.yaml` (정형 가설) | HTML 리포트 (트리거 상태표·차트·LLM 해설) |
| `analyze` | 자연어 한 줄 ("미국 10년물 4.5% 돌파") | LLM이 트리거 골격 생성 → 동일한 HTML 리포트. `--save-thesis`로 YAML 저장 가능 |
| `pdf` | 기존 HTML | Chrome headless로 PDF 변환 |
| `dashboard` | — | Streamlit 대시보드 (가설별 트리거 상태·히스토리 추이·최신 리포트, read-only) |
| `backtest` | `theses/*.yaml` + 날짜 범위 | as_of를 과거로 돌려 트리거 재평가 → CSV. 과거 재현 가능한 소스(FRED·yfinance·SEC EDGAR·transcript)만 평가, 나머지는 UNKNOWN 명시 |

## Rule of three

각 트리거는 leading / coincident / lagging 중 하나로 분류되며, 임계 비교 결과는 RED / YELLOW / GREEN 중 하나로 매핑됩니다. 카테고리 단위로 RED 개수를 집계해서:

- **3개 RED** → `defensive_position`
- **2개 RED** → `hedge_increase`
- **1개 RED** → `monitor`
- **0개 RED** → `no_signal` (YELLOW 카테고리는 안내)

## Quick start

```bash
# 1) 환경 준비
git clone https://github.com/jiwonsea/macro-risk-monitor.git
cd macro-risk-monitor
python -m venv .venv && .\.venv\Scripts\activate    # Windows PowerShell
pip install -e ".[ai,sources,charts,dev]"
cp .env.example .env                                 # FRED·Anthropic 키 입력

# 2) 정형 가설 실행 (FRED + yfinance만으로 평가)
python -m macro_risk_monitor.cli run theses/us_long_end_yield.yaml --pdf

# 3) 자연어 리스크
python -m macro_risk_monitor.cli analyze \
    "키어 스타머 정치 리스크로 영국 길트 spillover" \
    --save-thesis theses/uk_political_risk.yaml --pdf
```

## 디렉토리 구조

```
macro-risk-monitor/
├── theses/                          # 정형 가설 YAML (3개 동봉)
├── macro_risk_monitor/
│   ├── schemas.py                   # pydantic: Risk, Trigger, Reading, Verdict
│   ├── sources/                     # FRED · yfinance · SEC EDGAR · news_rss · manual_override
│   ├── engine/                      # 임계 평가 + Rule of three
│   ├── ai/                          # LLM 분석 + hallucination verifier
│   ├── output/                      # jinja2 HTML + matplotlib + Chrome PDF
│   └── pipeline/orchestrator.py     # 전 layer 연결
├── tests/                           # pytest (unit + integration)
└── reports/html/                    # 출력 리포트
```

## 동봉된 가설 3종

| 파일 | 가설 | 자동 fetch 비율 |
|---|---|---|
| `us_long_end_yield.yaml` | 미국 장기금리 → 모기지·회사채 spillover | 100% (FRED + yfinance) |
| `ai_circular_revenue.yaml` | AI 밸류체인 closed-loop revenue 가설 | 부분 (뉴스 키워드 카운트 자동, OpenAI premium·Oracle bond spread 수동) |
| `_401k_pe_distribution.yaml` | 401K 대체자산 개방 → PE retail distribution | 정성 위주 (manual_override) |

## 데이터 소스

| Source | 데이터 | 무료 여부 | 키 필요 |
|---|---|---|---|
| FRED | 금리·CPI·PPI·모기지·IG spread | ✓ | `FRED_API_KEY` |
| yfinance | 주가·ETF·^VIX | ✓ | — |
| SEC EDGAR | Company Facts (XBRL line items) | ✓ | `SEC_USER_AGENT` 권장 |
| News RSS | 키워드 매칭 기사 카운트 (Bloomberg·Reuters·CNBC) | ✓ | — |
| earnings_transcript_nlp | 로컬 transcript 키워드 분석 (`data/transcripts/{TICKER}/{YYYY-MM-DD}.txt`) | — (사용자 파일) | — |
| manual_override | Hiive·Forge·FINRA TRACE·DRAMeXchange | — | `data/manual_override/{thesis}.yaml` 직접 작성 |

## AI 협업 안내

이 프로젝트의 **리스크 분류·임계치 설계·결과 해석은 본인**이 수행했고, **코드 프로토타이핑·리팩터링·테스트 작성은 AI 도구(Claude Code)와 협업**했습니다. 트리거 5종 × 임계치 구성은 사전 1주에 걸친 시장 리서치(2026-05-15~18, [대화 share](https://claude.ai/share/90a3ca86-4de1-48ff-9d2f-240deb15a521)) 결과를 그대로 인코딩한 것입니다.

## Disclaimer

본 프로젝트는 **교육·포트폴리오 목적**의 소프트웨어이며, 산출되는 모든 리포트·트리거 평가·LLM 해설은 **투자 자문이나 매매 권유가 아닙니다.** 동봉된 가설·임계치·종목 언급은 파이프라인 시연을 위한 예시일 뿐, 특정 자산에 대한 의견이나 추천을 구성하지 않습니다. LLM 출력은 부정확하거나 환각을 포함할 수 있으며 사용자가 직접 1차 source로 검증해야 합니다. 본 도구의 사용으로 발생하는 어떤 투자 결정·손익에 대해서도 작성자는 책임지지 않습니다.

## License

MIT
