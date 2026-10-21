"""Normalize failures only after a saved formal root has been resolved."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

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


# Scoped to exact immutable event readback; ordinary B04/B05 readers retain CAS checks.
_SAVED_SEAL = ContextVar("publication_entry_saved_seal", default=False)


def reading_saved_seal() -> bool:
    return _SAVED_SEAL.get()


@contextmanager
def saved_seal() -> Iterator[None]:
    """Verify retained hashes/graph without readmitting bytes or live projections."""
    token = _SAVED_SEAL.set(True)
    try:
        with saved_dependency(ownership=True):
            yield
    finally:
        _SAVED_SEAL.reset(token)
