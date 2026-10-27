from __future__ import annotations

from brief.cluster import cluster_articles, tokenize
from brief.config import Section
from tests.factories import article


def test_tokenize_drops_stopwords_and_normalizes_plurals() -> None:
    assert tokenize("The Senators' votes on the shutdown, explained") == ["senator", "vote", "shutdown", "explained"]


def test_groups_same_event_across_outlets() -> None:
    articles = [
        article("a1", "fox", "Senate passes stopgap funding bill to end government shutdown"),
        article("a2", "nyt", "Senate votes to end shutdown with stopgap funding bill", published_at="2026-10-27T08:05:00Z"),
        article("a3", "wsj", "Shutdown ends as Senate passes funding bill", published_at="2026-10-27T08:10:00Z"),
        article("b1", "bbc", "Powerful earthquake strikes northern Japan", section=Section.WORLD),
        article("b2", "nikkei", "Earthquake in northern Japan triggers tsunami warning", section=Section.WORLD),
        article("c1", "gothamist", "MTA unveils new subway map", section=Section.NYC),
    ]
    clusters = cluster_articles(articles)
    groups = {frozenset(cluster.article_ids) for cluster in clusters}
    assert groups == {frozenset({"a1", "a2", "a3"}), frozenset({"b1", "b2"}), frozenset({"c1"})}
    assert clusters[0].article_ids == ("a1", "a2", "a3")
    assert clusters[0].source_ids == ("fox", "nyt", "wsj")
    assert clusters[0].id == "c001"
    assert clusters[1].section is Section.WORLD
