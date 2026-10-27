from __future__ import annotations

from brief.catalog import load_instruments, load_sources
from brief.config import FeedKind

GOOGLE_NEWS_PREFIX = "https://news.google.com/rss/search?"


def test_sources_load_and_feeds_are_well_formed() -> None:
    sources = load_sources()
    assert all(source.feeds for source in sources)
    for source in sources:
        for feed in source.feeds:
            assert feed.url.startswith("http")
            assert (feed.kind is FeedKind.GOOGLE_NEWS) == feed.url.startswith(GOOGLE_NEWS_PREFIX), feed.url


def test_instruments_load() -> None:
    assert load_instruments()
