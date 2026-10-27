"""Text cleanup shared by the feed and trend parsers."""

from __future__ import annotations

import html
import re

_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")
_ELLIPSIS = "…"


def strip_html(markup: str) -> str:
    return _SPACE.sub(" ", html.unescape(_TAG.sub(" ", markup))).strip()


def truncate_words(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:.") + _ELLIPSIS
