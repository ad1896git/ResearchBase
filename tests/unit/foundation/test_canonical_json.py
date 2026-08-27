import math

import pytest

from researchbase.foundation.canonical_json import (
    CANONICAL_JSON_SCHEME,
    canonical_json_bytes,
    canonical_json_text,
)
from researchbase.foundation.hashing import CANONICAL_JSON_HASH_SCHEME, sha256_canonical_json


def test_key_order_does_not_change_canonical_bytes() -> None:
    left = {"z": 1, "nested": {"b": 2, "a": [True, None, "文本"]}}
    right = {"nested": {"a": [True, None, "文本"], "b": 2}, "z": 1}

    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert canonical_json_text(left) == '{"nested":{"a":[true,null,"文本"],"b":2},"z":1}'


def test_canonical_json_is_utf8_compact_and_deterministic() -> None:
    encoded = canonical_json_bytes({"message": "é", "number": 1.5})

    assert encoded == b'{"message":"\xc3\xa9","number":1.5}'
    assert b" " not in encoded


def test_canonical_json_scheme_identifier_is_stable() -> None:
    assert CANONICAL_JSON_SCHEME == "canonical-json-v1"
    assert CANONICAL_JSON_HASH_SCHEME == "sha256-cjson-v1"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ({"b": 2, "a": [True, None, "文本"]}, '{"a":[true,null,"文本"],"b":2}'),
        ({"text": "é"}, '{"text":"é"}'),
        ({"number": 1}, '{"number":1}'),
        ({"number": 1.0}, '{"number":1.0}'),
        ({"number": -0.0}, '{"number":-0.0}'),
    ],
)
def test_canonical_json_v1_golden_vectors_freeze_supported_semantics(
    value: object, expected: str
) -> None:
    assert canonical_json_text(value) == expected


def test_sha256_cjson_v1_golden_vector_is_stable() -> None:
    assert (
        sha256_canonical_json({"a": 1, "b": 2})
        == "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"
    )


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_numbers_are_rejected(value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        canonical_json_bytes(value)


@pytest.mark.parametrize("value", [(1, 2), object(), {1: "non-string key"}])
def test_unsupported_values_are_rejected(value: object) -> None:
    with pytest.raises(TypeError, match="supported JSON subset"):
        canonical_json_bytes(value)
