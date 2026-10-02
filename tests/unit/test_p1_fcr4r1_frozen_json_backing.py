"""P1-FCR4R1 direct FrozenJSON backing-storage regression tests."""

from collections.abc import Callable, Iterator

import pytest
from tests.integration.test_p1_fcr4_ownership_matrix import (
    domain_factories,
    nested_json,
)

from researchbase.foundation.frozen_json import (
    FrozenJSONArray,
    FrozenJSONObject,
    freeze_json,
    thaw_json,
)

Attack = Callable[[object], None]


def _direct_backing_attacks(value: object) -> tuple[Attack, ...]:
    """Return attacks against every backing shape relevant to this value."""
    attacks: list[Attack] = []
    if isinstance(value, FrozenJSONObject):
        attacks.extend(
            (
                lambda item: item._values.__setitem__("nested", 2),  # type: ignore[attr-defined]
                lambda item: item._values.__delitem__("nested"),  # type: ignore[attr-defined]
                lambda item: item._values.clear(),  # type: ignore[attr-defined]
                lambda item: item._values.pop("nested"),  # type: ignore[attr-defined]
                lambda item: item._values.update({"nested": 2}),  # type: ignore[attr-defined]
                lambda item: item._values.setdefault("new", 3),  # type: ignore[attr-defined]
                lambda item: item._items.__setitem__(0, ("nested", 2)),  # type: ignore[attr-defined]
                lambda item: item._items.clear(),  # type: ignore[attr-defined]
            )
        )
    elif isinstance(value, FrozenJSONArray):
        attacks.extend(
            (
                lambda item: item._values.append(2),  # type: ignore[attr-defined]
                lambda item: item._values.extend((2,)),  # type: ignore[attr-defined]
                lambda item: item._values.clear(),  # type: ignore[attr-defined]
                lambda item: item._values.__setitem__(0, 2),  # type: ignore[attr-defined]
                lambda item: item._values.__delitem__(0),  # type: ignore[attr-defined]
            )
        )
    return tuple(attacks)


def _frozen_containers(value: object) -> Iterator[object]:
    if isinstance(value, FrozenJSONObject):
        yield value
        for child in value.values():
            yield from _frozen_containers(child)
    elif isinstance(value, FrozenJSONArray):
        yield value
        for child in value:
            yield from _frozen_containers(child)


def _attempt_without_material_change(value: object, attack: Attack) -> None:
    before = thaw_json(value)
    try:
        attack(value)
    except (AttributeError, IndexError, KeyError, TypeError):
        pass
    assert thaw_json(value) == before


def test_frozen_object_has_no_mutable_authoritative_backing_dict() -> None:
    value = freeze_json({"nested": {"x": 1}})

    assert isinstance(value, FrozenJSONObject)
    assert not hasattr(value, "_values")
    assert not hasattr(value, "_items")
    assert isinstance(value, tuple)
    assert all(isinstance(item, tuple) for item in tuple.__iter__(value))
    with pytest.raises(AttributeError):
        value._items = ()  # type: ignore[misc]
    with pytest.raises(AttributeError):
        object.__delattr__(value, "_items")
    for attack in _direct_backing_attacks(value):
        _attempt_without_material_change(value, attack)


def test_nested_object_backing_attacks_cannot_change_material() -> None:
    value = freeze_json({"a": {"b": [{"c": 1}]}})

    for container in _frozen_containers(value):
        for attack in _direct_backing_attacks(container):
            _attempt_without_material_change(container, attack)

    assert thaw_json(value) == {"a": {"b": [{"c": 1}]}}


def test_array_backing_attacks_cannot_change_material() -> None:
    value = freeze_json([{"x": 1}, 2])

    assert isinstance(value, FrozenJSONArray)
    assert isinstance(value, tuple)
    assert not hasattr(value, "_values")
    with pytest.raises(AttributeError):
        value._values = ()  # type: ignore[misc]
    with pytest.raises(AttributeError):
        object.__delattr__(value, "_values")
    for attack in _direct_backing_attacks(value):
        _attempt_without_material_change(value, attack)

    assert thaw_json(value) == [{"x": 1}, 2]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ({"nested": {"x": 1}}, {"nested": {"x": 1}}),
        ([{"nested": {"x": 1}}], [{"nested": {"x": 1}}]),
    ],
)
def test_direct_construction_owns_caller_containers(source: object, expected: object) -> None:
    value = freeze_json(source)
    if isinstance(source, dict):
        source["nested"] = {"x": 2}  # type: ignore[index]
    else:
        source[0]["nested"] = {"x": 2}  # type: ignore[index]

    assert thaw_json(value) == expected


def test_wrapper_constructors_own_direct_container_inputs() -> None:
    object_source = {"x": 1}
    array_source = [{"x": 1}]
    frozen_object = FrozenJSONObject((("payload", object_source),))
    frozen_array = FrozenJSONArray((array_source,))

    object_source["x"] = 2
    array_source[0]["x"] = 2

    assert thaw_json(frozen_object) == {"payload": {"x": 1}}
    assert thaw_json(frozen_array) == [[{"x": 1}]]


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


@pytest.mark.parametrize(
    ("owner_name", "field"),
    STRUCTURED_OWNER_FIELDS,
    ids=lambda value: value if isinstance(value, str) else repr(value),
)
def test_direct_backing_attacks_preserve_all_structured_owner_hashes(
    owner_name: str, field: str
) -> None:
    owner = domain_factories()[(owner_name, field)](nested_json())
    value = getattr(owner, field)
    before_material = thaw_json(value)
    before_hash = str(owner.content_hash)

    for container in _frozen_containers(value):
        for attack in _direct_backing_attacks(container):
            _attempt_without_material_change(value, attack)
            assert str(owner.content_hash) == before_hash

    assert thaw_json(value) == before_material
    assert str(owner.content_hash) == before_hash


def test_no_mutable_authoritative_container_exists_recursively() -> None:
    value = freeze_json({"a": {"b": [{"c": 1}]}})

    mutable_container_count = 0
    for container in _frozen_containers(value):
        if isinstance(container, FrozenJSONObject):
            assert isinstance(container, tuple)
            assert not hasattr(container, "_items")
            assert not hasattr(container, "_values")
        elif isinstance(container, FrozenJSONArray):
            assert isinstance(container, tuple)
            assert not hasattr(container, "_values")
        else:  # pragma: no cover - traversal yields only FrozenJSON containers
            mutable_container_count += 1

    assert mutable_container_count == 0
