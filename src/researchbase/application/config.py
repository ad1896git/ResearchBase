"""Shared Pydantic configuration for public Application boundary records."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast, dataclass_transform

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass as pydantic_dataclass
from pydantic_core import ValidationError

from researchbase.foundation.errors import ErrorCode, ResearchBaseError

APPLICATION_DTO_CONFIG = ConfigDict(
    extra="forbid",
    frozen=True,
    from_attributes=False,
    arbitrary_types_allowed=False,
    use_enum_values=False,
    strict=False,
)


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
        except ValidationError as exc:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "invalid Application request",
            ) from exc

    decorated.__init__ = normalized_init  # type: ignore[method-assign]
    return cast(type[RecordT], decorated)
