"""Durable R2 evidence on disposable PostgreSQL 18 through the actual reader."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from importlib import import_module
from threading import Event

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import sessionmaker
from tests.application_compat import LegacyApplicationService
from tests.integration.phase3.conftest import Credentials
from tests.integration.phase3.test_pr3_04_application import bind, command
from tests.integration.phase3.test_pr3_04_application import service as safety_service
from tests.integration.test_pr12_application import seed_claim, seed_measurement

from researchbase.agent_runtime.application.canonical_context import CanonicalContextService
from researchbase.agent_runtime.application.context_contracts import (
    ArtifactContext,
    ClaimContext,
    ContextRequest,
    LiteratureContext,
    ManuscriptContext,
)
from researchbase.agent_runtime.application.contracts import InputType, TaskInput
from researchbase.agent_runtime.application.research_task import TaskContextAdmission
from researchbase.agent_runtime.application.safety_contracts import BindPoliciesArguments
from researchbase.application.commands import (
    CreateArtifactCommand,
    CreateArtifactVersionCommand,
    CreateProjectCommand,
    FreezeArtifactVersionCommand,
    FreezeClaimVersionCommand,
    LinkEvidenceCommand,
)
from researchbase.application.governance import (
    CreateAuditFindingCommand,
    CreateImpactAssessmentCommand,
    GovernanceService,
    ProposedImpactTarget,
)
from researchbase.domain.artifact import ArtifactId, ArtifactVersionId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.ids import new_uuid7
from researchbase.foundation.time import SystemClock
from researchbase.persistence.context_repository import SqlAlchemyContextRepository
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


def create_task(planning, inputs):
    request = planning.command(
        arguments=dict(
            task_type="OTHER",
            objective="Inspect retained inputs",
            strategy_id="fixed",
            strategy_version="1",
            inputs=[{"type": kind, "id": str(identity)} for kind, identity in inputs.items()],
        )
    )
    planning.service.execute(planning.principal, request)
    return request.task_id


def reader(planning, *, store=None, engine=None):
    sessions = sessionmaker(engine if engine is not None else planning.engine)

    def factory():
        return SqlAlchemyUnitOfWork(
            sessions, context_artifact_store=store if store is not None else planning.store
        )

    return CanonicalContextService(factory, Credentials())


def scope(planning, task, step=None):
    return ContextRequest(project_id=planning.project, task_id=task, step_id=step)


@pytest.mark.parametrize("kind", tuple(InputType))
def test_each_family_resolves_task_and_step_bindings(planning, scientific_inputs, kind):
    identity = scientific_inputs[kind]
    task = create_task(planning, {kind: identity})
    step = new_uuid7()
    planning.plan(
        task,
        nodes=[
            dict(
                step_id=str(step),
                step_type="PLAN",
                ordinal=1,
                inputs=[{"type": kind, "id": str(identity)}],
            )
        ],
    )
    result = reader(planning).load_for_task(planning.principal, scope(planning, task, step))
    assert len(result.sources) == 1 and len(result.task.bindings) == 2
    source = result.sources[0]
    assert source.type == kind and source.reference.id == identity
    assert {b.step_id for b in result.task.bindings} == {None, step}
    assert all(b.source == source.reference for b in result.task.bindings)
    assert source.status == "FROZEN" and source.closure.complete
    assert source.validity.status == "UNASSESSED"
    assert any(w.code == "UNASSESSED" for w in result.warnings)
    if kind == InputType.CLAIM_VERSION:
        assert isinstance(source, ClaimContext)
        assert source.experiment_trace.paths and source.experiment_trace.runs
    elif kind == InputType.ARTIFACT_VERSION:
        assert isinstance(source, ArtifactContext)
        assert source.verified_bytes == b"pr301 exact input"
    elif kind == InputType.SOURCE_VERSION:
        assert isinstance(source, LiteratureContext)
        assert source.title == "Source" and source.fulltext is None
    elif kind == InputType.MANUSCRIPT_VERSION:
        assert isinstance(source, ManuscriptContext)
        assert (
            source.title == "Study" and source.document.id == scientific_inputs["ARTIFACT_VERSION"]
        )
    assert not result.safety.execution_enabled


def test_one_readonly_snapshot_survives_committed_writer(
    planning,
    scientific_inputs,
    normal_engine,
    monkeypatch,
):
    task = create_task(planning, scientific_inputs)
    observed, sessions = [], []
    reached, committed = Event(), Event()
    original = SqlAlchemyContextRepository.task_context

    def pause_after_bindings(repo, request):
        result = original(repo, request)
        reached.set()
        assert committed.wait(10), "concurrent writer did not commit"
        return result

    monkeypatch.setattr(SqlAlchemyContextRepository, "task_context", pause_after_bindings)

    def capture(conn, cursor, statement, parameters, context, executemany):
        observed.append(statement)

    def no_commit(conn):
        raise AssertionError("reader committed")

    class ObservedUow(SqlAlchemyUnitOfWork):
        def begin_formal_read(self):
            super().begin_formal_read()
            session = self._require_session()
            assert not session.autoflush
            assert session.execute(text("SHOW transaction_read_only")).scalar_one() == "on"
            assert (
                session.execute(text("SHOW transaction_isolation")).scalar_one()
                == "repeatable read"
            )
            assert not session.execute(
                text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")
            ).scalar_one()
            sessions.append(session)

            def no_flush(*args):
                raise AssertionError("reader flushed")

            event.listen(session, "before_flush", no_flush)

    def factory() -> SqlAlchemyUnitOfWork:
        return ObservedUow(sessionmaker(normal_engine), context_artifact_store=planning.store)

    def cancel():
        assert reached.wait(10), "reader did not reach bindings"
        planning.service.execute(
            planning.principal,
            planning.command(
                "cancel_research_task",
                task,
                1,
                {"reason": "Concurrent legitimate writer"},
            ),
        )
        committed.set()

    event.listen(normal_engine, "before_cursor_execute", capture)
    event.listen(normal_engine, "commit", no_commit)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            writer = pool.submit(cancel)
            result = CanonicalContextService(factory, Credentials()).load_for_task(
                planning.principal,
                scope(planning, task),
            )
            writer.result(timeout=10)
        assert result.task.row_version == result.safety.task_row_version == 1
        assert result.task.status == "CREATED" and len(result.sources) == 6
        assert len(sessions) == 1
        assert sum("transaction_timestamp()" in sql for sql in observed) == 1
        assert all(sql.lstrip().upper().startswith(("SELECT", "SHOW", "WITH")) for sql in observed)
        assert not any(
            token in sql.upper()
            for sql in observed
            for token in ("FOR UPDATE", "FOR SHARE", "PG_ADVISORY", "LOCK TABLE")
        )
    finally:
        event.remove(normal_engine, "before_cursor_execute", capture)
        event.remove(normal_engine, "commit", no_commit)
    fresh = reader(planning).load_for_task(planning.principal, scope(planning, task))
    assert fresh.task.row_version == fresh.safety.task_row_version == 2
    assert fresh.task.status == "CANCELLED"


class StoreSpy:
    def __init__(self, store):
        self.store, self.calls = store, []

    def verify(self, identity):
        self.calls.append(("verify", identity))
        return self.store.verify(identity)

    def open(self, identity):
        self.calls.append(("open", identity))
        return self.store.open(identity)


@pytest.mark.parametrize("project_scope", ["global", "foreign"])
def test_out_of_scope_node_denied_before_any_store_access(planning, project_scope):
    context = ExecutionContext(
        actor_id=planning.principal.actor_id, request_id=new_uuid7(), client_type="test"
    )
    app = LegacyApplicationService(planning.factory, SystemClock(), planning.store)
    project = (
        None
        if project_scope == "global"
        else app.create_project(CreateProjectCommand("Foreign artifact scope", None, context)).id
    )
    artifact = app.create_artifact(CreateArtifactCommand(project, "data", "Scoped", None, context))
    version = app.create_artifact_version(
        CreateArtifactVersionCommand(
            ArtifactId(artifact.id),
            b"private bytes",
            None,
            None,
            "text/plain",
            13,
            None,
            context,
        )
    )
    app.freeze_artifact_version(
        FreezeArtifactVersionCommand(
            ArtifactId(artifact.id),
            ArtifactVersionId(version.id),
            context,
            version.row_version,
        )
    )
    store = StoreSpy(planning.store)
    with SqlAlchemyUnitOfWork(sessionmaker(planning.engine), context_artifact_store=store) as uow:
        uow.begin_formal_read()
        TaskContextAdmission(Credentials()).authorize_context_read(
            uow,
            planning.principal,
            planning.project,
            uow.task_safety.snapshot_at(),
        )
        with pytest.raises(ResearchBaseError) as caught:
            uow.context_reads.source(
                planning.project, TaskInput(InputType.ARTIFACT_VERSION, version.id)
            )
    assert caught.value.code == ErrorCode.FORBIDDEN and not store.calls
    assert str(version.id) not in str(caught.value) and "private bytes" not in str(caught.value)


@pytest.mark.parametrize("damage", ["missing", "corrupt"])
def test_required_artifact_bytes_fail_entire_query(planning, scientific_inputs, damage):
    task = create_task(planning, {"MANUSCRIPT_VERSION": scientific_inputs["MANUSCRIPT_VERSION"]})
    artifact = reader(planning).load_for_task(planning.principal, scope(planning, task))
    assert isinstance(artifact.sources[0], ManuscriptContext)
    digest = artifact.sources[0].document.content_hash
    path = planning.store.root / "sha256" / digest[:2] / digest[2:4] / digest
    original = path.read_bytes()
    try:
        if damage == "missing":
            path.unlink()
        else:
            path.write_bytes(b"corrupted content")
        with pytest.raises(ResearchBaseError) as caught:
            reader(planning).load_for_task(planning.principal, scope(planning, task))
        assert caught.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    finally:
        path.write_bytes(original)


@pytest.mark.parametrize("module_name", ["researchbase.api.app", "researchbase.cli.composition"])
def test_real_composition_supplies_configured_artifact_store(
    planning,
    scientific_inputs,
    monkeypatch,
    tmp_path,
    module_name,
):
    module = import_module(module_name)
    monkeypatch.setenv("DATABASE_URL", planning.url)
    monkeypatch.setenv("ARTIFACT_STORE_ROOT", str(planning.store.root))
    monkeypatch.setenv("RESEARCHBASE_LOCAL_ROOT", str(tmp_path / "no-local-identity"))
    monkeypatch.setattr(module, "LocalIdentityAdapter", lambda *_: Credentials())
    task = create_task(planning, {"ARTIFACT_VERSION": scientific_inputs["ARTIFACT_VERSION"]})
    bundle = module.build_services()
    result = bundle.canonical_context.load_for_task(planning.principal, scope(planning, task))
    assert result.sources[0].verified_bytes == b"pr301 exact input"


def test_current_validity_and_safety_are_observations(planning):
    context = ExecutionContext(
        actor_id=planning.principal.actor_id, request_id=new_uuid7(), client_type="test"
    )
    # Give this test its own scientific history; never stale the session-scoped input fixture.
    app = LegacyApplicationService(planning.factory, SystemClock(), planning.store)
    measurement = seed_measurement(app, planning.project, context, "R2 validity")
    claim, version = seed_claim(app, planning.project, context)
    app.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            measurement,
            None,
            "supports",
            None,
            version.row_version,
            context,
        )
    )
    linked = app.get_current_claim_version(claim.id)
    frozen = app.freeze_claim_version(
        FreezeClaimVersionCommand(
            claim.id,
            linked.id,
            context,
            linked.row_version,
        )
    )
    identity = frozen.id
    task = create_task(planning, {"CLAIM_VERSION": identity})
    bound, _ = bind(planning, task, checkpoint={"required_types": ["plan_review"]})
    assert isinstance(bound.arguments, BindPoliciesArguments)
    governance = GovernanceService(planning.factory, SystemClock())
    finding = governance.create_audit_finding(
        CreateAuditFindingCommand(
            planning.project,
            "code_bug",
            "major",
            "R2 stale evidence",
            "Retained fact remains",
            "claim_version",
            identity,
            context,
        )
    )
    assessment = governance.create_impact_assessment(
        CreateImpactAssessmentCommand(
            planning.project,
            finding.id,
            {"basis": "R2 read test"},
            "stale",
            (ProposedImpactTarget("claim_version", identity, "stale"),),
            context,
        )
    )
    result = reader(planning).load_for_task(planning.principal, scope(planning, task))
    assert isinstance(result.sources[0], ClaimContext)
    assert result.sources[0].validity.status == "STALE"
    assert assessment.id in result.sources[0].validity.assessment_ids
    assert any(warning.code == "STALE" for warning in result.warnings)
    assert result.sources[0].statement and result.sources[0].experiment_trace.closure.complete
    assert result.safety.budget_policy_id == bound.arguments.budget_id
    assert result.safety.checkpoint_policy_id == bound.arguments.checkpoint_policy_id
    assert not result.safety.execution_enabled and any(
        not g.satisfied for g in result.safety.required_gates
    )


def test_expiry_is_projected_without_changing_checkpoint_history(planning):
    task = planning.create()
    bind(planning, task, checkpoint={"required_types": ["plan_review"], "timeout_seconds": 1})
    request = command(
        planning,
        task,
        2,
        "request_human_checkpoint",
        dict(
            checkpoint_id=str(new_uuid7()),
            step_id=None,
            checkpoint_type="plan_review",
            reason="Read expiry only",
        ),
    )
    safety_service(planning).execute(planning.principal, request)
    with planning.engine.connect() as conn:
        conn.execute(
            text(
                "SELECT pg_sleep(greatest(0,extract(epoch FROM (expires_at-clock_timestamp())))) "
                "FROM human_checkpoints WHERE research_task_id=:id"
            ),
            {"id": task},
        )
    result = reader(planning).load_for_task(planning.principal, scope(planning, task))
    checkpoint = result.checkpoint_history.checkpoints[0]
    assert checkpoint.status == "PENDING" and checkpoint.effective_status == "EXPIRED"
    with planning.engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT status FROM human_checkpoints WHERE research_task_id=:id"),
                {"id": task},
            ).scalar_one()
            == "PENDING"
        )


def test_dedup_contradiction_fails_closed_in_postgres_read(
    planning,
    scientific_inputs,
    monkeypatch,
):
    identity = scientific_inputs["RESEARCH_QUESTION_VERSION"]
    task = create_task(planning, {"RESEARCH_QUESTION_VERSION": identity})
    planning.plan(
        task,
        nodes=[
            dict(
                step_id=str(new_uuid7()),
                step_type="PLAN",
                ordinal=1,
                inputs=[{"type": "RESEARCH_QUESTION_VERSION", "id": str(identity)}],
            )
        ],
    )
    original = SqlAlchemyContextRepository.bindings

    def contradictory_read(repo, request):
        # Fault-inject an inconsistent read projection; never bypass a DB guard or alter history.
        first, second = original(repo, request)
        return first, replace(second, source=replace(second.source, content_hash="0" * 64))

    monkeypatch.setattr(SqlAlchemyContextRepository, "bindings", contradictory_read)
    with pytest.raises(ResearchBaseError) as caught:
        reader(planning).load_for_task(planning.principal, scope(planning, task))
    assert caught.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_revoked_principal_and_wrong_step_disclose_no_context(planning, scientific_inputs):
    task = create_task(planning, scientific_inputs)
    store = StoreSpy(planning.store)
    for principal, request in (
        (replace(planning.principal, actor_id=new_uuid7()), scope(planning, task)),
        (planning.principal, scope(planning, task, new_uuid7())),
    ):
        with pytest.raises(ResearchBaseError) as caught:
            reader(planning, store=store).load_for_task(principal, request)
        assert caught.value.code == ErrorCode.FORBIDDEN and not store.calls
