"""Checks a day's draft against that day's ingest bundle and publishes the brief.

    python -m brief.build --date 2026-10-27

Reads data/ingest/<date>.json and data/drafts/<date>/, writes
docs/data/briefs/<date>.json and refreshes docs/data/index.json. Every problem
in the draft is reported in one go so the writer can fix them in one pass.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from brief import draft, published
from brief.config import (
    BRIEFS_DIR,
    DRAFTS_DIR,
    INGEST_DIR,
    LEAN_BUCKETS,
    LEAN_ORDER,
    SECTION_TITLES,
    SITE_INDEX_PATH,
    Lean,
    LeanBucket,
    RefKind,
    Section,
    TrendSignal,
)
from brief.models import Article, IngestBundle, Quote, SourceInfo, TrendItem
from brief.serde import SchemaError, load_json, write_json

IMPORTANCE_RANGE = range(1, 6)
MIN_DISPUTE_POSITIONS = 2
SIGNALS_PER_KIND = 10


class BuildError(ValueError):
    pass


@dataclass(frozen=True)
class _Lookup:
    articles: dict[str, Article]
    sources: dict[str, SourceInfo]
    quotes: dict[str, Quote]

    @classmethod
    def from_bundle(cls, bundle: IngestBundle) -> _Lookup:
        return cls(
            articles={article.id: article for article in bundle.articles},
            sources={source.id: source for source in bundle.sources},
            quotes={quote.symbol: quote for quote in bundle.quotes},
        )


def build(date: str) -> Path:
    bundle = load_json(IngestBundle, INGEST_DIR / f"{date}.json")
    if bundle.date != date:
        raise BuildError(f"ingest bundle is for {bundle.date}, not {date}")
    day = draft.load_day_draft(DRAFTS_DIR / date)
    lookup = _Lookup.from_bundle(bundle)
    problems = _check_front(day.front, lookup) + _check_sections(day.sections, lookup)
    if problems:
        listing = "\n".join(f"  - {problem}" for problem in problems)
        raise BuildError(f"{len(problems)} problem(s) in data/drafts/{date}:\n{listing}")
    path = BRIEFS_DIR / f"{date}.json"
    write_json(_assemble(bundle, day, lookup), path, pretty=True)
    _update_index(date)
    return path


# --- checks -----------------------------------------------------------------


def _check_front(front: draft.FrontDraft, lookup: _Lookup) -> list[str]:
    problems = []
    if not front.overview.strip():
        problems.append("front: overview is empty")
    for mover in front.markets.movers:
        if mover.symbol not in lookup.quotes:
            problems.append(f"front: mover {mover.symbol!r} is not a quote in today's ingest")
    if not front.markets.concept.term.strip() or not front.markets.concept.explanation.strip():
        problems.append("front: markets.concept needs a term and an explanation")
    return problems


def _check_sections(sections: dict[Section, draft.SectionDraft], lookup: _Lookup) -> list[str]:
    problems = []
    story_ids = Counter(story.id for section in sections.values() for story in section.stories)
    problems += [f"story id {story_id!r} is used {count} times" for story_id, count in story_ids.items() if count > 1]
    for section, section_draft in sections.items():
        web_ids = Counter(ref.id for ref in section_draft.web_refs)
        problems += [f"{section}: web ref id {ref_id!r} is declared {n} times" for ref_id, n in web_ids.items() if n > 1]
        problems += [f"{section}: web ref id {ref_id!r} collides with an article id" for ref_id in web_ids if ref_id in lookup.articles]
        for story in section_draft.stories:
            problems += _check_story(f"{section}/{story.id}", story, set(web_ids), lookup)
    return problems


def _check_story(where: str, story: draft.StoryDraft, web_ids: set[str], lookup: _Lookup) -> list[str]:
    problems = []
    if not story.headline.strip() or not story.summary.strip():
        problems.append(f"{where}: headline and summary are required")
    if story.importance not in IMPORTANCE_RANGE:
        problems.append(f"{where}: importance {story.importance} is outside 1-5")
    if not story.facts:
        problems.append(f"{where}: needs at least one fact")
    for field_name, ref_id in _story_refs(story):
        if ref_id not in lookup.articles and ref_id not in web_ids:
            problems.append(f"{where}: {field_name} cites unknown ref {ref_id!r}")
    for index, claim in enumerate(story.facts):
        if not claim.refs:
            problems.append(f"{where}: facts[{index}] has no refs")
        opinion = [ref for ref in claim.refs if ref in lookup.articles and lookup.articles[ref].is_opinion]
        if opinion:
            problems.append(f"{where}: facts[{index}] cites opinion pieces {opinion}")
    for index, dispute in enumerate(story.disputed):
        if len(dispute.positions) < MIN_DISPUTE_POSITIONS:
            problems.append(f"{where}: disputed[{index}] needs at least {MIN_DISPUTE_POSITIONS} positions")
    for framing in story.framing:
        if framing.ref in web_ids:
            problems.append(f"{where}: framing must cite an ingested article, not web ref {framing.ref!r}")
    for index, omission in enumerate(story.left_out):
        unknown = [source_id for source_id in omission.missing_from if source_id not in lookup.sources]
        if unknown or not omission.missing_from:
            problems.append(f"{where}: left_out[{index}].missing_from needs known source ids, got {list(omission.missing_from)}")
    coverage = Counter(note.ref for note in story.coverage)
    problems += [f"{where}: coverage lists {ref!r} {n} times" for ref, n in coverage.items() if n > 1]
    return problems


def _story_refs(story: draft.StoryDraft) -> Iterator[tuple[str, str]]:
    for index, claim in enumerate(story.facts):
        yield from ((f"facts[{index}]", ref) for ref in claim.refs)
    for index, dispute in enumerate(story.disputed):
        for position in dispute.positions:
            yield from ((f"disputed[{index}]", ref) for ref in position.refs)
    for index, omission in enumerate(story.left_out):
        yield from ((f"left_out[{index}]", ref) for ref in omission.refs)
    yield from (("framing", framing.ref) for framing in story.framing)
    yield from (("coverage", note.ref) for note in story.coverage)


# --- assembly ---------------------------------------------------------------


def _assemble(bundle: IngestBundle, day: draft.DayDraft, lookup: _Lookup) -> published.Brief:
    sections = tuple(
        published.SectionBlock(
            id=section,
            title=SECTION_TITLES[section],
            stories=_stories(day.sections[section], lookup),
        )
        for section in Section
    )
    return published.Brief(
        date=bundle.date,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        ingested_at=bundle.generated_at,
        overview=day.front.overview,
        sections=sections,
        markets=_markets(day.front.markets, bundle, lookup),
        trending=day.front.trending,
        signals=_signals(bundle.trends),
        sources=bundle.sources,
        stats=published.Stats(
            outlets=len({article.source_id for article in bundle.articles}),
            articles=len(bundle.articles),
            clusters=sum(1 for cluster in bundle.clusters if len(cluster.source_ids) > 1),
            failed_fetches=len(bundle.errors),
        ),
    )


def _stories(section_draft: draft.SectionDraft, lookup: _Lookup) -> tuple[published.Story, ...]:
    web_refs = {ref.id: ref for ref in section_draft.web_refs}
    stories = (_story(story, lookup, web_refs) for story in section_draft.stories)
    return tuple(sorted(stories, key=lambda story: story.importance, reverse=True))


def _story(story: draft.StoryDraft, lookup: _Lookup, web_refs: dict[str, draft.WebRef]) -> published.Story:
    notes = {note.ref: note for note in story.coverage}
    ref_ids = dict.fromkeys(ref for _, ref in _story_refs(story))
    refs = {ref_id: _ref(ref_id, lookup, web_refs, notes) for ref_id in ref_ids}
    ordered = sorted(refs.values(), key=lambda ref: (LEAN_ORDER.index(ref.lean), ref.outlet))
    return published.Story(
        id=story.id,
        headline=story.headline,
        region=story.region,
        importance=story.importance,
        summary=story.summary,
        why_it_matters=story.why_it_matters,
        background=story.background,
        facts=tuple(
            published.Fact(text=claim.text, refs=claim.refs, outlet_count=_outlet_count(claim.refs, refs))
            for claim in story.facts
        ),
        disputed=tuple(
            published.Dispute(
                topic=dispute.topic,
                positions=tuple(published.Position(claim=p.claim, refs=p.refs) for p in dispute.positions),
            )
            for dispute in story.disputed
        ),
        framing=tuple(published.Framing(ref=framing.ref, note=framing.note) for framing in story.framing),
        left_out=tuple(
            published.Omission(
                text=omission.text,
                refs=omission.refs,
                missing_from=tuple(lookup.sources[source_id].name for source_id in omission.missing_from),
            )
            for omission in story.left_out
        ),
        social=story.social,
        refs=tuple(ordered),
        lean_counts=_lean_counts(ordered),
    )


def _ref(
    ref_id: str, lookup: _Lookup, web_refs: dict[str, draft.WebRef], notes: dict[str, draft.CoverageNote]
) -> published.Ref:
    note = notes.get(ref_id)
    takeaway = note.takeaway if note else ""
    if ref_id in web_refs:
        web = web_refs[ref_id]
        return published.Ref(
            id=ref_id, kind=RefKind.WEB, source_id="", outlet=web.outlet, lean=Lean.UNRATED, paywalled=False,
            url=web.url, title=web.title, published_at="", read_full=note.read_full if note else True,
            takeaway=takeaway,
        )
    article = lookup.articles[ref_id]
    source = lookup.sources[article.source_id]
    return published.Ref(
        id=ref_id, kind=RefKind.ARTICLE, source_id=source.id, outlet=source.name, lean=source.lean,
        paywalled=source.paywalled, url=article.url, title=article.title, published_at=article.published_at,
        read_full=note.read_full if note else False, takeaway=takeaway,
    )


def _outlet_count(ref_ids: tuple[str, ...], refs: dict[str, published.Ref]) -> int:
    return len({refs[ref_id].source_id or refs[ref_id].outlet for ref_id in ref_ids})


def _lean_counts(refs: list[published.Ref]) -> published.LeanCounts:
    outlets = {(ref.source_id or ref.outlet): LEAN_BUCKETS[ref.lean] for ref in refs}
    counts = Counter(outlets.values())
    return published.LeanCounts(
        left=counts[LeanBucket.LEFT],
        center=counts[LeanBucket.CENTER],
        right=counts[LeanBucket.RIGHT],
        unrated=counts[LeanBucket.UNRATED],
    )


def _markets(markets: draft.MarketsDraft, bundle: IngestBundle, lookup: _Lookup) -> published.MarketsBlock:
    return published.MarketsBlock(
        summary=markets.summary,
        movers=tuple(
            published.Mover(symbol=mover.symbol, name=lookup.quotes[mover.symbol].name, why=mover.why)
            for mover in markets.movers
        ),
        concept=markets.concept,
        watch=markets.watch,
        quotes=bundle.quotes,
    )


def _signals(trends: tuple[TrendItem, ...]) -> tuple[TrendItem, ...]:
    by_kind = {signal: [item for item in trends if item.signal is signal] for signal in TrendSignal}
    return tuple(item for items in by_kind.values() for item in items[:SIGNALS_PER_KIND])


def _update_index(date: str) -> None:
    dates = {date}
    if SITE_INDEX_PATH.exists():
        dates |= set(load_json(published.SiteIndex, SITE_INDEX_PATH).dates)
    ordered = tuple(sorted(dates, reverse=True))
    write_json(published.SiteIndex(latest=ordered[0], dates=ordered), SITE_INDEX_PATH, pretty=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()
    try:
        path = build(args.date)
    except (BuildError, SchemaError, FileNotFoundError) as error:
        raise SystemExit(str(error)) from error
    print(f"published {path}")


if __name__ == "__main__":
    main()
