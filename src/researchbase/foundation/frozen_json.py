# pyright: reportAssignmentType=false

"""Recursively owned immutable values for the canonical JSON subset."""

from __future__ import annotations

import math
from collections.abc import Iterator, Mapping, Sequence
from typing import Any

type JSONScalar = None | bool | int | float | str


class FrozenJSONObject(Mapping[str, object]):
    """An immutable, insertion-order-preserving JSON object snapshot."""

    __slots__ = ("_items",)
    __hash__: Any = None

    def __setattr__(self, name: str, value: object) -> None:
        if hasattr(self, name):
            raise AttributeError("FrozenJSONObject is immutable")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        raise AttributeError("FrozenJSONObject is immutable")

    def __init__(self, items: tuple[tuple[str, object], ...]) -> None:
        owned_items: list[tuple[str, FrozenJSON]] = []
        for key, value in items:
            if not isinstance(key, str):
                raise TypeError("canonical JSON object keys must be strings")
            owned_items.append((key, _own_json(value)))
        self._items = tuple(owned_items)

    def __getitem__(self, key: str) -> object:
        for item_key, item_value in self._items:
            if item_key == key:
                return item_value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (key for key, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Mapping):
            return False
        return thaw_json(self) == thaw_json(other)

    def __repr__(self) -> str:
        return f"FrozenJSONObject({thaw_json(self)!r})"


class FrozenJSONArray(Sequence[object]):
    """An immutable ordered JSON array snapshot."""

    __slots__ = ("_values",)
    __hash__ = None

    def __setattr__(self, name: str, value: object) -> None:
        if hasattr(self, name):
            raise AttributeError("FrozenJSONArray is immutable")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        raise AttributeError("FrozenJSONArray is immutable")

    def __init__(self, values: tuple[object, ...]) -> None:
        self._values = tuple(_own_json(value) for value in values)

    def __getitem__(self, index: int | slice) -> object:
        return self._values[index]

    def __len__(self) -> int:
        return len(self._values)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str | bytes | bytearray) or not isinstance(other, Sequence):
            return False
        return thaw_json(self) == thaw_json(other)

    def __repr__(self) -> str:
        return f"FrozenJSONArray({thaw_json(self)!r})"


type FrozenJSON = JSONScalar | FrozenJSONObject | FrozenJSONArray


def _own_json(value: object) -> FrozenJSON:
    """Return a recursively owned JSON value without copying owned wrappers."""
    if isinstance(value, FrozenJSONObject | FrozenJSONArray):
        return value
    return freeze_json(value)


def freeze_json(value: object) -> FrozenJSON:
    """Validate and recursively snapshot one canonical JSON value."""
    if value is None or isinstance(value, bool | str):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical JSON numbers must be finite")
        return value
    if isinstance(value, Mapping):
        items: list[tuple[str, FrozenJSON]] = []
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical JSON object keys must be strings")
            items.append((key, freeze_json(item)))
        return FrozenJSONObject(tuple(items))
    if isinstance(value, list | FrozenJSONArray):
        return FrozenJSONArray(tuple(freeze_json(item) for item in value))
    if isinstance(value, tuple | set | frozenset):
        raise TypeError("tuples and sets are outside the canonical JSON subset")
    raise TypeError("value is outside the canonical JSON subset")


def thaw_json(value: object) -> object:
    """Return a fresh plain-dict/list canonical JSON tree."""
    if isinstance(value, Mapping):
        return {key: thaw_json(item) for key, item in value.items()}
    if isinstance(value, FrozenJSONArray | list):
        return [thaw_json(item) for item in value]
    if value is None or isinstance(value, bool | int | float | str):
        return value
    raise TypeError("value is outside the canonical JSON subset")
