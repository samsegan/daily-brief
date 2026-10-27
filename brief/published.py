"""The brief the website reads: docs/data/briefs/<date>.json."""

from __future__ import annotations

from dataclasses import dataclass

from brief.config import Lean, RefKind, Section
from brief.draft import Concept, TrendNote
from brief.models import Quote, SourceInfo, TrendItem
from brief.usage import UsagePart


@dataclass(frozen=True)
class Ref:
    id: str
    kind: RefKind
    source_id: str
    outlet: str
    lean: Lean
    paywalled: bool
    url: str
    title: str
    published_at: str
    read_full: bool
    takeaway: str


@dataclass(frozen=True)
class Fact:
    text: str
    refs: tuple[str, ...]
    outlet_count: int


@dataclass(frozen=True)
class Position:
    claim: str
    refs: tuple[str, ...]


@dataclass(frozen=True)
class Dispute:
    topic: str
    positions: tuple[Position, ...]


@dataclass(frozen=True)
class Omission:
    text: str
    refs: tuple[str, ...]
    missing_from: tuple[str, ...]


@dataclass(frozen=True)
class Framing:
    ref: str
    note: str


@dataclass(frozen=True)
class LeanCounts:
    left: int
    center: int
    right: int
    unrated: int


@dataclass(frozen=True)
class Story:
    id: str
    headline: str
    region: str
    importance: int
    summary: str
    why_it_matters: str
    background: str
    facts: tuple[Fact, ...]
    disputed: tuple[Dispute, ...]
    framing: tuple[Framing, ...]
    left_out: tuple[Omission, ...]
    social: str
    refs: tuple[Ref, ...]
    lean_counts: LeanCounts


@dataclass(frozen=True)
class SectionBlock:
    id: Section
    title: str
    stories: tuple[Story, ...]


@dataclass(frozen=True)
class Mover:
    symbol: str
    name: str
    why: str


@dataclass(frozen=True)
class MarketsBlock:
    summary: str
    movers: tuple[Mover, ...]
    concept: Concept
    watch: tuple[str, ...]
    quotes: tuple[Quote, ...]


@dataclass(frozen=True)
class Stats:
    outlets: int
    articles: int
    clusters: int
    failed_fetches: int
    stories: int
    facts: int
    corroborated_facts: int


@dataclass(frozen=True)
class UsageBlock:
    """What writing this edition took, in tokens and in dollars at API list prices."""

    total_tokens: int
    cost_usd: float
    parts: tuple[UsagePart, ...]


@dataclass(frozen=True)
class Brief:
    date: str
    generated_at: str
    ingested_at: str
    overview: str
    sections: tuple[SectionBlock, ...]
    markets: MarketsBlock
    trending: tuple[TrendNote, ...]
    signals: tuple[TrendItem, ...]
    sources: tuple[SourceInfo, ...]
    stats: Stats
    usage: UsageBlock


@dataclass(frozen=True)
class SiteIndex:
    latest: str
    dates: tuple[str, ...]
