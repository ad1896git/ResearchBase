from __future__ import annotations

from uuid import uuid4

import pytest

from researchbase.application.closure import BatchLookup, BatchLookupState


def test_batch_lookup_distinguishes_found_missing_and_never_requested() -> None:
    found_id = uuid4()
    missing_id = uuid4()
    never_requested_id = uuid4()
    found_value = object()
    lookup = BatchLookup(
        values={found_id: found_value},
        requested_ids=frozenset({found_id, missing_id}),
    )

    assert lookup.resolve(found_id) == (BatchLookupState.FOUND, found_value)
    assert lookup.resolve(missing_id) == (BatchLookupState.MISSING, None)
    assert lookup.resolve(never_requested_id) == (BatchLookupState.NEVER_REQUESTED, None)
    assert lookup.missing_ids == frozenset({missing_id})


def test_batch_lookup_rejects_values_not_declared_as_requested() -> None:
    undeclared_id = uuid4()

    with pytest.raises(ValueError, match="values must be a subset of requested_ids"):
        BatchLookup(values={undeclared_id: object()}, requested_ids=frozenset())
