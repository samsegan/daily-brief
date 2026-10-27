"""Market and economic numbers: Yahoo Finance charts for prices, FRED for rates and macro."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from urllib.parse import quote, urlencode
from zoneinfo import ZoneInfo

from brief.config import (
    FRED_LOOKBACK_DAYS,
    MONTH_LOOKBACK_DAYS,
    YAHOO_CHART_RANGE,
    MarketProvider,
    Transform,
)
from brief.http import FetchFailed, fetch_bytes, fetch_json
from brief.models import Instrument, Quote

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?{query}"
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?{query}"
FRED_MISSING_VALUE = "."
_PERCENT = 100.0


@dataclass(frozen=True)
class Observation:
    day: date
    value: float


def fetch_quote(instrument: Instrument, today: date) -> Quote:
    match instrument.provider:
        case MarketProvider.YAHOO:
            if instrument.transform is not Transform.LEVEL:
                raise ValueError(f"{instrument.symbol}: Yahoo instruments only support the level transform")
            observations = _yahoo_series(instrument.symbol)
        case MarketProvider.FRED:
            observations = _fred_series(instrument.symbol, today, instrument.transform)
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


def _yahoo_series(symbol: str) -> list[Observation]:
    url = YAHOO_CHART_URL.format(symbol=quote(symbol, safe=""), query=urlencode({"range": YAHOO_CHART_RANGE, "interval": "1d"}))
    payload = fetch_json(url)
    try:
        result = payload["chart"]["result"][0]
        zone = ZoneInfo(result["meta"]["exchangeTimezoneName"])
        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
        return [
            Observation(day=datetime.fromtimestamp(stamp, tz=zone).date(), value=float(close))
            for stamp, close in zip(timestamps, closes, strict=True)
            if close is not None
        ]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise FetchFailed(url, f"unexpected chart response: {error!r}") from error


def _fred_series(series_id: str, today: date, transform: Transform) -> list[Observation]:
    start = today - timedelta(days=FRED_LOOKBACK_DAYS)
    url = FRED_CSV_URL.format(query=urlencode({"id": series_id, "cosd": start.isoformat()}))
    rows = list(csv.reader(io.StringIO(fetch_bytes(url).decode("utf-8"))))
    if len(rows) < 2 or len(rows[0]) != 2:
        raise FetchFailed(url, f"unexpected CSV header {rows[:1]}")
    try:
        levels = [
            Observation(day=date.fromisoformat(day), value=float(value))
            for day, value in rows[1:]
            if value != FRED_MISSING_VALUE
        ]
    except ValueError as error:
        raise FetchFailed(url, f"unparseable row: {error}") from error
    match transform:
        case Transform.LEVEL:
            return levels
        case Transform.YOY_PERCENT:
            return _year_over_year(levels)


def _year_over_year(levels: list[Observation]) -> list[Observation]:
    """Percent change from the same month a year earlier (for monthly index series like CPI)."""
    by_month = {(observation.day.year, observation.day.month): observation.value for observation in levels}
    changes = []
    for observation in levels:
        base = by_month.get((observation.day.year - 1, observation.day.month))
        if base:
            changes.append(Observation(day=observation.day, value=(observation.value / base - 1.0) * _PERCENT))
    return changes
