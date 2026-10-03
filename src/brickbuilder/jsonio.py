"""Small strict JSON boundary shared by configuration and native metadata."""

import json
from math import isfinite
from .transforms import Vector, vector
from pathlib import Path
from typing import Any


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def _nonfinite(name: str) -> None:
    raise ValueError(f"Non-finite JSON number: {name}")


def decode_json(text: str) -> Any:
    return json.loads(text, object_pairs_hook=_unique_object, parse_constant=_nonfinite)


def read_json(path: Path) -> Any:
    return decode_json(path.read_text(encoding="utf-8-sig"))


def object_fields(value: Any, fields: set[str], context: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(
            f"Invalid {context} fields; expected {', '.join(sorted(fields))}"
        )
    return value


def versioned(value: Any, fields: set[str], context: str) -> dict[str, Any]:
    data = object_fields(value, fields | {"schema_version"}, context)
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError(f"Unsupported {context} schema version")
    return data


def array(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{context} must be an array")
    return value


def text(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be a nonempty string")
    return value


def number(value: object, context: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (float, int))
        or not isfinite(value)
    ):
        raise ValueError(f"{context} must be finite")
    return float(value)


def coordinates(value: object, context: str) -> Vector:
    values = array(value, context)
    return vector(number(v, context) for v in values)
