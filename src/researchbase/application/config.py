"""Shared Pydantic configuration for public Application boundary records."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import fields
from typing import Any, cast, dataclass_transform

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass as pydantic_dataclass
from pydantic_core import ValidationError

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.frozen_json import FrozenJSONArray, FrozenJSONObject, thaw_json

APPLICATION_DTO_CONFIG = ConfigDict(
    extra="forbid",
    frozen=True,
    from_attributes=False,
    arbitrary_types_allowed=False,
    use_enum_values=False,
    strict=False,
)


def _snapshot_public_value(value: Any) -> Any:
    if isinstance(value, FrozenJSONObject | FrozenJSONArray):
        return thaw_json(value)
    if isinstance(value, dict | list):
        return deepcopy(value)
    return value


@dataclass_transform()
def application_dto_dataclass[RecordT](record: type[RecordT]) -> type[RecordT]:
    """Decorate one public Application record with the shared contract config."""

    decorated = pydantic_dataclass(
        record,
        config=APPLICATION_DTO_CONFIG,
        slots=True,
    )

    original_init = cast(Callable[..., None], decorated.__init__)

    def normalized_init(self: Any, *args: Any, **kwargs: Any) -> None:
        try:
            original_init(self, *args, **kwargs)
            for field in fields(self):
                object.__setattr__(
                    self,
                    field.name,
                    _snapshot_public_value(getattr(self, field.name)),
                )
        except ValidationError as exc:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "invalid Application request",
            ) from exc

    decorated.__init__ = normalized_init  # type: ignore[method-assign]
    return cast(type[RecordT], decorated)
