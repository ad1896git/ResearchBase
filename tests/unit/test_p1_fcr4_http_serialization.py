from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import pytest
from pydantic import BaseModel

from researchbase.api.routes import _json
from researchbase.foundation.frozen_json import (
    FrozenJSONArray,
    FrozenJSONObject,
    freeze_json,
    thaw_json,
)

DEEP_VALUE = {
    "outer": {
        "items": [
            1,
            {"inner": [True, None, {"value": "ResearchBase"}]},
        ]
    }
}


@dataclass(frozen=True, slots=True)
class FrozenDataclass:
    payload: object


class FrozenModel(BaseModel):
    payload: Any


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        (None, None),
        (True, True),
        (7, 7),
        (1.25, 1.25),
        ("ResearchBase", "ResearchBase"),
        ({"plain": [1, {"nested": "value"}]}, {"plain": [1, {"nested": "value"}]}),
        ([1, {"nested": [2]}], [1, {"nested": [2]}]),
        (freeze_json(DEEP_VALUE), DEEP_VALUE),
        (freeze_json(DEEP_VALUE["outer"]["items"]), DEEP_VALUE["outer"]["items"]),
        ({"wrapped": freeze_json(DEEP_VALUE)}, {"wrapped": DEEP_VALUE}),
        ([freeze_json(DEEP_VALUE)], [DEEP_VALUE]),
        (FrozenDataclass(freeze_json(DEEP_VALUE)), {"payload": DEEP_VALUE}),
        (FrozenModel(payload=freeze_json(DEEP_VALUE)), {"payload": DEEP_VALUE}),
    ),
    ids=(
        "null",
        "bool",
        "integer",
        "finite-float",
        "string",
        "plain-dict",
        "plain-list",
        "frozen-object",
        "frozen-array",
        "frozen-in-dict",
        "frozen-in-list",
        "dataclass-with-frozen",
        "pydantic-with-frozen",
    ),
)
def test_http_serializer_matrix_returns_plain_json(value: object, expected: object) -> None:
    assert _json(value) == expected


def test_http_serialization_does_not_mutate_frozen_source() -> None:
    source = freeze_json(DEEP_VALUE)
    before = thaw_json(source)

    first = _json(source)
    second = _json(source)

    assert first == DEEP_VALUE
    assert second == DEEP_VALUE
    assert thaw_json(source) == before
    assert isinstance(source, FrozenJSONObject)
    outer = cast(FrozenJSONObject, source["outer"])
    assert isinstance(outer, FrozenJSONObject)
    assert isinstance(outer["items"], FrozenJSONArray)
