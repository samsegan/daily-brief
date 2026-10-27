"""What people are searching for and reading: free, no-key trend signals.

These say what is getting attention, not what is true. The writer uses them to
spot stories and to fill "what people are saying"; they never back a fact.
"""

from __future__ import annotations

import xml.etree.ElementTree as ElementTree
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from urllib.parse import quote_plus, urlencode

from brief.config import (
    BLUESKY_TRENDS_LIMIT,
    GOOGLE_TRENDS_GEO,
    WIKIPEDIA_MOST_READ_LIMIT,
    TrendSignal,
)
from brief.http import FetchFailed, fetch_bytes, fetch_json
from brief.models import RelatedLink, TrendItem
from brief.text import strip_html

GOOGLE_TRENDS_URL = "https://trends.google.com/trending/rss?{query}"
GOOGLE_SEARCH_URL = "https://www.google.com/search?q={query}"
GOOGLE_TRENDS_NS = {"ht": "https://trends.google.com/trending/rss"}
WIKIPEDIA_FEED_URL = "https://en.wikipedia.org/api/rest_v1/feed/featured/{day:%Y/%m/%d}"
WIKIPEDIA_OUTLET = "Wikipedia"
BLUESKY_TRENDS_URL = "https://public.api.bsky.app/xrpc/app.bsky.unspecced.getTrends?{query}"
BLUESKY_WEB_ROOT = "https://bsky.app"


@dataclass(frozen=True)
class TrendJob:
    target: str
    run: Callable[[], tuple[TrendItem, ...]]


def trend_jobs(today: date) -> tuple[TrendJob, ...]:
    return (
        TrendJob("google-trends", google_trends),
        TrendJob("wikipedia", lambda: wikipedia(today)),
        TrendJob("bluesky", bluesky),
    )


def google_trends() -> tuple[TrendItem, ...]:
    url = GOOGLE_TRENDS_URL.format(query=urlencode({"geo": GOOGLE_TRENDS_GEO}))
    try:
        root = ElementTree.fromstring(fetch_bytes(url))
    except ElementTree.ParseError as error:
        raise FetchFailed(url, f"invalid XML: {error}") from error
    return tuple(_google_item(item) for item in root.iter("item"))


def wikipedia(day: date) -> tuple[TrendItem, ...]:
    """English Wikipedia's featured feed for `day`: the previous day's most-read
    articles plus the curated "In the news" items."""
    url = WIKIPEDIA_FEED_URL.format(day=day)
    payload = fetch_json(url)
    try:
        most_read = payload["mostread"]["articles"][:WIKIPEDIA_MOST_READ_LIMIT]
        in_the_news = payload.get("news", [])
        return tuple(_wikipedia_article(article) for article in most_read) + tuple(
            _wikipedia_news(story) for story in in_the_news
        )
    except (KeyError, TypeError) as error:
        raise FetchFailed(url, f"unexpected feed shape: {error!r}") from error


def bluesky() -> tuple[TrendItem, ...]:
    url = BLUESKY_TRENDS_URL.format(query=urlencode({"limit": BLUESKY_TRENDS_LIMIT}))
    payload = fetch_json(url)
    try:
        return tuple(
            TrendItem(
                signal=TrendSignal.BLUESKY,
                title=trend["displayName"],
                url=BLUESKY_WEB_ROOT + trend["link"],
                detail=f"{trend['postCount']:,} posts" if trend.get("postCount") else "trending",
                related=(),
            )
            for trend in payload["trends"]
        )
    except (KeyError, TypeError) as error:
        raise FetchFailed(url, f"unexpected trends shape: {error!r}") from error


def _google_item(item: ElementTree.Element) -> TrendItem:
    query = item.findtext("title", default="").strip()
    traffic = item.findtext("ht:approx_traffic", default="", namespaces=GOOGLE_TRENDS_NS)
    related = tuple(
        RelatedLink(
            title=strip_html(news.findtext("ht:news_item_title", default="", namespaces=GOOGLE_TRENDS_NS)),
            url=news.findtext("ht:news_item_url", default="", namespaces=GOOGLE_TRENDS_NS),
            outlet=news.findtext("ht:news_item_source", default="", namespaces=GOOGLE_TRENDS_NS),
        )
        for news in item.findall("ht:news_item", GOOGLE_TRENDS_NS)
    )
    return TrendItem(
        signal=TrendSignal.GOOGLE,
        title=query,
        url=GOOGLE_SEARCH_URL.format(query=quote_plus(query)),
        detail=f"{traffic} searches" if traffic else "trending search",
        related=related,
    )


def _wikipedia_article(article: dict) -> TrendItem:
    description = article.get("description", "")
    views = f"{article['views']:,} views"
    return TrendItem(
        signal=TrendSignal.WIKIPEDIA,
        title=article["titles"]["normalized"],
        url=article["content_urls"]["desktop"]["page"],
        detail=f"{views} · {description}" if description else views,
        related=(),
    )


def _wikipedia_news(story: dict) -> TrendItem:
    links = tuple(
        RelatedLink(title=link["titles"]["normalized"], url=link["content_urls"]["desktop"]["page"], outlet=WIKIPEDIA_OUTLET)
        for link in story["links"]
    )
    return TrendItem(
        signal=TrendSignal.WIKIPEDIA_NEWS,
        title=strip_html(story["story"]),
        url=links[0].url if links else "",
        detail="Wikipedia · In the news",
        related=links,
    )
