"""Central configuration: env vars, paths, logging bootstrap.

Import this module first so dotenv and logging are initialised before any
pipeline/engine module runs.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# This module lives at macro_risk_monitor/config.py; the project root is its parent.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# API credentials
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
FRED_API_KEY: str | None = os.getenv("FRED_API_KEY")
SEC_USER_AGENT: str = os.getenv("SEC_USER_AGENT", "macro-risk-monitor contact@example.com")

# ---------------------------------------------------------------------------
# LLM configuration
# ---------------------------------------------------------------------------
LLM_MODEL: str = os.getenv("MACRO_RISK_LLM_MODEL", "claude-sonnet-4-6")
LLM_MAX_TOKENS: int = int(os.getenv("MACRO_RISK_LLM_MAX_TOKENS", "4096"))
LLM_TEMPERATURE: float = float(os.getenv("MACRO_RISK_LLM_TEMPERATURE", "0.2"))

# ---------------------------------------------------------------------------
# Chrome (HTML → PDF)
# ---------------------------------------------------------------------------
CHROME_PATH: str = os.getenv(
    "CHROME_PATH",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = _PROJECT_ROOT
THESES_DIR = BASE_DIR / "theses"
CACHE_DIR = BASE_DIR / ".cache"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_HTML_DIR = REPORTS_DIR / "html"
REPORTS_PDF_DIR = REPORTS_DIR / "pdf"
REPORTS_RAW_DIR = REPORTS_DIR / "raw"
LOGS_DIR = BASE_DIR / "logs"
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"

for _d in (CACHE_DIR, REPORTS_HTML_DIR, REPORTS_PDF_DIR, REPORTS_RAW_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Per-source cache subdirs
FRED_CACHE_DIR = CACHE_DIR / "fred"
YFINANCE_CACHE_DIR = CACHE_DIR / "yfinance"
EDGAR_CACHE_DIR = CACHE_DIR / "edgar"
NEWS_RSS_CACHE_DIR = CACHE_DIR / "news_rss"
LLM_CACHE_DIR = CACHE_DIR / "llm"
for _d in (FRED_CACHE_DIR, YFINANCE_CACHE_DIR, EDGAR_CACHE_DIR, NEWS_RSS_CACHE_DIR, LLM_CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Pipeline defaults
# ---------------------------------------------------------------------------
DEFAULT_LOOKBACK_DAYS: int = 365  # how much history to fetch by default
CACHE_TTL_HOURS: int = 6          # data sources cache freshness window

# news_rss: outlets polled for keyword-match counts. Override with the
# MACRO_RISK_NEWS_FEEDS env var (comma-separated URLs).
NEWS_RSS_FEEDS: list[str] = [
    f.strip()
    for f in os.getenv(
        "MACRO_RISK_NEWS_FEEDS",
        ",".join(
            (
                "https://feeds.bloomberg.com/markets/news.rss",
                "https://www.reutersagency.com/feed/?best-topics=business-finance",
                "https://www.cnbc.com/id/100003114/device/rss/rss.html",
            )
        ),
    ).split(",")
    if f.strip()
]
NEWS_RSS_LOOKBACK_DAYS: int = int(os.getenv("MACRO_RISK_NEWS_LOOKBACK_DAYS", "30"))

# earnings_transcript_nlp: local transcript files, data/transcripts/{TICKER}/.
TRANSCRIPTS_DIR = Path(
    os.getenv("MACRO_RISK_TRANSCRIPTS_DIR", str(BASE_DIR / "data" / "transcripts"))
)
TRANSCRIPT_LOOKBACK_DAYS: int = int(os.getenv("MACRO_RISK_TRANSCRIPT_LOOKBACK_DAYS", "120"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("macro_risk_monitor")
