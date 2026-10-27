"""What the writer produces each day, before `brief.build` checks and publishes it.

A day's draft is a directory, data/drafts/<date>/, holding one file per section
(us.json, world.json, business.json, nyc.json) and front.json. The writer only
supplies text and reference ids; outlet names, leans, URLs and market numbers
are filled in by code from the ingest bundle so they can't be mistyped.

Reference ids are either ingest article ids or ids of web_refs declared in the
same file (pages the writer found through web research).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from brief.config import Section, TrendSignal
from brief.serde import load_json

FRONT_FILE = "front.json"


@dataclass(frozen=True)
class WebRef:
    id: str
    url: str
    title: str
    outlet: str


@dataclass(frozen=True)
class Claim:
    text: str
    refs: tuple[str, ...]


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
class CoverageNote:
    ref: str
    takeaway: str
    read_full: bool


@dataclass(frozen=True)
class StoryDraft:
    id: str
    headline: str
    region: str
    importance: int
    summary: str
    why_it_matters: str
    background: str
    facts: tuple[Claim, ...]
    disputed: tuple[Dispute, ...]
    framing: tuple[Framing, ...]
    left_out: tuple[Omission, ...]
    coverage: tuple[CoverageNote, ...]
    social: str


@dataclass(frozen=True)
class SectionDraft:
    stories: tuple[StoryDraft, ...]
    web_refs: tuple[WebRef, ...]


@dataclass(frozen=True)
class Mover:
    symbol: str
    why: str


@dataclass(frozen=True)
class Concept:
    term: str
    explanation: str


@dataclass(frozen=True)
class MarketsDraft:
    summary: str
    movers: tuple[Mover, ...]
    concept: Concept
    watch: tuple[str, ...]


@dataclass(frozen=True)
class TrendNote:
    title: str
    context: str
    signal: TrendSignal


@dataclass(frozen=True)
class FrontDraft:
    overview: str
    markets: MarketsDraft
    trending: tuple[TrendNote, ...]


@dataclass(frozen=True)
class DayDraft:
    front: FrontDraft
    sections: dict[Section, SectionDraft]


def load_day_draft(directory: Path) -> DayDraft:
    if not directory.is_dir():
        raise FileNotFoundError(f"no draft directory at {directory}")
    return DayDraft(
        front=load_json(FrontDraft, directory / FRONT_FILE),
        sections={section: load_json(SectionDraft, directory / f"{section}.json") for section in Section},
    )
