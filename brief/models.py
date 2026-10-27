"""Data the ingest step produces: the catalog it reads and the bundle it writes."""

from __future__ import annotations

from dataclasses import dataclass

from brief.config import (
    FeedKind,
    InstrumentGroup,
    Lean,
    MarketProvider,
    Section,
    Transform,
    TrendSignal,
    Unit,
)


@dataclass(frozen=True)
class Feed:
    url: str
    section: Section
    kind: FeedKind


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    lean: Lean
    paywalled: bool
    feeds: tuple[Feed, ...]


@dataclass(frozen=True)
class Instrument:
    symbol: str
    name: str
    group: InstrumentGroup
    unit: Unit
    provider: MarketProvider
    transform: Transform
    blurb: str


@dataclass(frozen=True)
class SourceInfo:
    """A source without its feeds: what downstream steps and the site need."""

    id: str
    name: str
    lean: Lean
    paywalled: bool


@dataclass(frozen=True)
class Article:
    id: str
    source_id: str
    section: Section
    title: str
    summary: str
    url: str
    published_at: str
    is_opinion: bool


@dataclass(frozen=True)
class Cluster:
    id: str
    section: Section
    article_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    top_terms: tuple[str, ...]


@dataclass(frozen=True)
class Quote:
    symbol: str
    name: str
    group: InstrumentGroup
    unit: Unit
    blurb: str
    last: float
    previous: float
    month_ago: float
    as_of: str
    provider: MarketProvider


@dataclass(frozen=True)
class RelatedLink:
    title: str
    url: str
    outlet: str


@dataclass(frozen=True)
class TrendItem:
    signal: TrendSignal
    title: str
    url: str
    detail: str
    related: tuple[RelatedLink, ...]


@dataclass(frozen=True)
class FetchError:
    target: str
    url: str
    error: str


@dataclass(frozen=True)
class IngestBundle:
    date: str
    generated_at: str
    sources: tuple[SourceInfo, ...]
    articles: tuple[Article, ...]
    clusters: tuple[Cluster, ...]
    quotes: tuple[Quote, ...]
    trends: tuple[TrendItem, ...]
    errors: tuple[FetchError, ...]
