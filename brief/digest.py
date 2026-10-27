"""Prints a compact Markdown view of a day's ingest bundle for the writer.

    python -m brief.digest --date 2026-10-27 --section us --summaries
    python -m brief.digest --date 2026-10-27 --front

Section mode lists candidate story clusters (most outlets first) with article
ids, outlets, leans and URLs, then single-outlet items. Front mode lists market
quotes, trend signals and feed failures.
"""

from __future__ import annotations

import argparse
from collections import Counter

from brief.config import (
    DIGEST_ARTICLES_PER_CLUSTER,
    DIGEST_MAX_CLUSTERS,
    DIGEST_MAX_SINGLETONS,
    INGEST_DIR,
    LEAN_BUCKETS,
    Lean,
    LeanBucket,
    Section,
    TrendSignal,
    Unit,
)
from brief.models import Article, Cluster, IngestBundle, Quote, SourceInfo
from brief.serde import load_json

LEAN_CODES = {
    Lean.LEFT: "L",
    Lean.LEAN_LEFT: "LL",
    Lean.CENTER: "C",
    Lean.LEAN_RIGHT: "LR",
    Lean.RIGHT: "R",
    Lean.UNRATED: "?",
}
PAYWALL_MARK = " $paywall"
OPINION_MARK = " (opinion)"
BASIS_POINTS = 100


def section_digest(bundle: IngestBundle, section: Section, summaries: bool) -> str:
    articles = {article.id: article for article in bundle.articles}
    sources = {source.id: source for source in bundle.sources}
    in_section = [cluster for cluster in bundle.clusters if cluster.section is section]
    multi = [cluster for cluster in in_section if len(cluster.source_ids) > 1][:DIGEST_MAX_CLUSTERS]
    singles = [cluster for cluster in in_section if len(cluster.source_ids) == 1]
    singles = sorted(singles, key=lambda c: articles[c.article_ids[-1]].published_at, reverse=True)
    lines = [
        f"# Digest {bundle.date} · {section}",
        f"{len(multi)} multi-outlet clusters, {len(singles)} single-outlet clusters in this section.",
        "Leans: L left, LL lean left, C center, LR lean right, R right. $paywall = summary only.",
        "",
        "## Stories covered by several outlets",
    ]
    for cluster in multi:
        lines += _cluster_lines(cluster, articles, sources, summaries)
    lines += ["", "## Single-outlet items (newest first)"]
    for cluster in singles[:DIGEST_MAX_SINGLETONS]:
        lines += _cluster_lines(cluster, articles, sources, summaries)
    return "\n".join(lines)


def front_digest(bundle: IngestBundle) -> str:
    lines = [f"# Front digest {bundle.date}", "", "## Market quotes", "symbol | name | last | day | 1 month | as of"]
    lines += [_quote_line(quote) for quote in bundle.quotes]
    for signal in TrendSignal:
        items = [item for item in bundle.trends if item.signal is signal]
        if items:
            lines += ["", f"## Trend signal: {signal}"]
            lines += [f"- {item.title} — {item.detail} — {item.url}" for item in items]
    lines += ["", f"## Failed fetches ({len(bundle.errors)})"]
    lines += [f"- {error.target}: {error.error}" for error in bundle.errors]
    return "\n".join(lines)


def _cluster_lines(
    cluster: Cluster, articles: dict[str, Article], sources: dict[str, SourceInfo], summaries: bool
) -> list[str]:
    buckets = Counter(LEAN_BUCKETS[sources[source_id].lean] for source_id in cluster.source_ids)
    spread = " ".join(f"{bucket.value[0].upper()}{buckets[bucket]}" for bucket in LeanBucket)
    lines = [
        "",
        f"### {cluster.id} · {len(cluster.source_ids)} outlets ({spread}) · terms: {', '.join(cluster.top_terms)}",
    ]
    for article_id in cluster.article_ids[-DIGEST_ARTICLES_PER_CLUSTER:]:
        article = articles[article_id]
        source = sources[article.source_id]
        marks = (PAYWALL_MARK if source.paywalled else "") + (OPINION_MARK if article.is_opinion else "")
        lines.append(
            f"- `{article.id}` {source.name} [{LEAN_CODES[source.lean]}]{marks} "
            f"{article.published_at[5:16]} — {article.title}"
        )
        if summaries and article.summary:
            lines.append(f"    {article.summary}")
        lines.append(f"    {article.url}")
    hidden = len(cluster.article_ids) - DIGEST_ARTICLES_PER_CLUSTER
    if hidden > 0:
        lines.append(f"- … {hidden} older articles in this cluster")
    return lines


def _quote_line(quote: Quote) -> str:
    return " | ".join(
        (quote.symbol, quote.name, f"{quote.last:,.2f}", _change(quote, quote.previous), _change(quote, quote.month_ago), quote.as_of)
    )


def _change(quote: Quote, base: float) -> str:
    if quote.unit is Unit.PERCENT:
        return f"{(quote.last - base) * BASIS_POINTS:+.0f} bp"
    return f"{(quote.last / base - 1) * 100:+.2f}%"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--section", choices=[section.value for section in Section])
    mode.add_argument("--front", action="store_true")
    parser.add_argument("--summaries", action="store_true", help="include each article's feed summary")
    args = parser.parse_args()
    bundle = load_json(IngestBundle, INGEST_DIR / f"{args.date}.json")
    print(front_digest(bundle) if args.front else section_digest(bundle, Section(args.section), args.summaries))


if __name__ == "__main__":
    main()
