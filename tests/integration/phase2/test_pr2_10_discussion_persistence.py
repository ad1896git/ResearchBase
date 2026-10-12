"""Disposable PostgreSQL-only PR2-10 tests; every principal is TEST ONLY."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from researchbase.application.discussion import DiscussionService
from researchbase.application.literature_evidence import LiteratureEvidenceService
from researchbase.application.source_identity import RegisterLiteratureSource
from researchbase.application.source_version import (
    CreateSourceVersion,
    SourceVersionService,
    TransitionSourceVersion,
)
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.source_identity import SourceKind
from researchbase.domain.source_version import (
    FrozenSourceReference,
    SourceVersionKind,
    SourceVersionMaterial,
)
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.test_pr2_01_source_identity import _authorized_service
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import _question

_EXPECTED_ADMIN_URL = "postgresql+psycopg://onephone@/postgres?host=/private/tmp&port=55442"
_EXPECTED_SYSTEM_ID = "7695073913076924777"


@pytest.fixture
def discussion_database_url(monkeypatch):
    admin_url = os.environ.get("RB_PR210_TEST_ADMIN_URL")
    if admin_url != _EXPECTED_ADMIN_URL:
        pytest.fail("RB_PR210_TEST_ADMIN_URL must name the exact approved test instance")
    admin = create_engine(admin_url)
    with admin.connect() as connection:
        identity = connection.execute(text("""SELECT current_user,current_database(),
            current_setting('port'),current_setting('data_directory'),
            (SELECT system_identifier FROM pg_control_system())""")).one()
    assert tuple(map(str, identity)) == (
        "onephone", "postgres", "55442", "/private/tmp/rb-m3-postgres", _EXPECTED_SYSTEM_ID
    )
    print("PR210_PG_PREFLIGHT: port=55442 system_id=7695073913076924777")
    name = f"researchbase_pr210_test_{uuid4().hex}"
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        assert not connection.execute(
            text("SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname=:name)"),
            {"name": name},
        ).scalar_one()
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    print(f"PR210_DISPOSABLE_CREATED: {name}")
    url = f"postgresql+psycopg://onephone@/{name}?host=/private/tmp&port=55442"
    monkeypatch.setenv("DATABASE_URL", url)
    try:
        engine = create_engine(url)
        with engine.connect() as connection:
            assert connection.execute(text("SELECT current_database()")).scalar_one() == name
            assert connection.execute(
                text("SELECT count(*) FROM pg_tables WHERE schemaname='public'")
            ).scalar_one() == 0
        engine.dispose()
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", url)
        command.upgrade(config, "0032_pr2_10_discussion")
        print(f"PR210_DISPOSABLE_REVISION: {name}=0032_pr2_10_discussion")
        yield url
    finally:
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(text("""SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity WHERE datname=:name AND pid<>pg_backend_pid()"""),
                {"name": name})
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        print(f"PR210_DISPOSABLE_DROPPED: {name}")
        admin.dispose()


class _TestCredentials:
    def __init__(self, principal: VerifiedPrincipal):
        self.principal = principal
        self.enabled = True

    def is_valid(self, principal, at):
        del at
        return self.enabled and principal == self.principal


@pytest.fixture
def discussion_env(discussion_database_url, tmp_path):
    engine, _, sources, principal, project = _authorized_service(
        discussion_database_url, migration_revision="0032_pr2_10_discussion"
    )
    _, question_id, _ = _question(engine, project, principal.actor_id)
    credentials = _TestCredentials(principal)
    sf = sessionmaker(engine, expire_on_commit=False, autoflush=False)
    def factory():
        return SqlAlchemyUnitOfWork(sf)
    store = ContentAddressedFilesystemArtifactStore(tmp_path / "cas")
    literature = LiteratureEvidenceService(factory, credentials, store)
    source = sources.register_literature_source(
        RegisterLiteratureSource(principal, project, SourceKind.PAPER,
                                 "Disposable discussion source", uuid4())
    )
    document = literature.import_document(
        principal, project, b"A test-only exact passage.", "text/plain",
        "Disposable fixture rights", uuid4(),
    )
    version_service = SourceVersionService(factory, credentials)
    version = version_service.create(CreateSourceVersion(
        principal, project,
        SourceVersionMaterial(
            UUID(str(source["source_id"])), SourceVersionKind.PUBLISHED,
            None, None, "Disposable discussion source", None, (), None,
            None, None,
            FrozenSourceReference(
                UUID(document["artifact_version_id"]), document["content_hash"]
            ),
            None,
        ), uuid4(),
    ))
    source_id = UUID(str(version["source_version_id"]))
    version_service.freeze(TransitionSourceVersion(
        principal, project, source_id, uuid4()
    ))
    service = DiscussionService(factory, credentials)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0032_pr2_10_discussion"
        )
    yield service, engine, credentials, principal, project, question_id, source_id
    engine.dispose()


def _create(env, request=None):
    service, _, _, principal, project, question, source = env
    return service.create(principal, project, "A bounded research discussion",
                          (question,), (), (source,), request or uuid4())


def test_durable_roundtrip_restart_exact_refs_and_no_promotion(discussion_env):
    service, engine, credentials, principal, project, question, source = discussion_env
    with engine.connect() as connection:
        artifact_count = connection.execute(
            text("SELECT count(*) FROM artifact_versions")
        ).scalar_one()
    created = _create(discussion_env)
    opened = service.read(principal, project, created.session_id)
    assert opened.status == "OPEN"
    assert opened.research_question_version_ids == (question,)
    assert opened.source_version_ids == (source,)
    appended = service.append(principal, project, created.session_id,
                              "method_expert", "Inspect the exact passage.",
                              (source,), (), uuid4())
    assert appended.turn_id is not None
    current = service.read(principal, project, created.session_id)
    assert current.turns[0].actor_id == principal.actor_id
    assert current.turns[0].cited_source_version_ids == (source,)
    closed = service.close(principal, project, created.session_id, uuid4())
    finalized = service.read(principal, project, closed.session_id)
    assert finalized.status == "CLOSED"
    assert finalized.row_version == 2
    assert finalized.closed_by == principal.actor_id
    assert finalized.closed_at is not None
    assert len(finalized.derived_candidates) == 2
    hashes = tuple(item.content_hash for item in finalized.derived_candidates)
    sf = sessionmaker(create_engine(engine.url), expire_on_commit=False, autoflush=False)
    fresh = DiscussionService(lambda: SqlAlchemyUnitOfWork(sf), credentials)
    reread = fresh.read(principal, project, created.session_id)
    assert tuple(item.content_hash for item in reread.derived_candidates) == hashes
    assert reread.turns == finalized.turns
    with pytest.raises(ResearchBaseError) as denied:
        service.request_promotion(principal, project, created.session_id, "Hypothesis")
    assert denied.value.code is ErrorCode.FORBIDDEN
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM discussion_command_receipts")
        ).scalar_one() == 3
        assert connection.execute(text("SELECT count(*) FROM hypotheses")).scalar_one() == 0
        assert connection.execute(text("SELECT count(*) FROM claims")).scalar_one() == 0
        assert connection.execute(
            text("SELECT count(*) FROM artifact_versions")
        ).scalar_one() == artifact_count
    sf.kw["bind"].dispose()


def test_replay_concurrency_and_conflict(discussion_env):
    service, engine, _, principal, project, _, source = discussion_env
    request = uuid4()
    created = _create(discussion_env, request)
    assert _create(discussion_env, request).session_id == created.session_id
    with pytest.raises(ResearchBaseError) as conflict:
        service.create(principal, project, "Changed topic", (), (), (), request)
    assert conflict.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    append_request = uuid4()
    def append_once():
        return service.append(principal, project, created.session_id,
                              "human", "One test-only turn", (source,), (), append_request)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: append_once(), range(2)))
    assert results[0] == results[1]
    assert _create(discussion_env, request) == created
    assert service.read(principal, project, created.session_id).turns[0].id == results[0].turn_id
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM discussion_turns")).scalar_one() == 1


def test_distinct_concurrent_appends_have_contiguous_durable_ordinals(discussion_env):
    service, _, _, principal, project, _, source = discussion_env
    created = _create(discussion_env)
    def append_once(number):
        return service.append(principal, project, created.session_id,
                              "human", f"Test-only turn {number}", (source,), (), uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(append_once, range(2)))
    assert results[0].turn_id != results[1].turn_id
    readback = service.read(principal, project, created.session_id)
    assert [turn.ordinal for turn in readback.turns] == [1, 2]


def test_invalid_refs_authority_state_and_rollback(discussion_env):
    service, engine, credentials, principal, project, _, source = discussion_env
    foreign_project = uuid4()
    with engine.begin() as connection:
        connection.execute(text("""INSERT INTO projects
            (id,name,created_by,created_at) VALUES
            (:id,'Foreign disposable project',:actor,clock_timestamp())"""),
            {"id": foreign_project, "actor": principal.actor_id})
    _, foreign_question, _ = _question(engine, foreign_project, principal.actor_id)
    draft_question, draft_version = uuid4(), uuid4()
    with engine.begin() as connection:
        connection.execute(text("""INSERT INTO research_questions
            (id,project_id,created_by,created_at)
            VALUES (:id,:project,:actor,clock_timestamp())"""),
            {"id": draft_question, "project": project, "actor": principal.actor_id})
        connection.execute(text("""INSERT INTO research_question_versions
            (id,research_question_id,version_number,status,question_text,created_by,created_at)
            VALUES (:id,:question,1,'DRAFT','Draft only',:actor,clock_timestamp())"""),
            {"id": draft_version, "question": draft_question, "actor": principal.actor_id})
    with pytest.raises(ResearchBaseError) as missing:
        service.create(principal, project, "Invalid", (uuid4(),), (), (), uuid4())
    assert missing.value.code is ErrorCode.FROZEN_REFERENCE_REQUIRED
    with pytest.raises(ResearchBaseError) as draft:
        service.create(principal, project, "Draft input", (draft_version,), (), (), uuid4())
    assert draft.value.code is ErrorCode.FROZEN_REFERENCE_REQUIRED
    with pytest.raises(ResearchBaseError) as cross_project:
        service.create(principal, project, "Foreign input", (foreign_question,), (), (), uuid4())
    assert cross_project.value.code is ErrorCode.FROZEN_REFERENCE_REQUIRED
    created = _create(discussion_env)
    with pytest.raises(ResearchBaseError):
        service.append(principal, project, created.session_id, "human", "No",
                       (uuid4(),), (), uuid4())
    with pytest.raises(ResearchBaseError):
        service.close(principal, project, created.session_id, uuid4())
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM discussion_turns")).scalar_one() == 0
        assert connection.execute(
            text("SELECT count(*) FROM discussion_command_receipts")
        ).scalar_one() == 1
    credentials.enabled = False
    with pytest.raises(ResearchBaseError) as forbidden:
        service.append(principal, project, created.session_id, "human", "Denied",
                       (source,), (), uuid4())
    assert forbidden.value.code is ErrorCode.FORBIDDEN
    credentials.enabled = True
    intruder = VerifiedPrincipal(uuid4(), principal.deployment_id, "OS_UID",
                                 "4294967294", "test-untrusted", datetime.now(UTC))
    with pytest.raises(ResearchBaseError):
        service.read(intruder, project, created.session_id)


def test_database_guards_reject_mutation_and_late_append(discussion_env):
    service, engine, _, principal, project, _, source = discussion_env
    created = _create(discussion_env)
    _, second_question, _ = _question(engine, project, principal.actor_id)
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(text("""INSERT INTO discussion_session_question_inputs
                (session_id,version_id,ordinal) VALUES (:session,:version,1)"""),
                {"session": created.session_id, "version": second_question})
    service.append(principal, project, created.session_id, "human", "Test-only content",
                   (source,), (), uuid4())
    closed = service.close(principal, project, created.session_id, uuid4())
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(text("UPDATE discussion_turns SET utterance='forged'"))
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(text("UPDATE discussion_sessions SET topic='forged'"))
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(text("""INSERT INTO discussion_turns
                (id,session_id,ordinal,actor_id,role,utterance,created_at)
                VALUES (:id,:session,2,:actor,'human','late direct write',clock_timestamp())"""),
                {"id": uuid4(), "session": created.session_id,
                 "actor": principal.actor_id})
    with pytest.raises(ResearchBaseError) as late:
        service.append(principal, project, closed.session_id, "human", "Late",
                       (source,), (), uuid4())
    assert late.value.code is ErrorCode.INVALID_STATE_TRANSITION


def test_migration_downgrade_preserves_committed_discussion_history(discussion_env):
    service, engine, _, principal, project, _, source = discussion_env
    created = _create(discussion_env)
    service.append(principal, project, created.session_id, "human", "Immutable history",
                   (source,), (), uuid4())
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", str(engine.url).replace("%2F", "/"))
    with pytest.raises(Exception, match="preserves discussion history"):
        command.downgrade(config, "0031_m3_snapshot_relation_cardinality")
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == "0032_pr2_10_discussion"
        assert connection.execute(
            text("SELECT count(*) FROM discussion_turns")
        ).scalar_one() == 1


def test_citation_order_is_database_enforced(discussion_env):
    service, engine, _, principal, project, _, source = discussion_env
    created = _create(discussion_env)
    appended = service.append(principal, project, created.session_id,
                              "human", "Citation ordering fixture", (), (), uuid4())
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(text("""INSERT INTO discussion_turn_source_citations
                (turn_id,version_id,ordinal) VALUES (:turn,:version,1)"""),
                {"turn": appended.turn_id, "version": source})
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM discussion_turn_source_citations")
        ).scalar_one() == 0


def test_committed_turn_citations_cannot_change(discussion_env):
    service, engine, _, principal, project, _, source = discussion_env
    created = _create(discussion_env)
    appended = service.append(principal, project, created.session_id,
                              "human", "Sealed citation fixture", (), (), uuid4())
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(text("""INSERT INTO discussion_turn_source_citations
                (turn_id,version_id,ordinal) VALUES (:turn,:version,0)"""),
                {"turn": appended.turn_id, "version": source})
    readback = service.read(principal, project, created.session_id)
    assert readback.turns[0].cited_source_version_ids == ()


def test_direct_close_cannot_precede_latest_turn(discussion_env):
    service, engine, _, principal, project, _, _ = discussion_env
    created = _create(discussion_env)
    service.append(principal, project, created.session_id,
                   "human", "Later turn fixture", (), (), uuid4())
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(text("""UPDATE discussion_sessions
                SET status='CLOSED',closed_by=:actor,closed_at=created_at,
                    row_version=row_version+1 WHERE id=:session"""),
                {"actor": principal.actor_id, "session": created.session_id})
    assert service.read(principal, project, created.session_id).status == "OPEN"
