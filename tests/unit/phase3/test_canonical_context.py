"""R2 Application admission, exact binding identity and snapshot composition."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, Self

import pytest

from researchbase.agent_runtime.application.canonical_context import CanonicalContextService
from researchbase.agent_runtime.application.context_contracts import (
    ContextRequest,
    ContextWarning,
    InputBinding,
    QuestionContext,
    SourceReference,
    TaskContext,
    ValidityObservation,
)
from researchbase.agent_runtime.application.contracts import InputType
from researchbase.application.provenance_queries import ClosureReportDTO
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7


@pytest.fixture
def reader():
    at = datetime(2026, 10, 24, tzinfo=UTC)
    project, task, step, identity = (new_uuid7() for _ in range(4))
    principal = VerifiedPrincipal(new_uuid7(), "local", "OS_UID", "subject", "credential", at)
    reference = SourceReference(
        type=InputType.RESEARCH_QUESTION_VERSION,
        id=identity,
        content_hash="a" * 64,
        hash_scheme=None,
    )
    bindings = tuple(
        sorted(
            (
                InputBinding(id=new_uuid7(), task_id=task, step_id=owner, source=reference)
                for owner in (None, step)
            ),
            key=lambda value: str(value.id),
        )
    )
    source = QuestionContext(
        reference=reference,
        owner_id=new_uuid7(),
        status="FROZEN",
        frozen_at=at,
        validity=ValidityObservation(
            status="UNASSESSED",
            warnings=(ContextWarning(code="UNASSESSED", source=reference.task_input),),
        ),
        closure=ClosureReportDTO(True, 1, ()),
        question_text="Retained question",
        scope_json=None,
        rationale=None,
    )
    context = TaskContext(
        id=task,
        project_id=project,
        row_version=1,
        plan_sealed_at=None,
        status="CREATED",
        objective="Inspect",
        selected_step_id=None,
        included_step_ids=(step,),
        bindings=bindings,
    )
    log = []
    authority = dict(
        retired_at=None,
        binding_status="ACTIVE",
        membership_status="ACTIVE",
        role="VIEWER",
        effective_from=at,
        effective_until=None,
        bound_at=at,
        revoked_at=None,
    )

    class Uow(SimpleNamespace):
        research_tasks: Any
        task_safety: Any
        context_reads: Any

        def __enter__(self) -> Self:
            log.append("enter")
            return self

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            log.append("exit")

        def begin_formal_read(self):
            log.append("begin")

    def snapshot():
        log.append("snapshot")
        return at

    def get_context(request):
        log.append("context")
        return uow.context

    def get_source(project, reference):
        log.append("source")
        return uow.source

    uow = Uow()
    uow.context, uow.source = context, source
    uow.research_tasks = SimpleNamespace(
        authority=lambda *_: log.append("authority") or [authority],
        project_active=lambda _: True,
        task=lambda _: dict(
            id=task,
            project_id=project,
            row_version=1,
            budget_policy_id=None,
            termination_policy_id=None,
            checkpoint_policy_id=None,
        ),
    )
    uow.task_safety = SimpleNamespace(
        snapshot_at=snapshot,
        rows=lambda *_: (),
        events=lambda *_: (),
    )
    uow.context_reads = SimpleNamespace(task_context=get_context, source=get_source)
    credentials = SimpleNamespace(is_valid=lambda p, checked_at: checked_at == at)
    service = CanonicalContextService(lambda: uow, credentials)
    return SimpleNamespace(
        service=service,
        uow=uow,
        log=log,
        principal=principal,
        request=ContextRequest(project_id=project, task_id=task),
        authority=authority,
    )


def test_single_snapshot_preserves_binding_owners_and_non_authorizing_safety(reader):
    result = reader.service.load_for_task(reader.principal, reader.request)
    assert reader.log == ["enter", "begin", "snapshot", "authority", "context", "source", "exit"]
    assert len(result.sources) == 1 and len(result.task.bindings) == 2
    assert {binding.step_id for binding in result.task.bindings} == {
        None,
        result.task.included_step_ids[0],
    }
    assert result.sources[0].question_text == "Retained question"
    assert result.warnings[0].code == "UNASSESSED"
    assert result.safety.task_row_version == result.checkpoint_history.task_row_version == 1
    assert not result.safety.execution_enabled
    with pytest.raises(FrozenInstanceError):
        result.sources = ()


def test_deduplicated_identity_with_different_saved_hash_fails_closed(reader):
    first, second = reader.uow.context.bindings
    contradictory = replace(second, source=replace(second.source, content_hash="b" * 64))
    reader.uow.context = replace(reader.uow.context, bindings=(first, contradictory))
    with pytest.raises(ResearchBaseError) as caught:
        reader.service.load_for_task(reader.principal, reader.request)
    assert caught.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert reader.log.count("source") == 1 and reader.log[-1] == "exit"


def test_resolved_material_must_match_saved_binding(reader):
    reader.uow.source = replace(
        reader.uow.source,
        reference=replace(
            reader.uow.source.reference,
            content_hash="b" * 64,
        ),
    )
    with pytest.raises(ResearchBaseError) as caught:
        reader.service.load_for_task(reader.principal, reader.request)
    assert caught.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


@pytest.mark.parametrize("role", ["OWNER", "RESEARCHER", "REVIEWER", "APPROVER", "VIEWER"])
def test_shared_read_roles(reader, role):
    reader.authority["role"] = role
    assert (
        reader.service.load_for_task(reader.principal, reader.request).task.id
        == reader.request.task_id
    )


def test_denied_admission_precedes_context_or_source_resolution(reader):
    reader.authority["binding_status"] = "REVOKED"
    with pytest.raises(ResearchBaseError) as caught:
        reader.service.load_for_task(reader.principal, reader.request)
    assert caught.value.code == ErrorCode.FORBIDDEN
    assert "context" not in reader.log and "source" not in reader.log


def test_untrusted_principal_has_no_protected_read(reader):
    with pytest.raises(ResearchBaseError) as caught:
        reader.service.load_for_task(object(), reader.request)
    assert caught.value.code == ErrorCode.AUTHENTICATION_REQUIRED
    assert "authority" not in reader.log


@pytest.mark.parametrize("missing", ["task", "source"])
def test_missing_task_or_required_source_fails_the_query(reader, missing):
    if missing == "task":
        reader.uow.context = None
    else:
        reader.uow.source = None
    with pytest.raises(ResearchBaseError) as caught:
        reader.service.load_for_task(reader.principal, reader.request)
    assert caught.value.code == ErrorCode.NOT_FOUND


def test_closed_request_rejects_before_uow(reader):
    with pytest.raises(ResearchBaseError) as caught:
        reader.service.load_for_task(reader.principal, object())
    assert caught.value.code == ErrorCode.VALIDATION_ERROR
    assert reader.log == []


@pytest.mark.parametrize("status", ["STALE", "INVALID", "UNKNOWN", "UNASSESSED"])
def test_observations_preserve_facts_and_do_not_invent_validity(reader, status):
    reader.uow.source = replace(
        reader.uow.source,
        validity=ValidityObservation(
            status=status,
            warnings=(ContextWarning(code=status, source=reader.uow.source.reference.task_input),),
        ),
    )
    result = reader.service.load_for_task(reader.principal, reader.request)
    assert result.sources[0].question_text == "Retained question"
    assert result.sources[0].validity.status == status
    assert result.warnings[0].code == status


def test_archived_project_and_historical_source_remain_readable(reader):
    reader.uow.research_tasks.project_active = lambda _: False
    reader.uow.source = replace(reader.uow.source, status="SUPERSEDED")
    assert (
        reader.service.load_for_task(reader.principal, reader.request).sources[0].status
        == "SUPERSEDED"
    )


@pytest.mark.parametrize("field", ["binding_status", "membership_status"])
def test_revoked_entitlement_discloses_no_dependencies(reader, field):
    reader.authority[field] = "REVOKED"
    with pytest.raises(ResearchBaseError) as caught:
        reader.service.load_for_task(reader.principal, reader.request)
    assert caught.value.code == ErrorCode.FORBIDDEN
    assert "source" not in reader.log and "context" not in reader.log


def test_revoked_credentials_precede_protected_sql(reader):
    service = CanonicalContextService(
        lambda: reader.uow, SimpleNamespace(is_valid=lambda *_: False)
    )
    with pytest.raises(ResearchBaseError) as caught:
        service.load_for_task(reader.principal, reader.request)
    assert caught.value.code == ErrorCode.FORBIDDEN
    assert "source" not in reader.log and "context" not in reader.log


@pytest.mark.parametrize("warning", ["CORRECTED", "RETRACTED"])
def test_correction_observations_do_not_replace_retained_values(reader, warning):
    reader.uow.source = replace(
        reader.uow.source,
        validity=ValidityObservation(
            status="UNKNOWN",
            warnings=(ContextWarning(code=warning, source=reader.uow.source.reference.task_input),),
        ),
    )
    result = reader.service.load_for_task(reader.principal, reader.request)
    assert result.sources[0].question_text == "Retained question"
    assert result.sources[0].validity.status == "UNKNOWN" and result.warnings[0].code == warning
