"""News RSS source — keyword-match counts across financial outlets.

Some qualitative triggers (e.g. "press attention to circular AI revenue",
"vendor-financing chatter") have no clean numeric series in FRED/yfinance but
*do* leave a measurable footprint in news flow. This source polls a set of RSS
feeds (Bloomberg / Reuters / CNBC by default, configured in `config.py`),
counts how many items within a lookback window match the trigger's keyword
spec, and returns that count as the Reading value so the normal threshold
machinery in `engine/trigger.py` can classify it RED/YELLOW/GREEN.

The trigger's `series` field is the keyword spec: comma-separated terms, where
each term is matched case-insensitively as a substring against an item's title
and summary. An item counts if it matches **any** term (OR semantics)::

    series: "circular revenue, vendor financing, round-trip deal"

Parsing is stdlib-only (`xml.etree.ElementTree`) and understands both RSS 2.0
(`<item>`) and Atom (`<entry>`) so no extra dependency is required. Per-feed
fetch failures are best-effort: they are logged and skipped so one dead outlet
does not blank the signal; only if *every* feed fails is `FetchError` raised.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import requests

from ..schemas import Reading, Trigger
from .base import DataSource, FetchError, SourceUnavailable

logger = logging.getLogger(__name__)

_USER_AGENT = "macro-risk-monitor/0.1 (+https://github.com/) news_rss"


class NewsItem:
    """A single parsed feed entry (title + summary + publication datetime)."""

    __slots__ = ("title", "summary", "published", "link")

    def __init__(
        self,
        title: str,
        summary: str,
        published: datetime | None,
        link: str | None,
    ):
        self.title = title
        self.summary = summary
        self.published = published
        self.link = link

    def matches(self, keywords: list[str]) -> bool:
        haystack = f"{self.title}\n{self.summary}".lower()
        return any(kw in haystack for kw in keywords)


class NewsRssSource(DataSource):
    name = "news_rss"

    def __init__(
        self,
        feeds: list[str],
        cache_dir: Path,
        cache_ttl_hours: int = 6,
        lookback_days: int = 30,
    ):
        self.feeds = list(feeds)
        self.cache_dir = cache_dir
        self.cache_ttl_hours = cache_ttl_hours
        self.lookback_days = lookback_days
        cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ fetch
    def fetch(self, trigger: Trigger, as_of: date | None = None) -> Reading:
        if not self.feeds:
            raise SourceUnavailable("news_rss has no feeds configured")
        keywords = self._parse_keywords(trigger.series)
        if not keywords:
            raise FetchError(
                f"news_rss trigger {trigger.id} missing keyword spec in 'series'"
            )

        end = as_of or date.today()
        cutoff = datetime.combine(
            end - timedelta(days=self.lookback_days), datetime.min.time(), timezone.utc
        )
        # Upper bound: end of the as_of day. Without it a backdated `as_of`
        # would still count items published after it.
        upper = datetime.combine(
            end + timedelta(days=1), datetime.min.time(), timezone.utc
        )

        items: list[NewsItem] = []
        errors: list[str] = []
        for feed in self.feeds:
            try:
                xml = self._load_feed(feed, end)
                items.extend(self._parse_feed(xml))
            except Exception as exc:  # noqa: BLE001 - one dead feed must not blank all
                logger.warning("news_rss feed failed %s: %s", feed, exc)
                errors.append(f"{feed}: {exc}")

        if not items and len(errors) == len(self.feeds):
            raise FetchError(
                f"news_rss: all {len(self.feeds)} feeds failed: {'; '.join(errors)}"
            )

        matched = [
            it
            for it in items
            if it.matches(keywords) and self._within(it, cutoff, upper)
        ]
        latest = max(
            (it.published for it in matched if it.published is not None),
            default=None,
        )
        return Reading(
            trigger_id=trigger.id,
            value=float(len(matched)),
            as_of=latest.date() if latest else end,
            source_url=self.feeds[0],
            raw={
                "keywords": keywords,
                "lookback_days": self.lookback_days,
                "feeds": self.feeds,
                "feed_errors": errors,
                "match_count": len(matched),
                "matched_titles": [it.title for it in matched][:25],
            },
        )

    # ----------------------------------------------------------------- parsing
    @staticmethod
    def _parse_keywords(series: str | None) -> list[str]:
        if not series:
            return []
        return [kw.strip().lower() for kw in series.split(",") if kw.strip()]

    def _within(self, item: NewsItem, cutoff: datetime, upper: datetime) -> bool:
        # Items with no parseable date are counted (conservative); dated items
        # must fall inside [cutoff, upper).
        if item.published is None:
            return True
        return cutoff <= item.published < upper

    @staticmethod
    def _parse_feed(xml: str) -> list[NewsItem]:
        try:
            root = ET.fromstring(xml)
        except ET.ParseError as exc:
            raise FetchError(f"unparseable feed XML: {exc}") from exc

        items: list[NewsItem] = []
        # RSS 2.0: <rss><channel><item>...  Atom: <feed><entry>...
        rss_items = root.findall(".//item")
        if rss_items:
            for it in rss_items:
                items.append(
                    NewsItem(
                        title=_text(it.find("title")),
                        summary=_text(it.find("description")),
                        published=_parse_rss_date(_text(it.find("pubDate"))),
                        link=_text(it.find("link")) or None,
                    )
                )
            return items

        for entry in root.findall(".//{*}entry"):
            published = _parse_iso_date(
                _text(entry.find("{*}published")) or _text(entry.find("{*}updated"))
            )
            items.append(
                NewsItem(
                    title=_text(entry.find("{*}title")),
                    summary=_text(entry.find("{*}summary"))
                    or _text(entry.find("{*}content")),
                    published=published,
                    link=_atom_link(entry),
                )
            )
        return items

    # ------------------------------------------------------------------ I/O
    def _load_feed(self, feed: str, end: date) -> str:
        cache_path = self.cache_dir / f"{_slug(feed)}_{end.isoformat()}.xml"
        if cache_path.exists() and self._cache_fresh(cache_path):
            return cache_path.read_text(encoding="utf-8")
        xml = self._http_get(feed)
        cache_path.write_text(xml, encoding="utf-8")
        return xml

    @staticmethod
    def _http_get(feed: str) -> str:
        logger.info("news_rss fetch %s", feed)
        resp = requests.get(feed, timeout=20, headers={"User-Agent": _USER_AGENT})
        if not resp.ok:
            raise FetchError(f"news_rss {resp.status_code}: {resp.text[:200]}")
        return resp.text

    def _cache_fresh(self, cache_path: Path) -> bool:
        import time

        age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
        return age_hours < self.cache_ttl_hours


# --------------------------------------------------------------------- helpers
def _text(elem: ET.Element | None) -> str:
    if elem is None or elem.text is None:
        return ""
    return elem.text.strip()


def _atom_link(entry: ET.Element) -> str | None:
    for link in entry.findall("{*}link"):
        if link.get("rel", "alternate") in ("alternate", ""):
            return link.get("href")
    first = entry.find("{*}link")
    return first.get("href") if first is not None else None


def _parse_rss_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _parse_iso_date(value: str) -> datetime | None:
    if not value:
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _slug(feed: str) -> str:
    # Host alone is not unique (two feeds on the same outlet would share a
    # cache file and silently overwrite each other), so append a short hash
    # of the full URL.
    host = urlparse(feed).netloc or "feed"
    digest = hashlib.sha1(feed.encode("utf-8")).hexdigest()[:8]
    return f"{re.sub(r'[^A-Za-z0-9._-]', '_', host)}_{digest}"
