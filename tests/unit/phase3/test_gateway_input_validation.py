"""Gateway batching retains ordered resolver failures and pass-local reads."""

from itertools import permutations
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from researchbase.agent_runtime.application.capability_gateway import (
    CapabilityGatewayService,
)
from researchbase.agent_runtime.application.contracts import InputType, TaskInput
from researchbase.agent_runtime.domain.capability_invocation import GatewayRef
from researchbase.foundation.errors import ResearchBaseError
from researchbase.persistence.research_task_queries import INPUT_FAMILIES
from researchbase.persistence.research_task_repository import SqlAlchemyResearchTaskRepository


@pytest.mark.parametrize("order", tuple(permutations(range(4))))
def test_batched_input_validation_matches_first_per_ref_error(order):
    project = UUID(int=100)
    ids = [UUID(int=i) for i in range(1, 6)]
    good = dict(scoped=True, status="FROZEN", frozen_at=1, content_hash="a" * 64)
    rows = {
        ("RESEARCH_QUESTION_VERSION", ids[0]): good,
        ("RESEARCH_QUESTION_VERSION", ids[2]): {**good, "scoped": False, "status": "DRAFT"},
        ("RESEARCH_QUESTION_VERSION", ids[3]): {**good, "status": "DRAFT"},
        ("SOURCE_VERSION", ids[4]): {**good, "hash_scheme": "wrong"},
    }
    refs = [GatewayRef("RESEARCH_QUESTION_VERSION", ids[0], "a" * 64, None)]
    failures = [
        GatewayRef("RESEARCH_QUESTION_VERSION", ids[1], "a" * 64, None),
        GatewayRef("RESEARCH_QUESTION_VERSION", ids[2], "a" * 64, None),
        GatewayRef("RESEARCH_QUESTION_VERSION", ids[3], "a" * 64, None),
        GatewayRef("SOURCE_VERSION", ids[4], "a" * 64, "sha256-cjson-v1"),
    ]
    refs += [failures[i] for i in order]
    lookups = []

    def batch(keys, scope):
        assert scope == project
        lookups.append(keys)
        return {key: rows[key] for key in keys if key in rows}

    uow = SimpleNamespace(
        research_tasks=SimpleNamespace(
            input_version=lambda kind, identity, scope: rows.get((kind, identity)),
            input_versions=batch,
        ),
        research_questions=SimpleNamespace(
            get_version=lambda identity: SimpleNamespace(content_hash="a" * 64)
        ),
    )
    uow.hypotheses = uow.claims = uow.research_questions
    service = CapabilityGatewayService(lambda: cast(Any, uow), None)
    with pytest.raises(ResearchBaseError) as before:
        for ref in refs:
            service._resolve(
                uow,
                project,
                TaskInput(InputType(ref.family), ref.version_id),
                {"content_hash": ref.content_hash, "hash_scheme": ref.hash_scheme},
            )
    with pytest.raises(ResearchBaseError) as after:
        service._validate_input_refs(uow, project, [], refs)
    assert (after.value.code, str(after.value)) == (before.value.code, str(before.value))
    assert len(lookups) == 1 and len(lookups[0]) == 5


def test_batched_input_validation_reloads_validity_on_next_pass(monkeypatch):
    from researchbase.application.governance_queries import ValidityProjection, ValidityState
    from researchbase.domain.governance import GovernanceTargetType

    project, identity = UUID(int=1), UUID(int=2)
    row = dict(scoped=True, status="FROZEN", frozen_at=1, content_hash="a" * 64, byte_size=1)
    reads = []
    state = [ValidityState.UNAFFECTED]

    def batch(scope, targets, *, defer_errors):
        assert scope == project and defer_errors
        reads.append(targets)
        return {key: ValidityProjection(key[0], key[1], state[0], (), (), ()) for key in targets}

    uow = SimpleNamespace(
        research_tasks=SimpleNamespace(
            input_versions=lambda refs, scope: {("ARTIFACT_VERSION", identity): row}
        ),
        manuscript_freeze=SimpleNamespace(),
        gateway=SimpleNamespace(input_validity_projections=batch),
    )
    service = CapabilityGatewayService(lambda: cast(Any, uow), None)
    seen = []
    from researchbase.application.manuscript_freeze import ManuscriptFreezeService

    monkeypatch.setattr(
        ManuscriptFreezeService,
        "_observe",
        lambda self, kind, identity, state, **facts: seen.append(state),
    )
    ref = GatewayRef("ARTIFACT_VERSION", identity, "a" * 64, None)
    service._validate_input_refs(uow, project, [], [ref, ref])
    state[0] = ValidityState.STALE
    service._validate_input_refs(uow, project, [], [ref, ref])
    assert reads == [((GovernanceTargetType.ARTIFACT_VERSION, identity),)] * 2
    assert seen[-2:] == ["STALE", "STALE"]


def test_repository_input_versions_one_statement_native_rows_and_scope():
    families = tuple(INPUT_FAMILIES)
    refs = tuple((kind, UUID(int=i + 1)) for i, kind in enumerate(families))
    fields = ["kind", "requested_id"]
    for i in range(6):
        fields += [f"rb_batch_start_{i}", "id", "content_hash", "frozen_at", "scoped"]
        if families[i] == "ARTIFACT_VERSION":
            fields += ["project_id", "artifact_type"]
    raw = []
    stamp = object()
    for index, (kind, identity) in enumerate(refs):
        row = [kind, identity]
        for i in range(6):
            row += [None, identity if index == i else None, "a" * 64, stamp, index != 2]
            if families[i] == "ARTIFACT_VERSION":
                row += [UUID(int=100), "data"]
        raw.append(row)

    class Result:
        def keys(self):
            return fields

        def __iter__(self):
            return iter(raw)

    class Recording:
        def __init__(self):
            self.calls = []

        def execute(self, sql, params):
            self.calls.append((str(sql), params))
            return Result()

    session = Recording()
    repo = SqlAlchemyResearchTaskRepository(cast(Session, session))
    rows = repo.input_versions(refs + refs[:1], UUID(int=100))
    assert len(session.calls) == 1 and len(rows) == 6
    sql, params = session.calls[0]
    assert len(params) == 13
    assert "literature_source_project_links" in sql
    for i, (kind, identity) in enumerate(refs):
        assert rows[kind, identity]["id"] is identity
        assert rows[kind, identity]["frozen_at"] is stamp
        assert rows[kind, identity]["scoped"] == (i != 2)
        assert f"{INPUT_FAMILIES[kind][1]} v{i}" in sql
    assert repo.input_versions((), UUID(int=100)) == {} and len(session.calls) == 1


@pytest.mark.parametrize("bad_hash", [True, False])
def test_batched_saved_input_failure_order_includes_malformed_later_binding(bad_hash):
    from tests.unit.phase3.gateway_fixtures import Fixture

    from researchbase.agent_runtime.application.research_task import _INPUT_COLUMNS

    f = Fixture()
    good = {
        **dict.fromkeys(_INPUT_COLUMNS.values()),
        "research_question_version_id": f.ref_id,
        "content_hash": "b" * 64 if bad_hash else f.ref_hash,
        "hash_scheme": None,
    }
    malformed = {**good, "research_question_version_id": None}
    with f.factory() as uow:
        with pytest.raises(ResearchBaseError) as before:
            f.service._saved_inputs(uow, f.project, [good, malformed])
        with pytest.raises(ResearchBaseError) as after:
            f.service._validate_input_refs(uow, f.project, [good, malformed], [])
    assert (after.value.code, str(after.value)) == (before.value.code, str(before.value))


def test_batched_unknown_version_precedes_later_invalid_family():
    from tests.unit.phase3.gateway_fixtures import Fixture

    from researchbase.foundation.errors import ErrorCode

    f = Fixture()
    refs = [
        SimpleNamespace(
            family="RESEARCH_QUESTION_VERSION",
            version_id=UUID(int=999),
            content_hash="a" * 64,
            hash_scheme=None,
        ),
        SimpleNamespace(
            family="INVALID", version_id=f.ref_id, content_hash="a" * 64, hash_scheme=None
        ),
    ]
    with f.factory() as uow:
        with pytest.raises(ResearchBaseError) as before:
            for ref in refs:
                f.service._resolve(
                    uow,
                    f.project,
                    TaskInput(InputType(ref.family), ref.version_id),
                    {"content_hash": ref.content_hash, "hash_scheme": ref.hash_scheme},
                )
        with pytest.raises(ResearchBaseError) as after:
            f.service._validate_input_refs(uow, f.project, [], refs)
    assert after.value.code == ErrorCode.NOT_FOUND
    assert (after.value.code, str(after.value)) == (before.value.code, str(before.value))


def test_discovery_error_then_deeper_target_raises_gateway_error(monkeypatch):
    from tests.unit.phase3.gateway_fixtures import Fixture

    from researchbase.application.manuscript_freeze import ManuscriptFreezeService
    from researchbase.foundation.errors import ErrorCode

    f = Fixture()
    calls = []
    monkeypatch.setattr(
        ManuscriptFreezeService, "with_governance", lambda self, governance: governance
    )

    def resolve(uow, project, ref, saved, *, verifier):
        calls.append(ref)
        if len(calls) == 1:
            raise ResearchBaseError(ErrorCode.NOT_FOUND, "discovery owning read failed")
        # Real validity can choose a deeper path that neutral discovery missed.
        verifier.validity_projection_in_uow(uow, project, "measurement", UUID(int=999))

    monkeypatch.setattr(f.service, "_resolve", resolve)
    ref = GatewayRef("RESEARCH_QUESTION_VERSION", f.ref_id, f.ref_hash, None)
    with f.factory() as uow:
        with pytest.raises(ResearchBaseError) as error:
            f.service._validate_input_refs(uow, f.project, [], [ref])
    assert len(calls) == 2
    assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert str(error.value) == "gateway validity target unavailable in discovered snapshot"
