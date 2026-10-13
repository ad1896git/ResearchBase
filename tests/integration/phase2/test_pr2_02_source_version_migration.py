from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Barrier, Event, Lock
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from researchbase.application.source_identity import RegisterLiteratureSource
from researchbase.application.source_merge import (
    DecideSourceMerge,
    ProposeSourceMerge,
    RevokeSourceMergeApproval,
    SourceMergeGovernanceService,
)
from researchbase.application.source_merge_execution import (
    ConsumeSourceMergeProposal,
    SourceMergeExecutionService,
)
from researchbase.application.source_version import (
    CreateSourceVersion,
    SourceVersionService,
    TransitionSourceVersion,
    UpdateSourceVersionDraft,
)
from researchbase.domain.source_identity import IdentifierType, SourceKind
from researchbase.domain.source_version import (
    FrozenSourceReference,
    SourceVersionKind,
    SourceVersionMaterial,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.source_merge_repository import SqlAlchemySourceMergeRepository
from researchbase.persistence.source_version_repository import SqlAlchemySourceVersionRepository
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.test_pr2_01_source_identity import _authorized_service, _frozen_basis


class _ExpiringCredential:
    def __init__(self) -> None:
        self.deadline: datetime | None = None
        self.authorization_times: list[datetime] = []

    def is_valid(self, principal, at):
        del principal
        self.authorization_times.append(at)
        return self.deadline is None or at < self.deadline


@pytest.mark.parametrize("operation", ["create", "update", "freeze", "abandon"])
def test_source_version_authority_rechecks_after_confirmed_lock_wait(
    phase2_database_url: str, operation: str
) -> None:
    credential = _ExpiringCredential()
    engine, _, literature, principal, project_id = _authorized_service(
        phase2_database_url, credential
    )
    source_id = UUID(
        str(
            literature.register_literature_source(
                RegisterLiteratureSource(
                    principal, project_id, SourceKind.PAPER, "Timed version", uuid4()
                )
            )["source_id"]
        )
    )

    service_engine = create_engine(phase2_database_url)

    def factory():
        return SqlAlchemyUnitOfWork(sessionmaker(bind=service_engine, expire_on_commit=False))

    service = SourceVersionService(factory, credential)
    with service_engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    material = SourceVersionMaterial(
        literature_source_id=source_id,
        version_kind=SourceVersionKind.PUBLISHED,
        predecessor_source_version=None,
        correction_basis_artifact=None,
        title="Timed version",
        abstract=None,
        authors=({"name": "Ana Lee", "orcid": None},),
        publication_date=None,
        venue=None,
        external_version_label=None,
        fulltext_artifact=None,
        metadata=None,
    )
    version_id = None
    if operation != "create":
        draft = service.create(CreateSourceVersion(principal, project_id, material, uuid4()))
        version_id = UUID(str(draft["source_version_id"]))
    request_id = uuid4()

    def invoke():
        if operation == "create":
            return service.create(CreateSourceVersion(principal, project_id, material, request_id))
        if operation == "update":
            assert version_id is not None
            changed = SourceVersionMaterial(
                literature_source_id=source_id,
                version_kind=SourceVersionKind.PUBLISHED,
                predecessor_source_version=None,
                correction_basis_artifact=None,
                title="Changed title",
                abstract=None,
                authors=material.authors,
                publication_date=None,
                venue=None,
                external_version_label=None,
                fulltext_artifact=None,
                metadata=None,
            )
            return service.update(
                UpdateSourceVersionDraft(principal, project_id, version_id, changed, request_id)
            )
        assert version_id is not None
        transition = TransitionSourceVersion(principal, project_id, version_id, request_id)
        return service.freeze(transition) if operation == "freeze" else service.abandon(transition)

    lock_acquired_times = []
    original_authorize = SqlAlchemySourceVersionRepository.authorize

    def observe_authorization_lock(repository, authorized_principal, authorized_project, at):
        facts = original_authorize(repository, authorized_principal, authorized_project, at)
        if facts is not None:
            lock_acquired_times.append(repository.at())
        return facts

    authorization_patch = patch.object(
        SqlAlchemySourceVersionRepository, "authorize", observe_authorization_lock
    )

    blocker = engine.connect()
    try:
        blocker.execute(
            text("SELECT id FROM actors WHERE id=:actor FOR UPDATE"),
            {"actor": principal.actor_id},
        )
        blocker_pid = blocker.execute(text("SELECT pg_backend_pid()")).scalar_one()
        credential.authorization_times.clear()
        expiry_at = blocker.execute(
            text("SELECT clock_timestamp() + interval '5 seconds'")
        ).scalar_one()
        credential.deadline = expiry_at
        authorization_patch.start()
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(invoke)
        wait_started_at = None
        transaction_started_at = None
        lock_diagnostics = None
        timeout_at = time.monotonic() + 10
        try:
            while time.monotonic() < timeout_at and not future.done():
                has_lock_wait = blocker.execute(
                    text(
                        "SELECT EXISTS(SELECT 1 FROM pg_locks l "
                        "JOIN pg_stat_activity a ON a.pid=l.pid "
                        "WHERE a.datname=current_database() AND a.pid<>:blocker "
                        "AND NOT l.granted)"
                    ),
                    {"blocker": blocker_pid},
                ).scalar_one()
                database_now = blocker.execute(text("SELECT clock_timestamp()")).scalar_one()
                if has_lock_wait:
                    if wait_started_at is None:
                        wait_started_at = database_now
                        transaction_started_at = blocker.execute(
                            text(
                                "SELECT a.xact_start FROM pg_stat_activity a "
                                "JOIN pg_locks l ON l.pid=a.pid "
                                "WHERE a.datname=current_database() AND a.pid<>:blocker "
                                "AND NOT l.granted ORDER BY a.xact_start DESC LIMIT 1"
                            ),
                            {"blocker": blocker_pid},
                        ).scalar_one_or_none()
                    if database_now >= expiry_at:
                        break
                time.sleep(0.01)
            if wait_started_at is None:
                lock_diagnostics = blocker.execute(
                    text(
                        "SELECT pid,datname,state,wait_event_type,wait_event,left(query,160) "
                        "FROM pg_stat_activity WHERE datname=current_database()"
                    )
                ).all()
            while blocker.execute(text("SELECT clock_timestamp()")).scalar_one() < expiry_at:
                time.sleep(0.01)
            release_time = blocker.execute(text("SELECT clock_timestamp()")).scalar_one()
            blocker.commit()
            with pytest.raises(ResearchBaseError) as denied:
                future.result(timeout=10)
        finally:
            blocker.rollback()
            executor.shutdown(wait=True)
            authorization_patch.stop()
        assert wait_started_at is not None, (
            f"no row-lock observation: {lock_diagnostics!r}; "
            f"deadline={credential.deadline!r}; "
            f"authorization_times={credential.authorization_times!r}; "
            f"principal_verified_at={principal.verified_at!r}"
        )
        assert transaction_started_at is not None
        assert wait_started_at is not None
        assert transaction_started_at < expiry_at
        assert wait_started_at < expiry_at
        assert release_time >= expiry_at
        assert lock_acquired_times
        lock_acquired_at = lock_acquired_times[-1]
        assert lock_acquired_at >= release_time
        assert credential.authorization_times
        assert credential.authorization_times[-1] >= lock_acquired_at
        assert credential.authorization_times[-1] >= expiry_at
        assert denied.value.code is ErrorCode.FORBIDDEN
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM source_version_command_receipts "
                        "WHERE request_id=:request"
                    ),
                    {"request": request_id},
                ).scalar_one()
                == 0
            )
            if operation == "create":
                assert (
                    connection.execute(
                        text(
                            "SELECT count(*) FROM source_versions "
                            "WHERE literature_source_id=:source"
                        ),
                        {"source": source_id},
                    ).scalar_one()
                    == 0
                )
            else:
                row = connection.execute(
                    text("SELECT status,title FROM source_versions WHERE id=:id"),
                    {"id": version_id},
                ).one()
                assert row.status == "DRAFT"
                assert row.title == "Timed version"
                assert (
                    connection.execute(
                        text("SELECT current_version_id FROM literature_sources WHERE id=:source"),
                        {"source": source_id},
                    ).scalar_one()
                    is None
                )
    finally:
        blocker.rollback()
        blocker.close()
        service_engine.dispose()
        engine.dispose()


def test_pr2_02_fresh_migration_adds_version_merge_and_command_receipt_schema(
    phase2_database_url: str,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    with patch.dict("os.environ", {"DATABASE_URL": phase2_database_url}):
        command.upgrade(config, "0022_source_version_and_merge_lineage")

    engine = create_engine(phase2_database_url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0022_source_version_and_merge_lineage"
        )
        tables = set(
            connection.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                    "AND tablename = ANY(:names)"
                ),
                {
                    "names": [
                        "source_versions",
                        "source_merge_records",
                        "source_version_command_receipts",
                    ]
                },
            ).scalars()
        )
        assert tables == {
            "source_versions",
            "source_merge_records",
            "source_version_command_receipts",
        }
        source_columns = set(
            connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='literature_sources'"
                )
            ).scalars()
        )
        assert {"current_version_id", "merged_into_source_id"} <= source_columns
        assert (
            connection.execute(text("SELECT version() ")).scalar_one().startswith("PostgreSQL 18.")
        )
    engine.dispose()


def test_pr2_02_empty_downgrade_restores_0021a_schema(phase2_database_url: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    with patch.dict("os.environ", {"DATABASE_URL": phase2_database_url}):
        command.upgrade(config, "0022_source_version_and_merge_lineage")
        command.downgrade(config, "0021a_source_merge_gov_guards")

    engine = create_engine(phase2_database_url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0021a_source_merge_gov_guards"
        )
        assert (
            connection.execute(text("SELECT to_regclass('public.source_versions')")).scalar_one()
            is None
        )
        columns = set(
            connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='literature_sources'"
                )
            ).scalars()
        )
        assert "current_version_id" not in columns
        assert "merged_into_source_id" not in columns
        stale_guard = connection.execute(
            text(
                "SELECT pg_get_functiondef('rb_validate_source_merge_stale_basis()'::regprocedure)"
            )
        ).scalar_one()
        assert (
            "source merge proposal cannot be marked stale while its durable basis is current"
            in stale_guard
        )
        assert "source_merge_proposal_identifier_basis" in stale_guard
    engine.dispose()
    with patch.dict("os.environ", {"DATABASE_URL": phase2_database_url}):
        command.upgrade(config, "0022_source_version_and_merge_lineage")


def test_pr2_02_populated_downgrade_refuses_without_losing_version_history(
    phase2_database_url: str,
) -> None:
    engine, _, literature, principal, project_id = _authorized_service(
        phase2_database_url, migration_revision="0022_source_version_and_merge_lineage"
    )
    source_id = UUID(
        str(
            literature.register_literature_source(
                RegisterLiteratureSource(
                    principal, project_id, SourceKind.PAPER, "Protected history", uuid4()
                )
            )["source_id"]
        )
    )
    service = SourceVersionService(
        lambda: SqlAlchemyUnitOfWork(sessionmaker(bind=engine, expire_on_commit=False)),
        _Credential(),
    )
    material = SourceVersionMaterial(
        literature_source_id=source_id,
        version_kind=SourceVersionKind.PUBLISHED,
        predecessor_source_version=None,
        correction_basis_artifact=None,
        title="Protected history",
        abstract=None,
        authors=({"name": "Ana Lee", "orcid": None},),
        publication_date=None,
        venue=None,
        external_version_label=None,
        fulltext_artifact=None,
        metadata=None,
    )
    created = service.create(CreateSourceVersion(principal, project_id, material, uuid4()))
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    with patch.dict("os.environ", {"DATABASE_URL": phase2_database_url}):
        with pytest.raises(RuntimeError, match="SOURCE_VERSION_LINEAGE_DATA_PRESERVATION_REQUIRED"):
            command.downgrade(config, "0021a_source_merge_gov_guards")
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM source_versions WHERE id=:id"),
                {"id": UUID(str(created["source_version_id"]))},
            ).scalar_one()
            == 1
        )
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0022_source_version_and_merge_lineage"
        )
    engine.dispose()


class _Credential:
    def is_valid(self, principal, at):
        return True


def test_source_version_lifecycle_and_scoped_command_replay(phase2_database_url: str) -> None:
    engine, identity, literature, principal, project_id = _authorized_service(phase2_database_url)
    source_id = literature.register_literature_source(
        RegisterLiteratureSource(
            principal, project_id, SourceKind.PAPER, "Versioned source", uuid4()
        )
    )["source_id"]
    service = SourceVersionService(
        lambda: SqlAlchemyUnitOfWork(sessionmaker(bind=engine, expire_on_commit=False)),
        _Credential(),
    )
    material = SourceVersionMaterial(
        literature_source_id=UUID(str(source_id)),
        version_kind=SourceVersionKind.PUBLISHED,
        predecessor_source_version=None,
        correction_basis_artifact=None,
        title="Café study",
        abstract=None,
        authors=({"name": "Ana Lee", "orcid": None},),
        publication_date=None,
        venue=None,
        external_version_label=None,
        fulltext_artifact=None,
        metadata=None,
    )
    request_id = uuid4()
    create = CreateSourceVersion(principal, project_id, material, request_id)
    created = service.create(create)
    assert service.create(create) == created
    changed = SourceVersionMaterial(
        literature_source_id=material.literature_source_id,
        version_kind=material.version_kind,
        predecessor_source_version=None,
        correction_basis_artifact=None,
        title="Different title",
        abstract=None,
        authors=material.authors,
        publication_date=None,
        venue=None,
        external_version_label=None,
        fulltext_artifact=None,
        metadata=None,
    )
    with pytest.raises(ResearchBaseError) as conflict:
        service.create(CreateSourceVersion(principal, project_id, changed, request_id))
    assert conflict.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    version_id = UUID(str(created["source_version_id"]))
    updated = service.update(
        UpdateSourceVersionDraft(principal, project_id, version_id, changed, uuid4())
    )
    assert updated["status"] == "DRAFT"
    frozen = service.freeze(TransitionSourceVersion(principal, project_id, version_id, request_id))
    assert frozen["status"] == "FROZEN"
    assert len(str(frozen["content_hash"])) == 64
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT current_version_id FROM literature_sources WHERE id=:source"),
                {"source": material.literature_source_id},
            ).scalar_one()
            == version_id
        )
    with pytest.raises(ResearchBaseError) as immutable:
        service.update(
            UpdateSourceVersionDraft(principal, project_id, version_id, material, uuid4())
        )
    assert immutable.value.code is ErrorCode.SOURCE_VERSION_IMMUTABLE
    other_source_id = literature.register_literature_source(
        RegisterLiteratureSource(principal, project_id, SourceKind.PAPER, "Other source", uuid4())
    )["source_id"]
    merge_governance = SourceMergeGovernanceService(
        lambda: SqlAlchemyUnitOfWork(sessionmaker(bind=engine, expire_on_commit=False)),
        _Credential(),
    )
    proposal = merge_governance.propose(
        ProposeSourceMerge(
            principal,
            project_id,
            material.literature_source_id,
            UUID(str(other_source_id)),
            material.literature_source_id,
            "Version basis snapshot",
            uuid4(),
        )
    )
    with engine.connect() as connection:
        basis_row = connection.execute(
            text("""SELECT current_version_id,current_version_hash,current_version_kind,
                          current_version_status FROM source_merge_proposal_source_basis
                         WHERE proposal_id=:proposal AND source_id=:source"""),
            {
                "proposal": UUID(str(proposal["proposal_id"])),
                "source": material.literature_source_id,
            },
        ).one()
    assert basis_row.current_version_id == version_id
    assert basis_row.current_version_hash == frozen["content_hash"]
    assert basis_row.current_version_kind == "PUBLISHED"
    assert basis_row.current_version_status == "FROZEN"

    second_project = identity.create_project_with_owner(
        principal, name="Second scope", request_id=uuid4()
    )
    second_source = UUID(
        str(
            literature.register_literature_source(
                RegisterLiteratureSource(
                    principal, second_project, SourceKind.PAPER, "Second project source", uuid4()
                )
            )["source_id"]
        )
    )
    second_command = CreateSourceVersion(
        principal,
        second_project,
        SourceVersionMaterial(
            literature_source_id=second_source,
            version_kind=SourceVersionKind.PUBLISHED,
            predecessor_source_version=None,
            correction_basis_artifact=None,
            title="Second project source",
            abstract=None,
            authors=({"name": "Ana Lee", "orcid": None},),
            publication_date=None,
            venue=None,
            external_version_label=None,
            fulltext_artifact=None,
            metadata=None,
        ),
        request_id,
    )
    second_result = service.create(second_command)
    assert second_result["source_version_id"] != created["source_version_id"]
    engine.dispose()


def test_approved_source_merge_is_atomic_and_exactly_once(phase2_database_url: str) -> None:
    engine, _, literature, principal, project_id = _authorized_service(phase2_database_url)
    source_a = UUID(
        str(
            literature.register_literature_source(
                RegisterLiteratureSource(
                    principal,
                    project_id,
                    SourceKind.PAPER,
                    "Merge A",
                    uuid4(),
                    IdentifierType.DOI,
                    "10.5555/merge-a",
                )
            )["source_id"]
        )
    )
    source_b = UUID(
        str(
            literature.register_literature_source(
                RegisterLiteratureSource(
                    principal, project_id, SourceKind.PAPER, "Merge B", uuid4()
                )
            )["source_id"]
        )
    )

    def factory():
        return SqlAlchemyUnitOfWork(sessionmaker(bind=engine, expire_on_commit=False))

    governance = SourceMergeGovernanceService(factory, _Credential())
    from researchbase.application.source_merge import DecideSourceMerge

    evidence_id = _frozen_basis(engine, project_id, principal.actor_id)
    proposal = governance.propose(
        ProposeSourceMerge(
            principal,
            project_id,
            source_a,
            source_b,
            source_b,
            "Duplicate DOI record",
            uuid4(),
            None,
            (evidence_id,),
        )
    )
    proposal_id = UUID(str(proposal["proposal_id"]))
    governance.decide(DecideSourceMerge(principal, project_id, proposal_id, "APPROVE", uuid4()))
    with engine.connect() as connection:
        evidence_hash = connection.execute(
            text("SELECT content_hash FROM artifact_versions WHERE id=:id"),
            {"id": evidence_id},
        ).scalar_one()
    command = ConsumeSourceMergeProposal(
        principal,
        project_id,
        proposal_id,
        str(proposal["proposal_basis_hash"]),
        FrozenSourceReference(evidence_id, evidence_hash),
        uuid4(),
    )
    service = SourceMergeExecutionService(factory, _Credential())
    barrier = Barrier(2)

    def consume_concurrently():
        barrier.wait(timeout=10)
        return service.consume(command)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(consume_concurrently)
        second = executor.submit(consume_concurrently)
        record = first.result(timeout=20)
        assert second.result(timeout=20) == record
    assert record["losing_source_id"] == str(source_a)
    assert record["winning_source_id"] == str(source_b)
    resolved = literature.find_source_by_identifier(
        principal, project_id, IdentifierType.DOI, "10.5555/merge-a"
    )
    assert resolved["source_id"] == str(source_b)
    assert service.consume(command) == record
    with pytest.raises(ResearchBaseError) as changed:
        service.consume(
            ConsumeSourceMergeProposal(
                principal,
                project_id,
                proposal_id,
                command.proposal_basis_hash,
                FrozenSourceReference(evidence_id, "f" * 64),
                command.request_id,
            )
        )
    assert changed.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT lifecycle_status FROM literature_sources WHERE id=:id"),
                {"id": source_a},
            ).scalar_one()
            == "MERGED"
        )
        assert (
            connection.execute(text("SELECT count(*) FROM source_merge_records")).scalar_one() == 1
        )
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM source_merge_governance_events "
                    "WHERE event_kind='PROPOSAL_CONSUMED'"
                )
            ).scalar_one()
            == 1
        )
    engine.dispose()


def test_revoked_merge_approval_returns_canonical_denial_without_effects(
    phase2_database_url: str,
) -> None:
    engine, _, literature, principal, project_id = _authorized_service(phase2_database_url)
    source_a = UUID(
        str(
            literature.register_literature_source(
                RegisterLiteratureSource(
                    principal, project_id, SourceKind.PAPER, "Revoked merge A", uuid4()
                )
            )["source_id"]
        )
    )
    source_b = UUID(
        str(
            literature.register_literature_source(
                RegisterLiteratureSource(
                    principal, project_id, SourceKind.PAPER, "Revoked merge B", uuid4()
                )
            )["source_id"]
        )
    )

    def factory():
        return SqlAlchemyUnitOfWork(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        )

    governance = SourceMergeGovernanceService(factory, _Credential())
    identity_basis_id = _frozen_basis(engine, project_id, principal.actor_id)
    proposal = governance.propose(
        ProposeSourceMerge(
            principal,
            project_id,
            source_a,
            source_b,
            source_b,
            "Approval revocation denial test",
            uuid4(),
            None,
            (identity_basis_id,),
        )
    )
    proposal_id = UUID(str(proposal["proposal_id"]))
    governance.decide(DecideSourceMerge(principal, project_id, proposal_id, "APPROVE", uuid4()))
    governance.revoke(
        RevokeSourceMergeApproval(
            principal, project_id, proposal_id, "Owner withdrew approval", uuid4()
        )
    )
    with engine.connect() as connection:
        identity_basis_hash = connection.execute(
            text("SELECT content_hash FROM artifact_versions WHERE id=:id"),
            {"id": identity_basis_id},
        ).scalar_one()
    service = SourceMergeExecutionService(factory, _Credential())
    command = ConsumeSourceMergeProposal(
        principal,
        project_id,
        proposal_id,
        str(proposal["proposal_basis_hash"]),
        FrozenSourceReference(identity_basis_id, identity_basis_hash),
        uuid4(),
    )

    with pytest.raises(ResearchBaseError) as denied:
        service.consume(command)

    assert denied.value.code is ErrorCode.SOURCE_MERGE_APPROVAL_FORBIDDEN
    with pytest.raises(IntegrityError, match="event violates terminal proposal state"):
        with engine.begin() as connection:
            connection.execute(text("SET CONSTRAINTS trg_source_merge_event_valid IMMEDIATE"))
            connection.execute(
                text(
                    "INSERT INTO source_merge_governance_events"
                    "(id,proposal_id,approval_id,project_id,actor_id,event_kind,occurred_at,reason,"
                    "deployment_id,request_id,request_hash,basis_hash,command_name) "
                    "VALUES (:id,:proposal,NULL,:project,:actor,'PROPOSAL_CONSUMED',"
                    "clock_timestamp(),NULL,:deployment,:request,:request_hash,:basis,"
                    "'CONSUME_SOURCE_MERGE_PROPOSAL')"
                ),
                {
                    "id": uuid4(),
                    "proposal": proposal_id,
                    "project": project_id,
                    "actor": principal.actor_id,
                    "deployment": principal.deployment_id,
                    "request": uuid4(),
                    "request_hash": "b" * 64,
                    "basis": proposal["proposal_basis_hash"],
                },
            )
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT count(*) FROM source_merge_records")).scalar_one() == 0
        )
        states = connection.execute(
            text(
                "SELECT lifecycle_status,merged_into_source_id FROM literature_sources "
                "WHERE id=ANY(:ids) ORDER BY id"
            ),
            {"ids": [source_a, source_b]},
        ).all()
        assert len(states) == 2
        assert all(row.lifecycle_status == "ACTIVE" for row in states)
        assert all(row.merged_into_source_id is None for row in states)
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM source_identifiers WHERE literature_source_id=ANY(:ids)"
                ),
                {"ids": [source_a, source_b]},
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM source_merge_governance_events "
                    "WHERE proposal_id=:proposal AND event_kind='PROPOSAL_CONSUMED'"
                ),
                {"proposal": proposal_id},
            ).scalar_one()
            == 0
        )
    engine.dispose()


@pytest.mark.parametrize("winner", ["revocation", "merge"])
def test_merge_and_approval_revocation_serialize(
    phase2_database_url: str, monkeypatch: pytest.MonkeyPatch, winner: str
) -> None:
    engine, _, literature, principal, project_id = _authorized_service(phase2_database_url)
    source_a = UUID(
        str(
            literature.register_literature_source(
                RegisterLiteratureSource(
                    principal, project_id, SourceKind.PAPER, "Race source A", uuid4()
                )
            )["source_id"]
        )
    )
    source_b = UUID(
        str(
            literature.register_literature_source(
                RegisterLiteratureSource(
                    principal, project_id, SourceKind.PAPER, "Race source B", uuid4()
                )
            )["source_id"]
        )
    )

    def factory():
        return SqlAlchemyUnitOfWork(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        )

    governance = SourceMergeGovernanceService(factory, _Credential())
    identity_basis_id = _frozen_basis(engine, project_id, principal.actor_id)
    proposal = governance.propose(
        ProposeSourceMerge(
            principal,
            project_id,
            source_a,
            source_b,
            source_b,
            "Approval revocation serialization test",
            uuid4(),
            None,
            (identity_basis_id,),
        )
    )
    proposal_id = UUID(str(proposal["proposal_id"]))
    governance.decide(DecideSourceMerge(principal, project_id, proposal_id, "APPROVE", uuid4()))
    with engine.connect() as connection:
        identity_basis_hash = connection.execute(
            text("SELECT content_hash FROM artifact_versions WHERE id=:id"),
            {"id": identity_basis_id},
        ).scalar_one()
    execution = SourceMergeExecutionService(factory, _Credential())
    merge_command = ConsumeSourceMergeProposal(
        principal,
        project_id,
        proposal_id,
        str(proposal["proposal_basis_hash"]),
        FrozenSourceReference(identity_basis_id, identity_basis_hash),
        uuid4(),
    )
    revoke_command = RevokeSourceMergeApproval(
        principal, project_id, proposal_id, "Owner withdrew approval", uuid4()
    )

    first_locked = Event()
    release_first = Event()
    gate_guard = Lock()
    gate_used = False
    original_lock_project = SqlAlchemySourceMergeRepository.lock_project

    def hold_first_project_lock(repository, locked_project_id):
        nonlocal gate_used
        original_lock_project(repository, locked_project_id)
        should_hold = False
        with gate_guard:
            if locked_project_id == project_id and not gate_used:
                gate_used = True
                should_hold = True
        if should_hold:
            first_locked.set()
            if not release_first.wait(timeout=20):
                raise TimeoutError("test did not release the winning transaction")

    monkeypatch.setattr(SqlAlchemySourceMergeRepository, "lock_project", hold_first_project_lock)
    revocation_first = winner == "revocation"

    def first_operation():
        if revocation_first:
            return governance.revoke(revoke_command)
        return execution.consume(merge_command)

    def second_operation():
        if revocation_first:
            return execution.consume(merge_command)
        return governance.revoke(revoke_command)

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(first_operation)
            assert first_locked.wait(timeout=10)
            second = executor.submit(second_operation)
            wait_deadline = time.monotonic() + 10
            lock_wait_observed = False
            while time.monotonic() < wait_deadline and not lock_wait_observed:
                with engine.connect() as connection:
                    lock_wait_observed = connection.execute(
                        text(
                            "SELECT EXISTS(SELECT 1 FROM pg_stat_activity "
                            "WHERE datname=current_database() AND pid<>pg_backend_pid() "
                            "AND wait_event_type='Lock')"
                        )
                    ).scalar_one()
                if not lock_wait_observed:
                    if second.done():
                        second.result()
                    time.sleep(0.01)
            assert lock_wait_observed, "second command did not wait on the shared project lock"
            release_first.set()
            first_result = first.result(timeout=20)
            if revocation_first:
                assert first_result is None
                with pytest.raises(ResearchBaseError) as denied:
                    second.result(timeout=20)
                assert denied.value.code is ErrorCode.SOURCE_MERGE_APPROVAL_FORBIDDEN
            else:
                assert first_result is not None
                assert first_result["winning_source_id"] == str(source_b)
                with pytest.raises(ResearchBaseError) as terminal:
                    second.result(timeout=20)
                assert terminal.value.code is ErrorCode.SOURCE_MERGE_BASIS_CONFLICT
    finally:
        release_first.set()

    with engine.connect() as connection:
        merge_count = connection.execute(
            text("SELECT count(*) FROM source_merge_records")
        ).scalar_one()
        consumed_count = connection.execute(
            text(
                "SELECT count(*) FROM source_merge_governance_events "
                "WHERE event_kind='PROPOSAL_CONSUMED'"
            )
        ).scalar_one()
        revoked_count = connection.execute(
            text(
                "SELECT count(*) FROM source_merge_governance_events "
                "WHERE event_kind='APPROVAL_REVOKED'"
            )
        ).scalar_one()
        source_a_status = connection.execute(
            text("SELECT lifecycle_status FROM literature_sources WHERE id=:id"),
            {"id": source_a},
        ).scalar_one()
    assert merge_count == (0 if revocation_first else 1)
    assert consumed_count == (0 if revocation_first else 1)
    assert revoked_count == (1 if revocation_first else 0)
    assert source_a_status == ("ACTIVE" if revocation_first else "MERGED")
    engine.dispose()
