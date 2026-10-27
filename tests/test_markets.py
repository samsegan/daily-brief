from __future__ import annotations

import json
from datetime import date

import pytest

from brief import markets
from brief.config import InstrumentGroup, MarketProvider, Transform, Unit
from brief.models import Instrument

YAHOO = {
    "chart": {
        "result": [
            {
                "meta": {"exchangeTimezoneName": "America/New_York"},
                "timestamp": [1758000000, 1759900000, 1761400000, 1761500000],
                "indicators": {"quote": [{"close": [100.0, 104.0, None, 110.0]}]},
            }
        ],
        "error": None,
    }
}

FRED_CPI = "observation_date,CPIAUCSL\n2025-08-01,300.0\n2025-09-01,301.0\n2026-08-01,309.0\n2026-09-01,310.03\n"


def _instrument(provider: MarketProvider, transform: Transform) -> Instrument:
    return Instrument(
        symbol="X", name="X", group=InstrumentGroup.US_STOCKS, unit=Unit.POINTS, provider=provider,
        transform=transform, blurb="",
    )


def test_yahoo_quote(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(markets, "fetch_json", lambda url: json.loads(json.dumps(YAHOO)))
    quote = markets.fetch_quote(_instrument(MarketProvider.YAHOO, Transform.LEVEL), date(2026, 10, 27))
    assert (quote.last, quote.previous, quote.month_ago) == (110.0, 104.0, 100.0)
    assert quote.as_of == "2025-10-26"


def test_fred_year_over_year(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(markets, "fetch_bytes", lambda url: FRED_CPI.encode())
    quote = markets.fetch_quote(_instrument(MarketProvider.FRED, Transform.YOY_PERCENT), date(2026, 10, 27))
    assert quote.last == pytest.approx(3.0)
    assert quote.previous == pytest.approx(3.0)
    assert quote.as_of == "2026-09-01"
