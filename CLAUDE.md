# macro-risk-monitor — session log

이 파일은 Claude Code 협업 세션의 학습·결정 사항을 기록합니다.
새 세션 시작 시 우선 읽고, 종료 시 새 학습이 있으면 갱신합니다.

## Architecture invariants

- **Sources / engine / ai / output 4 layer 분리.** orchestrator만 4 layer를 잇는 유일한 모듈. 각 layer는 독립적으로 테스트 가능해야 한다 — 한 layer가 다른 layer를 직접 import해서 cross-cutting concern을 만들면 안 됨.
- **Risk(YAML) → Reading → Verdict → Decision → Report** — 다섯 단계 데이터 모델이 schemas.py에 정의. 새 트리거·소스 추가 시 이 흐름을 깨지 말 것.
- **LLM 수치 인용은 verifier로 cross-check.** ai/verifier.py가 Reading 값과 임계치 numeric set을 정답지로 두고, markdown 본문의 모든 수치가 그 set에 ±5% 안에 있는지 검증. PASS/FAIL을 HTML 리포트 footer에 노출.
- **임계치는 사용자 정의, RED/YELLOW/GREEN 분류는 자동.** engine/trigger.py는 사용자가 작성한 비교식만 평가; 임계치 자체를 LLM이 결정하지 않음.

## Session log

### 2026-05-26 — 초기 구축
- 사용자 5/16~5/18 Claude 대화를 그대로 인코딩한 `theses/ai_circular_revenue.yaml`이 첫 검증 자산. 5개 트리거 × leading/coincident/lagging × 임계치는 사용자 결정값 그대로.
- 동봉 가설 3개 중 `us_long_end_yield.yaml`만 FRED + yfinance로 100% 자동 fetch 가능. 나머지 두 개는 manual_override 의존도 높음 — Phase 2 NLP·federalregister API 통합 시 자동화 격상 예정.
- LLM 모델 기본값 `claude-sonnet-4-6` (env `MACRO_RISK_LLM_MODEL`로 override). Opus 4.7은 비용 ~5배라 분기점 분석 등 중요 case에만 수동 전환.
- HTML/CSS 출력 결정 (markdown 대신) — 트리거 상태 색상·차트 임베드·PDF 변환 모두 유리. Chrome headless PDF는 career `_build_pdf.py` 패턴 그대로 재사용.

## Conventions

- 새 가설 추가 시 `theses/{name}.yaml` + `tests/unit/test_hypothesis_loader.py` 파라미터에 한 줄 추가.
- 새 소스 추가 시 `sources/{name}.py` + `SourceKind` enum 갱신 + `sources/registry.py` 분기 추가 + `tests/unit/test_sources_mock.py` 보강.
- 임계치 비교식 신규 연산자(`==`, 범위 등) 추가 시 `engine/trigger.py` 정규식 + `tests/unit/test_trigger.py` 케이스 동시 추가.

## Known gotchas

- `from ..sources import get_source`는 import 시점에 바인딩되므로 테스트에서 monkeypatch 시 `macro_risk_monitor.pipeline.orchestrator.get_source` 경로로 패치해야 한다 (registry 모듈만 패치하면 안 잡힘).
- `config.py`가 패키지 내부에 있으므로 `BASE_DIR`는 `__file__.resolve().parent.parent` — 프로젝트 루트가 아닌 패키지 디렉토리를 가리키지 않게 주의.
- Chrome 미설치 환경에서 `output/pdf.py`는 None 반환하고 silently 넘어감 — CI에서는 PDF 단계 스킵.
- yfinance·anthropic·matplotlib은 optional extras. orchestrator가 ImportError 시 graceful degrade하므로, 새 모듈 추가할 때도 동일 패턴(try/except ImportError → 폴백) 유지.

## Phase 2 backlog

- `sources/news_rss.py` (Bloomberg·Reuters·CNBC) + 키워드 매칭
- `sources/earnings_transcript_nlp.py` (CFO 어휘 변화 자동 탐지)
- 백테스트: 2024~26 데이터로 ai_circular_revenue 가설 재현 가능성 평가
- Streamlit 대시보드
- GitHub Actions daily cron + Slack/이메일 알림
- GitHub Pages 자동 배포 (포트폴리오 공개 surface)
