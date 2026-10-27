from __future__ import annotations

from dataclasses import dataclass

import pytest

from brief.config import Section
from brief.serde import SchemaError, from_jsonable, to_jsonable


@dataclass(frozen=True)
class Inner:
    name: str
    count: int


@dataclass(frozen=True)
class Outer:
    section: Section
    items: tuple[Inner, ...]
    ratio: float
    flag: bool


def test_round_trip() -> None:
    value = Outer(section=Section.NYC, items=(Inner("a", 1), Inner("b", 2)), ratio=0.5, flag=True)
    assert from_jsonable(Outer, to_jsonable(value)) == value


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"section": "mars", "items": [], "ratio": 0.5, "flag": True}, "$.section: expected one of"),
        ({"section": "us", "items": [{"name": "a", "count": True}], "ratio": 0.5, "flag": True}, "$.items[0].count: expected int"),
        ({"section": "us", "items": [], "ratio": 1, "flag": True}, "$.ratio: expected float"),
        ({"section": "us", "items": [], "ratio": 0.5}, "missing keys ['flag']"),
        ({"section": "us", "items": [], "ratio": 0.5, "flag": True, "extra": 1}, "unknown keys ['extra']"),
        ({"section": "us", "items": {}, "ratio": 0.5, "flag": True}, "$.items: expected a list"),
    ],
)
def test_rejects_bad_input(data: dict, message: str) -> None:
    with pytest.raises(SchemaError, match=message.replace("[", r"\[").replace("$", r"\$")):
        from_jsonable(Outer, data)
