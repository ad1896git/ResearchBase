"""P1-FCR4R2 intrinsic FrozenJSON immutability regression tests.

Threat boundary: ordinary Python-level operations, including
``object.__setattr__`` and ``object.__delattr__``, must not mutate authoritative
FrozenJSON material.  CPython memory corruption, ctypes, C extensions, debugger
memory patching, and direct process-memory modification are outside scope.
"""

from __future__ import annotations

from collections.abc import Iterator
from operator import setitem
from typing import Any, cast

import pytest

from researchbase.foundation.frozen_json import (
    FrozenJSONArray,
    FrozenJSONObject,
    freeze_json,
    thaw_json,
)
from researchbase.foundation.hashing import sha256_canonical_json
from tests.integration.test_p1_fcr4_ownership_matrix import domain_factories, nested_json


def _containers(value: object) -> Iterator[FrozenJSONObject | FrozenJSONArray]:
    if isinstance(value, FrozenJSONObject):
        yield value
        for child in value.values():
            yield from _containers(child)
    elif isinstance(value, FrozenJSONArray):
        yield value
        for child in value:
            yield from _containers(child)


def _reflective_attacks(value: FrozenJSONObject | FrozenJSONArray) -> None:
    for name in ("_items", "_values", "x"):
        try:
            object.__setattr__(value, name, ())
        except (AttributeError, TypeError):
            pass
        try:
            object.__delattr__(value, name)
        except (AttributeError, TypeError):
            pass


@pytest.mark.parametrize(
    ("source", "legacy_name"),
    [
        ({"nested": {"x": 1}}, "_items"),
        ([{"x": 1}], "_values"),
    ],
)
def test_canonical_payload_is_intrinsic_tuple_value(source: object, legacy_name: str) -> None:
    value = freeze_json(source)
    before = thaw_json(value)

    assert isinstance(value, tuple)
    assert type(value).__slots__ == ()
    assert not hasattr(value, "__dict__")
    assert not hasattr(value, legacy_name)
    with pytest.raises((AttributeError, TypeError)):
        object.__setattr__(value, legacy_name, ())
    with pytest.raises((AttributeError, TypeError)):
        object.__setattr__(value, "x", object())
    with pytest.raises((AttributeError, TypeError)):
        object.__delattr__(value, legacy_name)

    assert thaw_json(value) == before


def test_recursive_reflective_and_tuple_mutation_attacks_cannot_change_material() -> None:
    value = freeze_json({"a": {"b": [{"c": 1}]}})
    before = thaw_json(value)
    nodes = tuple(_containers(value))

    assert len(nodes) == 4
    for node in nodes:
        _reflective_attacks(node)
        with pytest.raises(TypeError):
            setitem(cast(Any, node), 0, None)

    assert thaw_json(value) == before
    assert all(not hasattr(node, "__dict__") for node in nodes)
    assert all(type(node).__slots__ == () for node in nodes)


STRUCTURED_OWNER_FIELDS = (
    ("ResearchQuestionVersion", "scope"),
    ("HypothesisVersion", "success_criteria"),
    ("ExperimentSpecVersion", "protocol"),
    ("DatasetSnapshot", "selection_definition"),
    ("MetricDefinitionVersion", "definition"),
    ("Measurement", "structured_value"),
    ("StatisticalResult", "result_payload"),
    ("ClaimVersion", "scope"),
    ("ImpactAssessment", "assessment_payload"),
    ("CorrectionRecord", "corrected_assertion"),
)


@pytest.mark.parametrize(("owner_name", "field"), STRUCTURED_OWNER_FIELDS)
def test_reflective_attacks_preserve_structured_owner_material_and_digest(
    owner_name: str, field: str
) -> None:
    owner = domain_factories()[(owner_name, field)](nested_json())
    value = getattr(owner, field)
    before_material = thaw_json(value)
    before_owner_hash = str(owner.content_hash)
    before_digest = sha256_canonical_json(before_material)

    nodes = tuple(_containers(value))
    for node in nodes:
        _reflective_attacks(node)

    assert thaw_json(value) == before_material
    assert str(owner.content_hash) == before_owner_hash
    assert sha256_canonical_json(thaw_json(value)) == before_digest


def test_mapping_sequence_and_semantic_equality_contracts_are_preserved() -> None:
    object_value = freeze_json({"b": 2, "a": [1, {"x": True}]})
    array_value = freeze_json([{"x": 1}, 2])

    assert isinstance(object_value, FrozenJSONObject)
    assert tuple(object_value) == ("b", "a")
    assert tuple(object_value.items()) == (("b", 2), ("a", [1, {"x": True}]))
    assert object_value == {"b": 2, "a": [1, {"x": True}]}
    assert isinstance(array_value, FrozenJSONArray)
    assert array_value[0] == {"x": 1}
    assert array_value == [{"x": 1}, 2]
