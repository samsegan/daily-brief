"""Strict JSON <-> frozen dataclass conversion.

Decoding rejects unknown keys, missing keys and wrong types instead of coercing,
so a typo in a hand- or model-written draft fails loudly with its JSON path.
"""

from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from enum import Enum
from functools import cache
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

_SCALARS = (str, int, float, bool)


class SchemaError(ValueError):
    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"{path}: {reason}")


def to_jsonable(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: to_jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple | list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    return value


def from_jsonable[T](cls: type[T], data: object, path: str = "$") -> T:
    return _decode(cls, data, path)


def load_json[T](cls: type[T], path: Path) -> T:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return from_jsonable(cls, data, path.name)


def write_json(value: object, path: Path, pretty: bool) -> None:
    """Pretty output for files people diff (briefs); compact for bulk data (ingest bundles)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = to_jsonable(value)
    if pretty:
        text = json.dumps(data, ensure_ascii=False, indent=1)
    else:
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text + "\n", encoding="utf-8")


@cache
def _hints(cls: type) -> dict[str, Any]:
    return get_type_hints(cls)


def _decode(hint: Any, data: object, path: str) -> Any:
    origin = get_origin(hint)
    if origin is tuple:
        if not isinstance(data, list):
            raise SchemaError(path, "expected a list")
        item_hint = get_args(hint)[0]
        return tuple(_decode(item_hint, item, f"{path}[{index}]") for index, item in enumerate(data))
    if isinstance(hint, type) and is_dataclass(hint):
        return _decode_dataclass(hint, data, path)
    if isinstance(hint, type) and issubclass(hint, Enum):
        allowed = [member.value for member in hint]
        if data not in allowed:
            raise SchemaError(path, f"expected one of {allowed}, got {data!r}")
        return hint(data)
    if hint in _SCALARS:
        # bool is an int subclass; never let true/false stand in for a number.
        if not isinstance(data, hint) or (hint is not bool and isinstance(data, bool)):
            raise SchemaError(path, f"expected {hint.__name__}, got {type(data).__name__}")
        return data
    raise TypeError(f"unsupported type hint {hint!r} at {path}")


def _decode_dataclass(cls: type, data: object, path: str) -> Any:
    if not isinstance(data, dict):
        raise SchemaError(path, "expected an object")
    hints = _hints(cls)
    names = [field.name for field in fields(cls)]
    unknown = sorted(set(data) - set(names))
    missing = [name for name in names if name not in data]
    if unknown:
        raise SchemaError(path, f"unknown keys {unknown}")
    if missing:
        raise SchemaError(path, f"missing keys {missing}")
    return cls(**{name: _decode(hints[name], data[name], f"{path}.{name}") for name in names})
