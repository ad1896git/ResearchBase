"""Normalize failures only after a saved formal root has been resolved."""

from collections.abc import Iterator
from contextlib import contextmanager

from researchbase.foundation.errors import ErrorCode, ResearchBaseError

MESSAGE = "saved formal provenance is unresolved"
_SAVED_FAILURES = frozenset(
    {
        ErrorCode.NOT_FOUND,
        ErrorCode.FROZEN_REFERENCE_REQUIRED,
        ErrorCode.VERSION_NOT_FROZEN,
        ErrorCode.INVALID_SOURCE_VERSION_LINEAGE,
        ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
    }
)


@contextmanager
def saved_dependency(*, ownership: bool = False) -> Iterator[None]:
    """Do not translate authentication, infrastructure or programming failures."""
    try:
        yield
    except ResearchBaseError as error:
        if error.code not in _SAVED_FAILURES and not (
            ownership and error.code is ErrorCode.FORBIDDEN
        ):
            raise
        raise ResearchBaseError(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, MESSAGE) from None
