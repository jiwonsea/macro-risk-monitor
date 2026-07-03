# data/transcripts/

`earnings_transcript_nlp` 소스가 읽는 로컬 transcript 저장소.

```
data/transcripts/{TICKER}/{YYYY-MM-DD}[-anything].txt
```

예: `data/transcripts/MSFT/2026-04-29-fy26q3.txt`

- 파일명은 **YYYY-MM-DD 날짜 prefix 필수** (as_of 필터링·백테스트에 사용).
- 트리거 series 스펙: `"MSFT|GOOGL|META|AMZN::rationalize,efficiency,discipline"`
- Reading.value = 키워드가 1회 이상 등장한 기업 수 (lookback 내 최신 transcript 기준).
- `.txt` 파일은 저작권 문제로 **gitignore 처리됨** — 커밋되지 않음.
