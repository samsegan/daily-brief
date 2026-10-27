from __future__ import annotations

from datetime import date

import pytest

from brief import trends
from brief.config import TrendSignal

TOP = {
    "items": [
        {
            "articles": [
                {"article": "Main_Page", "views": 5_000_000, "rank": 1},
                {"article": "Special:Search", "views": 900_000, "rank": 2},
                {"article": "World_Series", "views": 400_000, "rank": 3},
                {"article": "New_York_City", "views": 250_000, "rank": 4},
            ]
        }
    ]
}

GOOGLE = b"""<?xml version="1.0"?>
<rss xmlns:ht="https://trends.google.com/trending/rss" version="2.0"><channel>
<item><title>world series</title><ht:approx_traffic>500K+</ht:approx_traffic>
  <ht:news_item><ht:news_item_title>Game 3 recap</ht:news_item_title>
  <ht:news_item_url>https://ex.com/g3</ht:news_item_url><ht:news_item_source>AP</ht:news_item_source></ht:news_item>
</item></channel></rss>"""


def test_most_read_skips_non_articles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(trends, "fetch_json", lambda url: TOP)
    items = trends.wikipedia_most_read(date(2026, 10, 26))
    assert [item.title for item in items] == ["World Series", "New York City"]
    assert items[0].url == "https://en.wikipedia.org/wiki/World_Series"
    assert items[0].detail == "400,000 views"
    assert items[0].signal is TrendSignal.WIKIPEDIA


def test_google_trends_items(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(trends, "fetch_bytes", lambda url: GOOGLE)
    (item,) = trends.google_trends()
    assert (item.title, item.detail) == ("world series", "500K+ searches")
    assert item.related[0].outlet == "AP"
