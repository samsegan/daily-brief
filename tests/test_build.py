from __future__ import annotations

import json
from pathlib import Path

import pytest

from brief import build
from brief.config import InstrumentGroup, Lean, MarketProvider, Section, Unit
from brief.models import Cluster, IngestBundle, Quote
from brief.serde import write_json
from tests.factories import article, source

DATE = "2026-10-27"


def _bundle() -> IngestBundle:
    articles = (
        article("a1", "fox", "Senate passes funding bill"),
        article("a2", "nyt", "Senate ends shutdown"),
        article("a3", "wsj", "Shutdown ends"),
        article("op", "nyt", "Opinion | Shutdown lessons", is_opinion=True),
    )
    return IngestBundle(
        date=DATE,
        generated_at="2026-10-27T10:10:00Z",
        sources=(source("fox", Lean.RIGHT), source("nyt", Lean.LEAN_LEFT, paywalled=True), source("wsj", Lean.CENTER)),
        articles=articles,
        clusters=(Cluster("c001", Section.US, ("a1", "a2", "a3"), ("fox", "nyt", "wsj"), ("shutdown",)),),
        quotes=(
            Quote("^GSPC", "S&P 500", InstrumentGroup.US_STOCKS, Unit.POINTS, "", 6000.0, 5900.0, 5800.0, DATE, MarketProvider.FRED),
        ),
        trends=(),
        errors=(),
    )


def _story(**overrides: object) -> dict:
    story = {
        "id": "shutdown-ends",
        "headline": "Senate passes bill ending the shutdown",
        "region": "",
        "importance": 5,
        "summary": "The Senate passed a stopgap bill.",
        "why_it_matters": "Federal workers get paid again.",
        "background": "Funding lapsed on Oct 1.",
        "facts": [{"text": "The vote was 52-48.", "refs": ["a1", "a3"]}],
        "disputed": [],
        "framing": [{"ref": "a1", "note": "Calls it a win."}],
        "left_out": [{"text": "Back pay timing", "refs": ["a3"], "missing_from": ["fox"]}],
        "coverage": [{"ref": "a1", "takeaway": "Focus on the vote.", "read_full": True}],
        "social": "",
    }
    return story | overrides


def _write_draft(root: Path, us_stories: list[dict], web_refs: list[dict]) -> None:
    drafts = root / "drafts" / DATE
    drafts.mkdir(parents=True)
    front = {
        "overview": "A quiet day.",
        "markets": {"summary": "Stocks rose.", "movers": [{"symbol": "^GSPC", "why": "Rally."}],
                    "concept": {"term": "Index", "explanation": "A basket."}, "watch": []},
        "trending": [],
    }
    (drafts / "front.json").write_text(json.dumps(front))
    for section in Section:
        stories = us_stories if section is Section.US else []
        refs = web_refs if section is Section.US else []
        (drafts / f"{section}.json").write_text(json.dumps({"stories": stories, "web_refs": refs}))


@pytest.fixture
def paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(build, "INGEST_DIR", tmp_path / "ingest")
    monkeypatch.setattr(build, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(build, "BRIEFS_DIR", tmp_path / "site" / "briefs")
    monkeypatch.setattr(build, "SITE_INDEX_PATH", tmp_path / "site" / "index.json")
    write_json(_bundle(), tmp_path / "ingest" / f"{DATE}.json", pretty=False)
    return tmp_path


def test_publishes_resolved_brief(paths: Path) -> None:
    web = [{"id": "us-w1", "url": "https://x.com/post", "title": "A post", "outlet": "X"}]
    _write_draft(paths, [_story(facts=[{"text": "The vote was 52-48.", "refs": ["a1", "a3", "us-w1"]}])], web)
    brief = json.loads(build.build(DATE).read_text())
    (story,) = brief["sections"][0]["stories"]
    assert story["facts"][0]["outlet_count"] == 3
    assert [ref["id"] for ref in story["refs"]] == ["a3", "a1", "us-w1"]
    fox = next(ref for ref in story["refs"] if ref["id"] == "a1")
    assert (fox["outlet"], fox["lean"], fox["read_full"], fox["takeaway"]) == ("FOX", "right", True, "Focus on the vote.")
    assert story["lean_counts"] == {"left": 0, "center": 1, "right": 1, "unrated": 1}
    assert story["left_out"][0]["missing_from"] == ["FOX"]
    assert brief["markets"]["movers"][0]["name"] == "S&P 500"
    assert json.loads((paths / "site" / "index.json").read_text()) == {"latest": DATE, "dates": [DATE]}


def test_reports_every_problem(paths: Path) -> None:
    bad = _story(
        importance=9,
        facts=[{"text": "x", "refs": ["nope"]}, {"text": "y", "refs": ["op"]}],
        left_out=[{"text": "z", "refs": [], "missing_from": ["cnn"]}],
    )
    _write_draft(paths, [bad, _story()], [])
    with pytest.raises(build.BuildError) as raised:
        build.build(DATE)
    message = str(raised.value)
    for expected in ("importance 9", "unknown ref 'nope'", "opinion pieces ['op']", "missing_from", "used 2 times"):
        assert expected in message


def test_check_validates_one_section(paths: Path) -> None:
    _write_draft(paths, [_story(facts=[{"text": "x", "refs": ["nope"]}])], [])
    with pytest.raises(build.BuildError, match="unknown ref 'nope'"):
        build.check_section(DATE, Section.US)
    build.check_section(DATE, Section.WORLD)
