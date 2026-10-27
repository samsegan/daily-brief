"""Fetches every feed, market series and trend signal, clusters the articles,
and writes one IngestBundle JSON for the day.

    python -m brief.ingest --out DIR

Individual sources fail all the time (a feed moves, a site blocks a runner IP);
those are recorded in bundle.errors and the run carries on. The run itself
fails only when no articles came back at all.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Iterable
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from brief.catalog import load_instruments, load_sources, source_info
from brief.cluster import cluster_articles
from brief.config import HOME_TZ, HTTP_WORKERS, INGEST_DIR
from brief.feeds import fetch_feed
from brief.http import FetchFailed
from brief.markets import fetch_quote
from brief.models import Article, FetchError, IngestBundle
from brief.serde import write_json
from brief.trends import trend_jobs

log = logging.getLogger("brief.ingest")


class IngestFailed(RuntimeError):
    pass


def run_ingest(now: datetime) -> IngestBundle:
    sources = load_sources()
    instruments = load_instruments()
    today = now.astimezone(HOME_TZ).date()
    with ThreadPoolExecutor(max_workers=HTTP_WORKERS) as pool:
        feed_jobs = {
            f"{source.id} {feed.url}": pool.submit(fetch_feed, source, feed, now)
            for source in sources
            for feed in source.feeds
        }
        quote_jobs = {instrument.symbol: pool.submit(fetch_quote, instrument, today) for instrument in instruments}
        trend_futures = {job.target: pool.submit(job.run) for job in trend_jobs(today)}
        article_batches, feed_errors = _gather(feed_jobs)
        quotes, quote_errors = _gather(quote_jobs)
        trend_batches, trend_errors = _gather(trend_futures)

    articles = _dedupe(article for batch in article_batches for article in batch)
    if not articles:
        raise IngestFailed(f"no articles from any of {len(feed_jobs)} feeds")
    trends = [item for batch in trend_batches for item in batch]
    return IngestBundle(
        date=today.isoformat(),
        generated_at=now.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        sources=tuple(source_info(source) for source in sources),
        articles=articles,
        clusters=cluster_articles(articles),
        quotes=tuple(quotes),
        trends=tuple(trends),
        errors=tuple(feed_errors + quote_errors + trend_errors),
    )


def _gather[T](jobs: dict[str, Future[T]]) -> tuple[list[T], list[FetchError]]:
    results: list[T] = []
    errors: list[FetchError] = []
    for target, future in jobs.items():
        try:
            results.append(future.result())
        except FetchFailed as failure:
            errors.append(FetchError(target=target, url=failure.url, error=failure.reason))
    return results, errors


def _dedupe(articles: Iterable[Article]) -> tuple[Article, ...]:
    """One article per URL, and per outlet headline (outlets repeat stories across section feeds)."""
    seen_ids: set[str] = set()
    seen_titles: set[tuple[str, str]] = set()
    unique = []
    for article in articles:
        title_key = (article.source_id, article.title.casefold())
        if article.id in seen_ids or title_key in seen_titles:
            continue
        seen_ids.add(article.id)
        seen_titles.add(title_key)
        unique.append(article)
    return tuple(unique)


def _log_summary(bundle: IngestBundle, path: Path) -> None:
    log.info(
        "wrote %s: %d articles from %d outlets, %d clusters (%d multi-outlet), %d quotes, %d trend items",
        path,
        len(bundle.articles),
        len({article.source_id for article in bundle.articles}),
        len(bundle.clusters),
        sum(1 for cluster in bundle.clusters if len(cluster.source_ids) > 1),
        len(bundle.quotes),
        len(bundle.trends),
    )
    for error in bundle.errors:
        log.warning("failed %s: %s", error.target, error.error)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=INGEST_DIR, help="directory for <date>.json")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    bundle = run_ingest(datetime.now(UTC))
    path = args.out / f"{bundle.date}.json"
    write_json(bundle, path, pretty=False)
    _log_summary(bundle, path)


if __name__ == "__main__":
    main()
