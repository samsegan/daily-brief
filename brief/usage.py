"""Token use and estimated API cost of writing an edition.

    python -m brief.usage --date 2026-10-27 --label session --since 2026-10-27T10:40:00Z
    python -m brief.usage --date 2026-10-27 --label writers --since ... --until ... --files a.jsonl b.jsonl

Reads Claude Code transcripts (JSONL; each assistant entry carries the API's
usage block), sums tokens per model for messages between --since and --until
(default: now), prices
them from config/pricing.toml, and records the result as one labelled part of
data/drafts/<date>/usage.json. Running it again with the same label replaces
that part. Without --files it reads every transcript under ~/.claude/projects
that changed since --since, which in a scheduled session is exactly its own.

On a Claude plan none of this is billed per token; the cost is what the same
tokens would cost at API list prices.
"""

from __future__ import annotations

import argparse
import json
import tomllib
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from brief.config import (
    DRAFTS_DIR,
    PRICING_PATH,
    SEARCHES_PER_PRICE_UNIT,
    TOKENS_PER_MILLION,
    TRANSCRIPTS_DIR,
    USAGE_FILE,
)
from brief.serde import from_jsonable, load_json, write_json

TRANSCRIPT_GLOB = "*.jsonl"
ASSISTANT_ENTRY = "assistant"
# Claude Code's WebSearch tool runs outside the logged API usage, so searches are
# counted from its tool calls. The model call it makes to read results isn't
# logged at all and isn't included.
WEB_SEARCH_TOOL = "WebSearch"
TOOL_USE_BLOCK = "tool_use"


class UsageError(ValueError):
    pass


@dataclass(frozen=True)
class ModelPrice:
    id: str
    input: float
    output: float
    cache_write_5m: float
    cache_write_1h: float
    cache_read: float


@dataclass(frozen=True)
class PricingTable:
    web_search_per_thousand: float
    model: tuple[ModelPrice, ...]


@dataclass(frozen=True)
class TokenCounts:
    input: int
    cache_write_5m: int
    cache_write_1h: int
    cache_read: int
    output: int
    web_searches: int

    @property
    def total(self) -> int:
        return self.input + self.cache_write_5m + self.cache_write_1h + self.cache_read + self.output

    def plus(self, other: TokenCounts) -> TokenCounts:
        return TokenCounts(
            input=self.input + other.input,
            cache_write_5m=self.cache_write_5m + other.cache_write_5m,
            cache_write_1h=self.cache_write_1h + other.cache_write_1h,
            cache_read=self.cache_read + other.cache_read,
            output=self.output + other.output,
            web_searches=self.web_searches + other.web_searches,
        )


ZERO = TokenCounts(input=0, cache_write_5m=0, cache_write_1h=0, cache_read=0, output=0, web_searches=0)


@dataclass(frozen=True)
class ModelUsage:
    model: str
    requests: int
    tokens: TokenCounts
    cost_usd: float


@dataclass(frozen=True)
class UsagePart:
    label: str
    since: str
    until: str
    total_tokens: int
    cost_usd: float
    models: tuple[ModelUsage, ...]


@dataclass(frozen=True)
class UsageReport:
    parts: tuple[UsagePart, ...]


@dataclass(frozen=True)
class _Message:
    model: str
    timestamp: str
    tokens: TokenCounts


def measure(label: str, since: datetime, until: datetime, paths: Iterable[Path], pricing: PricingTable) -> UsagePart:
    messages = [message for path in paths for message in _read_transcript(path, since, until)]
    if not messages:
        raise UsageError(f"no assistant messages between {since:%Y-%m-%dT%H:%M:%SZ} and {until:%H:%M:%SZ}")
    prices = {price.id: price for price in pricing.model}
    by_model: dict[str, list[TokenCounts]] = defaultdict(list)
    for message in messages:
        by_model[message.model].append(message.tokens)
    models = []
    for model, counts in sorted(by_model.items()):
        if model not in prices:
            raise UsageError(f"no price for model {model!r}; add it to {PRICING_PATH.name}")
        tokens = _sum(counts)
        cost = _cost(tokens, prices[model], pricing)
        models.append(ModelUsage(model=model, requests=len(counts), tokens=tokens, cost_usd=cost))
    return UsagePart(
        label=label,
        since=min(message.timestamp for message in messages),
        until=max(message.timestamp for message in messages),
        total_tokens=sum(model.tokens.total for model in models),
        cost_usd=round(sum(model.cost_usd for model in models), 2),
        models=tuple(models),
    )


def record(date: str, part: UsagePart) -> Path:
    path = DRAFTS_DIR / date / USAGE_FILE
    parts = load_json(UsageReport, path).parts if path.exists() else ()
    kept = tuple(existing for existing in parts if existing.label != part.label)
    write_json(UsageReport(parts=kept + (part,)), path, pretty=True)
    return path


def changed_transcripts(since: datetime) -> list[Path]:
    return [path for path in TRANSCRIPTS_DIR.rglob(TRANSCRIPT_GLOB) if path.stat().st_mtime >= since.timestamp()]


def _read_transcript(path: Path, since: datetime, until: datetime) -> list[_Message]:
    """One result per API message. Claude Code logs each content block of a message
    as its own entry with the message's usage repeated, so usage is taken once per
    message id and searches are counted from every entry's tool calls."""
    latest: dict[str, _Message] = {}
    searches: dict[str, set[str]] = defaultdict(set)
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue  # a live transcript can end mid-line
            message = entry.get("message")
            if entry.get("type") != ASSISTANT_ENTRY or not isinstance(message, dict) or not message.get("usage"):
                continue
            if not since <= datetime.fromisoformat(entry["timestamp"]) <= until:
                continue
            searches[message["id"]] |= _search_calls(message)
            tokens = _token_counts(message["usage"], path)
            if tokens.total:
                latest[message["id"]] = _Message(model=message["model"], timestamp=entry["timestamp"], tokens=tokens)
    return [
        _Message(model=m.model, timestamp=m.timestamp, tokens=m.tokens.plus(_searches_only(len(searches[message_id]))))
        for message_id, m in latest.items()
    ]


def _search_calls(message: dict) -> set[str]:
    content = message.get("content")
    blocks = content if isinstance(content, list) else []
    return {
        block["id"]
        for block in blocks
        if block.get("type") == TOOL_USE_BLOCK and block.get("name") == WEB_SEARCH_TOOL
    }


def _searches_only(count: int) -> TokenCounts:
    return TokenCounts(input=0, cache_write_5m=0, cache_write_1h=0, cache_read=0, output=0, web_searches=count)


def _token_counts(usage: dict, path: Path) -> TokenCounts:
    written = usage.get("cache_creation_input_tokens", 0)
    by_ttl = usage.get("cache_creation")
    if written and not by_ttl:
        raise UsageError(f"{path.name}: cache writes without a 5m/1h breakdown can't be priced")
    return TokenCounts(
        input=usage.get("input_tokens", 0),
        cache_write_5m=by_ttl["ephemeral_5m_input_tokens"] if by_ttl else 0,
        cache_write_1h=by_ttl["ephemeral_1h_input_tokens"] if by_ttl else 0,
        cache_read=usage.get("cache_read_input_tokens", 0),
        output=usage.get("output_tokens", 0),
        web_searches=usage.get("server_tool_use", {}).get("web_search_requests", 0),
    )


def _sum(counts: list[TokenCounts]) -> TokenCounts:
    total = ZERO
    for count in counts:
        total = total.plus(count)
    return total


def _cost(tokens: TokenCounts, price: ModelPrice, pricing: PricingTable) -> float:
    per_token = (
        tokens.input * price.input
        + tokens.cache_write_5m * price.cache_write_5m
        + tokens.cache_write_1h * price.cache_write_1h
        + tokens.cache_read * price.cache_read
        + tokens.output * price.output
    ) / TOKENS_PER_MILLION
    return round(per_token + tokens.web_searches * pricing.web_search_per_thousand / SEARCHES_PER_PRICE_UNIT, 4)


def load_pricing(path: Path = PRICING_PATH) -> PricingTable:
    with path.open("rb") as handle:
        return from_jsonable(PricingTable, tomllib.load(handle), path.name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--date", required=True, help="the edition, YYYY-MM-DD")
    parser.add_argument("--label", required=True, help="name for this part, e.g. session or writers")
    parser.add_argument("--since", required=True, type=datetime.fromisoformat, help="ISO time with zone, e.g. 2026-10-27T10:40Z")
    parser.add_argument("--until", type=datetime.fromisoformat, default=datetime.now(UTC), help="ISO time with zone; default now")
    parser.add_argument("--files", nargs="+", type=Path, default=[], help="transcripts to read instead of discovering them")
    args = parser.parse_args()
    paths = args.files or changed_transcripts(args.since)
    try:
        part = measure(args.label, args.since, args.until, paths, load_pricing())
    except UsageError as error:
        raise SystemExit(str(error)) from error
    path = record(args.date, part)
    print(f"{path}: {args.label} {part.total_tokens:,} tokens, ${part.cost_usd:,.2f} at API prices")


if __name__ == "__main__":
    main()
