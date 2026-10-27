"""Fetches one outlet feed and turns its entries into Articles."""

from __future__ import annotations

import calendar
import hashlib
from datetime import UTC, datetime, timedelta

import feedparser

from brief.config import (
    ARTICLE_WINDOW_HOURS,
    MAX_SUMMARY_CHARS,
    OPINION_TITLE_PREFIXES,
    OPINION_URL_MARKERS,
    FeedKind,
)
from brief.http import FetchFailed, fetch_bytes
from brief.models import Article, Feed, Source
from brief.text import strip_html, truncate_words

ARTICLE_ID_LENGTH = 10
_GOOGLE_NEWS_SUFFIX = " - "


def fetch_feed(source: Source, feed: Feed, now: datetime) -> tuple[Article, ...]:
    """Articles from one feed published inside the ingest window.

    Raises FetchFailed when the feed can't be fetched or parsed, or when it has
    nothing recent: a feed that stopped updating is a config problem to fix.
    """
    parsed = feedparser.parse(fetch_bytes(feed.url))
    if not parsed.entries:
        raise FetchFailed(feed.url, f"no entries ({parsed.get('bozo_exception', 'empty feed')})")
    cutoff = now - timedelta(hours=ARTICLE_WINDOW_HOURS)
    usable = [entry for entry in parsed.entries if _is_usable(entry)]
    articles = tuple(
        _to_article(source, feed, entry, published)
        for entry in usable
        if (published := _published(entry)) >= cutoff
    )
    if not articles:
        raise FetchFailed(feed.url, f"no entries in the last {ARTICLE_WINDOW_HOURS}h")
    return articles


def article_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:ARTICLE_ID_LENGTH]


def is_opinion(url: str, title: str) -> bool:
    lowered_url = url.lower()
    lowered_title = title.lower()
    return any(marker in lowered_url for marker in OPINION_URL_MARKERS) or lowered_title.startswith(
        OPINION_TITLE_PREFIXES
    )


def _is_usable(entry: feedparser.FeedParserDict) -> bool:
    has_date = bool(entry.get("published_parsed") or entry.get("updated_parsed"))
    return bool(entry.get("link")) and bool(entry.get("title")) and has_date


def _published(entry: feedparser.FeedParserDict) -> datetime:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    return datetime.fromtimestamp(calendar.timegm(parsed), tz=UTC)


def _to_article(source: Source, feed: Feed, entry: feedparser.FeedParserDict, published: datetime) -> Article:
    url = entry["link"].strip()
    title = strip_html(entry["title"])
    summary = strip_html(entry.get("summary", ""))
    if feed.kind is FeedKind.GOOGLE_NEWS:
        title = _strip_outlet_suffix(title)
        summary = ""
    return Article(
        id=article_id(url),
        source_id=source.id,
        section=feed.section,
        title=title,
        summary=truncate_words(summary, MAX_SUMMARY_CHARS),
        url=url,
        published_at=published.strftime("%Y-%m-%dT%H:%M:%SZ"),
        is_opinion=is_opinion(url, title),
    )


def _strip_outlet_suffix(title: str) -> str:
    head, separator, _ = title.rpartition(_GOOGLE_NEWS_SUFFIX)
    return head if separator else title
