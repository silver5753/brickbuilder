"""Strict JSON input validation."""

import pytest

from brickbuilder.jsonio import decode_json


@pytest.mark.parametrize(
    "value", ["NaN", "Infinity", "-Infinity"], ids=["NaN", "Infinity", "-Infinity"]
)
def test_strict_json_rejects_nonfinite_numbers(value):
    with pytest.raises(ValueError):
        decode_json('{"value":' + value + "}")
