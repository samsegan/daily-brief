"""Small builders for test data."""

from __future__ import annotations

from brief.config import Lean, Section
from brief.models import Article, SourceInfo


def article(
    article_id: str,
    source_id: str,
    title: str,
    summary: str = "",
    section: Section = Section.US,
    published_at: str = "2026-10-27T08:00:00Z",
    is_opinion: bool = False,
) -> Article:
    return Article(
        id=article_id,
        source_id=source_id,
        section=section,
        title=title,
        summary=summary,
        url=f"https://{source_id}.example/{article_id}",
        published_at=published_at,
        is_opinion=is_opinion,
    )


def source(source_id: str, lean: Lean, paywalled: bool = False) -> SourceInfo:
    return SourceInfo(id=source_id, name=source_id.upper(), lean=lean, paywalled=paywalled)
