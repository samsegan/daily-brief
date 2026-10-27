"""Market and economic numbers from free, keyless CSV sources.

FRED (St. Louis Fed) for US indexes, rates, Bitcoin and macro series; Stooq for
world indexes, commodities and currencies FRED doesn't carry. Both serve plain
CSV and answer GitHub Actions runners, which Yahoo Finance rate-limits on sight.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from urllib.parse import urlencode

from brief.config import (
    FRED_LOOKBACK_DAYS,
    MONTH_LOOKBACK_DAYS,
    STOOQ_LOOKBACK_DAYS,
    MarketProvider,
    Transform,
)
from brief.http import FetchFailed, fetch_bytes
from brief.models import Instrument, Quote

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?{query}"
STOOQ_CSV_URL = "https://stooq.com/q/d/l/?{query}"
# FRED marks a day without a value (a market holiday) with "." in older files
# and an empty cell in newer ones.
FRED_MISSING_VALUES = frozenset({".", ""})
STOOQ_DATE_COLUMN = "Date"
STOOQ_CLOSE_COLUMN = "Close"
_PERCENT = 100.0


@dataclass(frozen=True)
class Observation:
    day: date
    value: float


def fetch_quote(instrument: Instrument, today: date) -> Quote:
    match instrument.provider:
        case MarketProvider.FRED:
            observations = _fred_series(instrument.symbol, today)
        case MarketProvider.STOOQ:
            observations = _stooq_series(instrument.symbol, today)
    match instrument.transform:
        case Transform.LEVEL:
            pass
        case Transform.YOY_PERCENT:
            observations = _year_over_year(observations)
    return _to_quote(instrument, observations)


def _to_quote(instrument: Instrument, observations: list[Observation]) -> Quote:
    if len(observations) < 2:
        raise FetchFailed(instrument.symbol, f"only {len(observations)} observations")
    last, previous = observations[-1], observations[-2]
    month_target = last.day - timedelta(days=MONTH_LOOKBACK_DAYS)
    earlier = [observation for observation in observations if observation.day <= month_target]
    month_ago = earlier[-1] if earlier else observations[0]
    return Quote(
        symbol=instrument.symbol,
        name=instrument.name,
        group=instrument.group,
        unit=instrument.unit,
        blurb=instrument.blurb,
        last=last.value,
        previous=previous.value,
        month_ago=month_ago.value,
        as_of=last.day.isoformat(),
        provider=instrument.provider,
    )


def _fred_series(series_id: str, today: date) -> list[Observation]:
    start = today - timedelta(days=FRED_LOOKBACK_DAYS)
    url = FRED_CSV_URL.format(query=urlencode({"id": series_id, "cosd": start.isoformat()}))
    rows = _csv_rows(url)
    if len(rows[0]) != 2:
        raise FetchFailed(url, f"unexpected CSV header {rows[0]}")
    return _observations(url, ((day, value) for day, value in rows[1:] if value not in FRED_MISSING_VALUES))


def _stooq_series(symbol: str, today: date) -> list[Observation]:
    start = today - timedelta(days=STOOQ_LOOKBACK_DAYS)
    query = {"s": symbol, "i": "d", "d1": start.strftime("%Y%m%d"), "d2": today.strftime("%Y%m%d")}
    url = STOOQ_CSV_URL.format(query=urlencode(query))
    rows = _csv_rows(url)
    header = rows[0]
    if STOOQ_DATE_COLUMN not in header or STOOQ_CLOSE_COLUMN not in header:
        # An unknown symbol or an exhausted daily quota answers with one line of text.
        raise FetchFailed(url, f"no price data: {','.join(header)[:80]}")
    day_index, close_index = header.index(STOOQ_DATE_COLUMN), header.index(STOOQ_CLOSE_COLUMN)
    return _observations(url, ((row[day_index], row[close_index]) for row in rows[1:]))


def _csv_rows(url: str) -> list[list[str]]:
    rows = [row for row in csv.reader(io.StringIO(fetch_bytes(url).decode("utf-8"))) if row]
    if len(rows) < 2:
        raise FetchFailed(url, f"no data rows: {rows[:1]}")
    return rows


def _observations(url: str, pairs: Iterable[tuple[str, str]]) -> list[Observation]:
    try:
        return [Observation(day=date.fromisoformat(day), value=float(value)) for day, value in pairs]
    except ValueError as error:
        raise FetchFailed(url, f"unparseable row: {error}") from error


def _year_over_year(levels: list[Observation]) -> list[Observation]:
    """Percent change from the same month a year earlier (for monthly index series like CPI)."""
    by_month = {(observation.day.year, observation.day.month): observation.value for observation in levels}
    changes = []
    for observation in levels:
        base = by_month.get((observation.day.year - 1, observation.day.month))
        if base:
            changes.append(Observation(day=observation.day, value=(observation.value / base - 1.0) * _PERCENT))
    return changes
