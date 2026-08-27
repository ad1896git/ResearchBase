import math

import pytest

from researchbase.foundation.canonical_json import canonical_json_bytes, canonical_json_text


def test_key_order_does_not_change_canonical_bytes() -> None:
    left = {"z": 1, "nested": {"b": 2, "a": [True, None, "文本"]}}
    right = {"nested": {"a": [True, None, "文本"], "b": 2}, "z": 1}

    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert canonical_json_text(left) == '{"nested":{"a":[true,null,"文本"],"b":2},"z":1}'


def test_canonical_json_is_utf8_compact_and_deterministic() -> None:
    encoded = canonical_json_bytes({"message": "é", "number": 1.5})

    assert encoded == b'{"message":"\xc3\xa9","number":1.5}'
    assert b" " not in encoded


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_numbers_are_rejected(value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        canonical_json_bytes(value)


@pytest.mark.parametrize("value", [(1, 2), object(), {1: "non-string key"}])
def test_unsupported_values_are_rejected(value: object) -> None:
    with pytest.raises(TypeError, match="supported JSON subset"):
        canonical_json_bytes(value)
