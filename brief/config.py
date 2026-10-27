"""Paths, tunables and the enums shared across the pipeline."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"
SOURCES_PATH = CONFIG_DIR / "sources.toml"
MARKETS_PATH = CONFIG_DIR / "markets.toml"
INGEST_DIR = REPO_ROOT / "data" / "ingest"
DRAFTS_DIR = REPO_ROOT / "data" / "drafts"
SITE_DATA_DIR = REPO_ROOT / "docs" / "data"
BRIEFS_DIR = SITE_DATA_DIR / "briefs"
SITE_INDEX_PATH = SITE_DATA_DIR / "index.json"

HOME_TZ = ZoneInfo("America/New_York")

# Ingest
ARTICLE_WINDOW_HOURS = 36
MAX_SUMMARY_CHARS = 300
HTTP_TIMEOUT_SECONDS = 20
HTTP_WORKERS = 16
MAX_RESPONSE_BYTES = 10 * 1024 * 1024
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36 daily-brief/0.1 (+https://github.com/samsegan/daily-brief)"
)
OPINION_URL_MARKERS = ("/opinion", "/opinions/", "/commentary/", "/editorial", "/op-ed", "/columnists/")
OPINION_TITLE_PREFIXES = ("opinion", "op-ed", "editorial")

# Clustering
CLUSTER_SIMILARITY_THRESHOLD = 0.30
CLUSTER_INDEX_TERMS = 12
CLUSTER_TOP_TERMS = 6
TITLE_WEIGHT = 2

# Markets
FRED_LOOKBACK_DAYS = 450
MONTH_LOOKBACK_DAYS = 30

# Trends
GOOGLE_TRENDS_GEO = "US"
WIKIPEDIA_MOST_READ_LIMIT = 15
BLUESKY_TRENDS_LIMIT = 15

# Digest
DIGEST_MAX_CLUSTERS = 40
DIGEST_MAX_SINGLETONS = 40
DIGEST_ARTICLES_PER_CLUSTER = 10


class Section(StrEnum):
    US = "us"
    WORLD = "world"
    BUSINESS = "business"
    NYC = "nyc"


SECTION_TITLES = {
    Section.US: "United States",
    Section.WORLD: "World",
    Section.BUSINESS: "Business & Markets",
    Section.NYC: "New York City",
}


class Lean(StrEnum):
    LEFT = "left"
    LEAN_LEFT = "lean_left"
    CENTER = "center"
    LEAN_RIGHT = "lean_right"
    RIGHT = "right"
    UNRATED = "unrated"


class LeanBucket(StrEnum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    UNRATED = "unrated"


LEAN_BUCKETS = {
    Lean.LEFT: LeanBucket.LEFT,
    Lean.LEAN_LEFT: LeanBucket.LEFT,
    Lean.CENTER: LeanBucket.CENTER,
    Lean.LEAN_RIGHT: LeanBucket.RIGHT,
    Lean.RIGHT: LeanBucket.RIGHT,
    Lean.UNRATED: LeanBucket.UNRATED,
}

LEAN_ORDER = tuple(Lean)


class FeedKind(StrEnum):
    RSS = "rss"
    # Google News search feeds stand in for outlets without RSS (AP, Reuters):
    # titles carry an " - Outlet" suffix and summaries are just a link.
    GOOGLE_NEWS = "google_news"


class InstrumentGroup(StrEnum):
    US_STOCKS = "us_stocks"
    WORLD_STOCKS = "world_stocks"
    RATES = "rates"
    ECONOMY = "economy"
    COMMODITIES = "commodities"
    CURRENCIES = "currencies"
    CRYPTO = "crypto"


class Unit(StrEnum):
    POINTS = "points"
    USD = "usd"
    PERCENT = "percent"
    FX_RATE = "fx_rate"


class MarketProvider(StrEnum):
    FRED = "fred"


class Transform(StrEnum):
    LEVEL = "level"
    YOY_PERCENT = "yoy_percent"


class TrendSignal(StrEnum):
    GOOGLE = "google"
    WIKIPEDIA = "wikipedia"
    WIKIPEDIA_NEWS = "wikipedia_news"
    BLUESKY = "bluesky"
    WEB = "web"


class RefKind(StrEnum):
    ARTICLE = "article"
    WEB = "web"
