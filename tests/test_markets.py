from __future__ import annotations

from datetime import date

import pytest

from brief import markets
from brief.config import InstrumentGroup, MarketProvider, Transform, Unit
from brief.http import FetchFailed
from brief.models import Instrument

TODAY = date(2026, 10, 27)
FRED_CPI = "observation_date,CPIAUCSL\n2025-08-01,300.0\n2025-09-01,301.0\n2026-08-01,309.0\n2026-09-01,310.03\n"
FRED_WITH_GAPS = "observation_date,DGS10\n2026-09-25,4.05\n2026-10-13,\n2026-10-23,4.18\n2026-10-24,.\n2026-10-26,4.21\n"


def _instrument(provider: MarketProvider, transform: Transform) -> Instrument:
    return Instrument(
        symbol="X", name="X", group=InstrumentGroup.US_STOCKS, unit=Unit.POINTS, provider=provider,
        transform=transform, blurb="",
    )


def _serve(monkeypatch: pytest.MonkeyPatch, body: str) -> None:
    monkeypatch.setattr(markets, "fetch_bytes", lambda url: body.encode())


def test_fred_skips_missing_days(monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(monkeypatch, FRED_WITH_GAPS)
    quote = markets.fetch_quote(_instrument(MarketProvider.FRED, Transform.LEVEL), TODAY)
    assert (quote.last, quote.previous, quote.month_ago, quote.as_of) == (4.21, 4.18, 4.05, "2026-10-26")


def test_fred_year_over_year(monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(monkeypatch, FRED_CPI)
    quote = markets.fetch_quote(_instrument(MarketProvider.FRED, Transform.YOY_PERCENT), TODAY)
    assert quote.last == pytest.approx(3.0)
    assert quote.previous == pytest.approx(3.0)
    assert quote.as_of == "2026-09-01"


def test_fred_empty_series(monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(monkeypatch, "observation_date,DGS10\n")
    with pytest.raises(FetchFailed, match="no data rows"):
        markets.fetch_quote(_instrument(MarketProvider.FRED, Transform.LEVEL), TODAY)
