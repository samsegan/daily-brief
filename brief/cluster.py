"""Groups articles about the same event into candidate story clusters.

Pure-Python TF-IDF over title and summary, then single-pass "leader" clustering:
each article joins the most similar existing cluster centroid above a threshold,
or starts a new one. An inverted index keeps candidate lookups small, so a run
over a few thousand articles takes well under a second. The clusters are a
starting point for the writer, who merges or splits them as needed.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field

from brief.config import (
    CLUSTER_INDEX_TERMS,
    CLUSTER_SIMILARITY_THRESHOLD,
    CLUSTER_TOP_TERMS,
    TITLE_WEIGHT,
    Section,
)
from brief.models import Article, Cluster

Vector = dict[str, float]

_TOKEN = re.compile(r"[a-z0-9][a-z0-9'\-]+")
_MIN_TOKEN_LENGTH = 3
_STOPWORDS = frozenset(
    """
    about above after again against all also am an and any are as at be because been before being below
    between both but by can could did do does doing down during each few for from further had has have
    having he her here hers him his how if in into is it its just me more most my no nor not now of off
    on once only or other our out over own same say says said she should so some such than that the their
    them then there these they this those through to too under until up very was we were what when where
    which while who whom why will with would you your new news live latest update updates video watch
    week year years day days get gets got make makes made one two first last time report reports amid
    """.split()
)
_NO_MATCH = -1


@dataclass
class _Group:
    member_indices: list[int] = field(default_factory=list)
    centroid: Vector = field(default_factory=dict)
    norm: float = 0.0

    def add(self, index: int, vector: Vector) -> None:
        self.member_indices.append(index)
        for term, weight in vector.items():
            self.centroid[term] = self.centroid.get(term, 0.0) + weight
        self.norm = math.sqrt(sum(weight * weight for weight in self.centroid.values()))

    def similarity(self, vector: Vector) -> float:
        dot = sum(weight * self.centroid.get(term, 0.0) for term, weight in vector.items())
        return dot / self.norm


def tokenize(text: str) -> list[str]:
    tokens = []
    for raw in _TOKEN.findall(text.lower()):
        token = _normalize(raw.removesuffix("'s").strip("'-"))
        if len(token) >= _MIN_TOKEN_LENGTH and token not in _STOPWORDS and not token.isdigit():
            tokens.append(token)
    return tokens


def cluster_articles(articles: Sequence[Article]) -> tuple[Cluster, ...]:
    vectors = _tfidf_vectors(articles)
    groups: list[_Group] = []
    postings: dict[str, set[int]] = defaultdict(set)
    for index in sorted(range(len(articles)), key=lambda i: articles[i].published_at):
        vector = vectors[index]
        best, score = _best_group(vector, groups, postings)
        if best == _NO_MATCH or score < CLUSTER_SIMILARITY_THRESHOLD:
            best = len(groups)
            groups.append(_Group())
        groups[best].add(index, vector)
        for term in _top_terms(vector, CLUSTER_INDEX_TERMS):
            postings[term].add(best)
    return _finalize(groups, articles)


def _normalize(token: str) -> str:
    if len(token) > 5 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _tfidf_vectors(articles: Sequence[Article]) -> list[Vector]:
    term_counts = [_term_counts(article) for article in articles]
    document_frequency = Counter(term for counts in term_counts for term in counts)
    total = len(articles)
    vectors = []
    for counts in term_counts:
        weights = {
            term: count * (math.log((total + 1) / (document_frequency[term] + 1)) + 1.0)
            for term, count in counts.items()
        }
        norm = math.sqrt(sum(weight * weight for weight in weights.values()))
        vectors.append({term: weight / norm for term, weight in weights.items()} if norm else {})
    return vectors


def _term_counts(article: Article) -> Counter[str]:
    counts = Counter(tokenize(article.summary))
    for token in tokenize(article.title):
        counts[token] += TITLE_WEIGHT
    return counts


def _best_group(vector: Vector, groups: list[_Group], postings: dict[str, set[int]]) -> tuple[int, float]:
    candidates = set().union(*(postings.get(term, set()) for term in vector)) if vector else set()
    best, best_score = _NO_MATCH, 0.0
    for candidate in candidates:
        score = groups[candidate].similarity(vector)
        if score > best_score:
            best, best_score = candidate, score
    return best, best_score


def _top_terms(vector: Vector, count: int) -> list[str]:
    return [term for term, _ in sorted(vector.items(), key=lambda item: item[1], reverse=True)[:count]]


def _finalize(groups: list[_Group], articles: Sequence[Article]) -> tuple[Cluster, ...]:
    def rank(group: _Group) -> tuple[int, int, str]:
        members = [articles[index] for index in group.member_indices]
        outlets = len({article.source_id for article in members})
        return outlets, len(members), max(article.published_at for article in members)

    ordered = sorted(groups, key=rank, reverse=True)
    clusters = []
    for number, group in enumerate(ordered, start=1):
        members = sorted((articles[index] for index in group.member_indices), key=lambda a: a.published_at)
        clusters.append(
            Cluster(
                id=f"c{number:03d}",
                section=_majority_section(members),
                article_ids=tuple(article.id for article in members),
                source_ids=tuple(dict.fromkeys(article.source_id for article in members)),
                top_terms=tuple(_top_terms(group.centroid, CLUSTER_TOP_TERMS)),
            )
        )
    return tuple(clusters)


def _majority_section(members: Sequence[Article]) -> Section:
    counts = Counter(article.section for article in members)
    order = list(Section)
    return max(counts, key=lambda section: (counts[section], -order.index(section)))
