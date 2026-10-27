from __future__ import annotations

from datetime import UTC, datetime

import pytest

from brief import feeds
from brief.config import FeedKind, Lean, Section
from brief.http import FetchFailed
from brief.models import Feed, Source

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)

RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Example</title>
<item><title>Senate passes funding bill</title><link>https://ex.com/a</link>
  <description>&lt;p&gt;The Senate voted &lt;b&gt;52-48&lt;/b&gt; late Monday.&lt;/p&gt;</description>
  <pubDate>Mon, 27 Oct 2026 03:00:00 GMT</pubDate></item>
<item><title>Opinion | The bill is a mistake</title><link>https://ex.com/opinion/b</link>
  <pubDate>Mon, 27 Oct 2026 04:00:00 GMT</pubDate></item>
<item><title>Old story</title><link>https://ex.com/old</link>
  <pubDate>Fri, 24 Oct 2026 04:00:00 GMT</pubDate></item>
<item><title>No date</title><link>https://ex.com/nodate</link></item>
</channel></rss>"""

GOOGLE_NEWS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Google News</title>
<item><title>Quake hits northern Japan - Reuters</title><link>https://news.google.com/rss/articles/x</link>
  <description>&lt;a href="x"&gt;Quake hits northern Japan&lt;/a&gt;</description>
  <pubDate>Mon, 27 Oct 2026 09:00:00 GMT</pubDate></item>
</channel></rss>"""


def _source(kind: FeedKind) -> tuple[Source, Feed]:
    feed = Feed(url="https://ex.com/feed", section=Section.US, kind=kind)
    return Source(id="ex", name="Example", lean=Lean.CENTER, paywalled=False, feeds=(feed,)), feed


def test_parses_recent_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(feeds, "fetch_bytes", lambda url: RSS)
    source, feed = _source(FeedKind.RSS)
    articles = feeds.fetch_feed(source, feed, NOW)
    assert [a.title for a in articles] == ["Senate passes funding bill", "Opinion | The bill is a mistake"]
    first, second = articles
    assert first.summary == "The Senate voted 52-48 late Monday."
    assert first.published_at == "2026-10-27T03:00:00Z"
    assert first.id == feeds.article_id("https://ex.com/a")
    assert not first.is_opinion and second.is_opinion


def test_google_news_strips_outlet_suffix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(feeds, "fetch_bytes", lambda url: GOOGLE_NEWS)
    source, feed = _source(FeedKind.GOOGLE_NEWS)
    (only,) = feeds.fetch_feed(source, feed, NOW)
    assert only.title == "Quake hits northern Japan"
    assert only.summary == ""


def test_stale_feed_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(feeds, "fetch_bytes", lambda url: RSS)
    source, feed = _source(FeedKind.RSS)
    with pytest.raises(FetchFailed, match="no entries in the last"):
        feeds.fetch_feed(source, feed, datetime(2026, 11, 5, tzinfo=UTC))
