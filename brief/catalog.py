"""Loads the outlet and market-instrument catalogs from config/*.toml."""

from __future__ import annotations

import tomllib
from collections import Counter
from pathlib import Path

from brief.config import MARKETS_PATH, SOURCES_PATH
from brief.models import Instrument, Source, SourceInfo
from brief.serde import from_jsonable


class CatalogError(ValueError):
    pass


def load_sources(path: Path = SOURCES_PATH) -> tuple[Source, ...]:
    sources = _load_table(path, "source", Source)
    _require_unique(path, [source.id for source in sources])
    return sources


def load_instruments(path: Path = MARKETS_PATH) -> tuple[Instrument, ...]:
    instruments = _load_table(path, "instrument", Instrument)
    _require_unique(path, [instrument.symbol for instrument in instruments])
    return instruments


def source_info(source: Source) -> SourceInfo:
    return SourceInfo(id=source.id, name=source.name, lean=source.lean, paywalled=source.paywalled)


def _load_table[T](path: Path, key: str, cls: type[T]) -> tuple[T, ...]:
    with path.open("rb") as handle:
        document = tomllib.load(handle)
    rows = document.get(key)
    if not isinstance(rows, list) or not rows:
        raise CatalogError(f"{path.name}: expected at least one [[{key}]] table")
    return tuple(from_jsonable(cls, row, f"{path.name}[{index}]") for index, row in enumerate(rows))


def _require_unique(path: Path, keys: list[str]) -> None:
    duplicates = sorted(key for key, count in Counter(keys).items() if count > 1)
    if duplicates:
        raise CatalogError(f"{path.name}: duplicate ids {duplicates}")
