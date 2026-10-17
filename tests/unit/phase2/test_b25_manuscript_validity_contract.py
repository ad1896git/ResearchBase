"""Closed B25 DTOs, conservative state mapping and complete response bounds."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from itertools import permutations
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest

from researchbase.application.governance_queries import ValidityProjection, ValidityState
from researchbase.application.internal_review import verify_open_issue_history
from researchbase.application.manuscript_validity import (
    AuditNodeRef,
    AuditOccurrence,
    GetManuscriptAuditQuery,
    GetManuscriptValidityQuery,
    ManuscriptValidityReadback,
    ManuscriptValidityService,
    UnsupportedAssertionConcern,
    _bounded,
    _Collector,
    _path_key,
)
from researchbase.domain.governance import GovernanceTargetType
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def _unused_uow() -> Any:
    raise AssertionError("unit traversal must not open UoW")


@pytest.mark.parametrize("query", [GetManuscriptValidityQuery, GetManuscriptAuditQuery])
@pytest.mark.parametrize("field", ["project_id", "publication_id", "manuscript_version_id"])
@pytest.mark.parametrize("invalid", [None, "uuid", True, 1, {}, ()])
def test_query_exact_uuid(query, field, invalid):
    args: dict[str, Any] = dict(
        project_id=uuid4(), publication_id=uuid4(), manuscript_version_id=uuid4()
    )
    args[field] = invalid
    with pytest.raises(ResearchBaseError) as error:
        query(**args)
    assert error.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("extra", ["actor_id", "status", "limit", "evaluated_at", "content_hash"])
@pytest.mark.parametrize("query", [GetManuscriptValidityQuery, GetManuscriptAuditQuery])
def test_query_closed_and_frozen(query, extra):
    ids = [uuid4() for _ in range(3)]
    with pytest.raises(ResearchBaseError):
        query(*ids, **{extra: None})
    value = query(*ids)
    with pytest.raises(FrozenInstanceError):
        value.project_id = uuid4()


@pytest.mark.parametrize("method", ["get_manuscript_validity", "get_manuscript_audit"])
@pytest.mark.parametrize("wrong", [None, {}, (), SimpleNamespace()])
def test_wrong_query_before_uow(method, wrong):
    def forbidden_factory():
        pytest.fail("invalid query opened UoW")

    service = ManuscriptValidityService(forbidden_factory, None, None)
    with pytest.raises(ResearchBaseError) as error:
        getattr(service, method)(None, wrong)
    assert error.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("state", list(ValidityState))
@pytest.mark.parametrize("corrected", [False, True])
def test_governance_mapping_preserves_original_ids(state, corrected, monkeypatch):
    collector = _Collector(_unused_uow, None, None, uuid4())
    identity, correction = uuid4(), uuid4()
    projection = ValidityProjection(
        GovernanceTargetType.CLAIM_VERSION,
        identity,
        state,
        (),
        (),
        (correction,) if corrected else (),
    )
    monkeypatch.setattr(
        collector, "_governance", SimpleNamespace(validity_projection_in_uow=lambda *a: projection)
    )
    with collector._path("ClaimVersion", identity):
        result = collector._validity(None, uuid4(), "claim_version", identity)
    expected = (
        "INVALID"
        if state == ValidityState.INVALID
        else "VALID"
        if state in {ValidityState.NOT_ASSESSED, ValidityState.UNAFFECTED} and not corrected
        else "STALE"
    )
    assert result == expected
    assert collector.witnesses()[0].governance == projection


@pytest.mark.parametrize("states", list(permutations(["VALID", "STALE", "INVALID"])))
def test_invalid_dominates_every_branch_order(states):
    assert _Collector._merge(*states) == "INVALID"


def test_occurrence_sort_dedup_and_historical_lineage():
    collector = _Collector(_unused_uow, None, None, uuid4())
    target = uuid4()
    placements = [uuid4(), uuid4()]
    for placement in reversed(placements):
        with collector._placement_path("CLAIM", placement):
            with collector._path("ClaimVersion", target):
                collector._observe("ClaimVersion", target, "VALID")
                collector._observe("ClaimVersion", target, "VALID")
    with collector._path("SourceVersion", uuid4(), historical=True):
        collector._observe(
            "SourceVersion", collector.nodes[-1].id, "INVALID", source_kind="CORRECTED"
        )
    assert collector.active_state == "VALID"
    witness = next(w for w in collector.witnesses() if w.node.kind == "ClaimVersion")
    assert len(witness.occurrences) == 2
    assert list(witness.occurrences) == sorted(witness.occurrences, key=_path_key)
    assert collector.path_count == 3


@pytest.mark.parametrize("size", [0, 1, 9999, 10000])
def test_exact_row_ceiling(size):
    _bounded(size)


def test_ceiling_plus_one_fails_closed():
    with pytest.raises(ResearchBaseError) as error:
        _bounded(10001)
    assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_path_boundary_and_boolean_ordinal():
    root = AuditNodeRef("ManuscriptVersion", uuid4())
    assert len(AuditOccurrence(None, None, (root,) * 256).nodes) == 256
    for nodes in [(), (root,) * 257, (AuditNodeRef("Run", uuid4()),)]:
        with pytest.raises(ResearchBaseError):
            AuditOccurrence(None, None, nodes)
    with pytest.raises(ResearchBaseError):
        UnsupportedAssertionConcern(
            uuid4(),
            uuid4(),
            root,
            "a" * 64,
            "b" * 64,
            "UNSUPPORTED_CLAIM",
            "INFO",
            "OPEN",
            "Concern",
            True,
            uuid4(),
            uuid4(),
            datetime.now(UTC),
            (),
        )


@pytest.mark.parametrize(
    "field,invalid",
    [
        ("content_hash", "A" * 64),
        ("placement_set_hash", "x"),
        ("evaluated_at", datetime(2026, 1, 1)),
        ("status", "DRAFT"),
        ("current_validity", "RETRACTED"),
    ],
)
def test_readback_hash_status_time_contract(field, invalid):
    args: dict[str, Any] = dict(
        project_id=uuid4(),
        publication_id=uuid4(),
        manuscript_version_id=uuid4(),
        status="FROZEN",
        content_hash="a" * 64,
        placement_set_hash="b" * 64,
        current_validity="VALID",
        witnesses=(),
        evaluated_at=datetime.now(UTC),
    )
    args[field] = invalid
    with pytest.raises(ResearchBaseError):
        ManuscriptValidityReadback(**args)


@pytest.mark.parametrize("description", ["", " ", "e\u0301", "\ud800", "x" * 16001])
def test_issue_text_boundaries(description):
    actor, issue_id = uuid4(), uuid4()
    at = datetime.now(UTC)
    issue = dict(
        id=issue_id,
        severity="INFO",
        issue_type="UNSUPPORTED_CLAIM",
        description=description,
        ordinal=0,
        status="OPEN",
        created_at=at,
    )
    event = dict(
        issue_id=issue_id, prior_status=None, new_status="OPEN", actor_id=actor, occurred_at=at
    )
    with pytest.raises(ResearchBaseError) as error:
        verify_open_issue_history(dict(reviewer_actor_id=actor), [issue], [event])
    assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


@pytest.mark.parametrize(
    "code,http,cli",
    [
        (ErrorCode.VALIDATION_ERROR, 422, 2),
        (ErrorCode.AUTHENTICATION_REQUIRED, 401, 3),
        (ErrorCode.FORBIDDEN, 403, 3),
        (ErrorCode.NOT_FOUND, 404, 3),
        (ErrorCode.VERSION_NOT_FROZEN, 409, 4),
        (ErrorCode.FROZEN_REFERENCE_REQUIRED, 409, 5),
        (ErrorCode.PROVENANCE_CLOSURE_VIOLATION, 409, 5),
        (ErrorCode.CONCURRENT_MODIFICATION, 409, 4),
    ],
)
def test_existing_error_mappings(code, http, cli):
    from researchbase.api.errors import _STATUS
    from researchbase.cli.errors import CLI_EXIT_CODES

    assert _STATUS[code] == http
    assert CLI_EXIT_CODES[code] == cli


def test_snapshot_chain_ceiling_precedes_owner_allocation():
    from researchbase.application.manuscript_validity import _BoundedLiterature

    service = _BoundedLiterature(_unused_uow, None, cast(Any, None))
    uow = SimpleNamespace(
        literature_evidence=SimpleNamespace(snapshot=lambda *a: {"previous_snapshot_id": uuid4()})
    )
    with pytest.raises(ResearchBaseError, match="ceiling"):
        service._snapshot(uow, uuid4(), uuid4())
