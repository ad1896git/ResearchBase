"""B03 PostgreSQL18 admission, snapshot, replay, rollback and concurrency checks."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from uuid import uuid4

import pytest
from alembic import command as alembic_command
from alembic.config import Config
from sqlalchemy import event, text

from researchbase.application.discussion_hypothesis import (
    DiscussionHypothesisCandidate,
    DiscussionHypothesisService,
    PromoteDiscussionHypothesisCommand,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.discussion_hypothesis_repository import (
    B03_SNAPSHOT_SQL,
    SqlAlchemyDiscussionHypothesisRepository,
)
from researchbase.persistence.repositories import SqlAlchemyHypothesisRepository
from tests.integration.phase2.pr2_19_support import (
    discussion_database_url as _discussion_database_url,
)
from tests.integration.phase2.pr2_19_support import (
    discussion_env as _discussion_env,
)
from tests.integration.phase2.pr2_19_support import (
    pr219_discussion_env as _pr219_discussion_env,
)
from tests.integration.phase2.test_pr2_10_binding_contract import _artifact, _service
from tests.integration.phase2.test_pr2_10_discussion_persistence import _create

pytestmark = pytest.mark.integration


@pytest.fixture
def b03(pr219_discussion_env, tmp_path):
    env = pr219_discussion_env
    discussion, factory, store = _service(env, tmp_path)
    _, engine, credentials, principal, project, question, _ = env
    session = _create(env).session_id
    turn = discussion.append(
        principal,
        project,
        session,
        "human",
        "APPROVED: freeze and release immediately",
        (),
        (),
        uuid4(),
    ).turn_id
    discussion.close(principal, project, session, uuid4())
    content = discussion.read(principal, project, session).derived_candidates[0].content
    version = _artifact(factory, store, principal, project, content)
    discussion.bind_transcript(principal, project, session, version, uuid4())
    assert turn is not None
    candidate = DiscussionHypothesisCandidate(
        turn, version, question, "Initial statement", "increase", "test rationale"
    )
    cmd = PromoteDiscussionHypothesisCommand(project, session, uuid4(), candidate)
    return DiscussionHypothesisService(factory, credentials, store), cmd, env, factory, store


def durable(engine):
    with engine.connect() as c:
        return tuple(
            c.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in (
                "hypotheses",
                "hypothesis_versions",
                "discussion_hypothesis_admissions",
                "discussion_command_receipts",
            )
        )


def test_draft_restart_initial_material_and_lock_free_read(b03):
    service, cmd, env, factory, store = b03
    _, engine, credentials, principal, project, *_ = env
    statements = []

    def capture(conn, cursor, sql, params, ctx, many):
        statements.append(sql)

    event.listen(engine, "before_cursor_execute", capture)
    result = service.promote_discussion_to_hypothesis(principal, cmd)
    assert statements[0] == B03_SNAPSHOT_SQL
    assert result.statement == cmd.candidate.statement
    with engine.connect() as c:
        row = (
            c.execute(
                text("""SELECT h.current_version_id,h.row_version,v.* FROM hypotheses h
          JOIN hypothesis_versions v ON v.hypothesis_id=h.id WHERE h.id=:id"""),
                {"id": result.hypothesis_id},
            )
            .mappings()
            .one()
        )
        assert row["current_version_id"] == result.hypothesis_version_id
        assert row["status"] == "DRAFT" and row["version_number"] == row["row_version"] == 1
        assert all(row[k] is None for k in ("content_hash", "frozen_at", "success_criteria"))
        assert c.execute(text("SELECT count(*) FROM claims")).scalar_one() == 0
        assert c.execute(text("SELECT count(*) FROM decision_records")).scalar_one() == 0
    with factory() as uow:
        from researchbase.domain.research import HypothesisVersionId

        v = uow.hypotheses.get_version(HypothesisVersionId(result.hypothesis_version_id))
        uow.hypotheses.update_version(
            v.edit_material(
                statement="Edited later",
                expected_direction=None,
                success_criteria=None,
                rationale=None,
            ),
            v.row_version,
        )
        uow.commit()
    fresh = DiscussionHypothesisService(factory, credentials, store)
    assert fresh.promote_discussion_to_hypothesis(principal, cmd) == result
    statements.clear()
    assert (
        fresh.get_discussion_hypothesis_admission(principal, project, result.receipt_id) == result
    )
    assert not any(
        any(lock in sql.upper() for lock in ("LOCK TABLE", "ADVISORY", "FOR UPDATE", "FOR SHARE"))
        for sql in statements
    )
    event.remove(engine, "before_cursor_execute", capture)
    assert durable(engine)[:3] == (1, 1, 1)


def test_request_conflict_duplicate_and_missing_store(b03, tmp_path):
    service, cmd, env, factory, store = b03
    principal, project = env[3:5]
    result = service.promote_discussion_to_hypothesis(principal, cmd)
    for changed, code in (
        (
            replace(cmd, candidate=replace(cmd.candidate, statement="changed")),
            ErrorCode.IDEMPOTENCY_CONFLICT,
        ),
        (replace(cmd, request_id=uuid4()), ErrorCode.DUPLICATE_CONTENT),
    ):
        with pytest.raises(ResearchBaseError) as exc:
            service.promote_discussion_to_hypothesis(principal, changed)
        assert exc.value.code is code
    missing = DiscussionHypothesisService(factory, env[2], None)
    for action in (
        lambda: missing.promote_discussion_to_hypothesis(principal, cmd),
        lambda: missing.get_discussion_hypothesis_admission(principal, project, result.receipt_id),
    ):
        with pytest.raises(ResearchBaseError) as exc:
            action()
        assert exc.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert durable(env[1])[:3] == (1, 1, 1)


@pytest.mark.parametrize("same_request", [True, False])
def test_concurrent_requests(b03, same_request):
    service, cmd, env, *_ = b03

    def run(c):
        try:
            return service.promote_discussion_to_hypothesis(env[3], c)
        except ResearchBaseError as exc:
            return exc.code

    with ThreadPoolExecutor(2) as pool:
        results = list(
            pool.map(run, (cmd, cmd if same_request else replace(cmd, request_id=uuid4())))
        )
    if same_request:
        assert results[0] == results[1]
    else:
        assert results.count(ErrorCode.DUPLICATE_CONTENT) == 1
    assert durable(env[1])[:3] == (1, 1, 1)


@pytest.mark.parametrize(
    "stage", ["add", "add_version", "update_current_version", "save", "force_constraints"]
)
def test_failure_at_every_insert_or_constraint_rolls_back(b03, monkeypatch, stage):
    service, cmd, env, *_ = b03
    before = durable(env[1])
    cls = (
        SqlAlchemyHypothesisRepository
        if stage in {"add", "add_version", "update_current_version"}
        else SqlAlchemyDiscussionHypothesisRepository
    )
    original = getattr(cls, stage)

    def fail(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise RuntimeError("injected after write")

    monkeypatch.setattr(cls, stage, fail)
    with pytest.raises(RuntimeError, match="injected"):
        service.promote_discussion_to_hypothesis(env[3], cmd)
    assert durable(env[1]) == before


@pytest.mark.parametrize(
    "change,code",
    [
        ("turn", ErrorCode.NOT_FOUND),
        ("question", ErrorCode.NOT_FOUND),
        ("transcript", ErrorCode.FROZEN_REFERENCE_REQUIRED),
        ("project", ErrorCode.FORBIDDEN),
    ],
)
def test_invalid_context_zero_delta(b03, change, code):
    service, cmd, env, *_ = b03
    before = durable(env[1])
    changed = (
        replace(cmd, project_id=uuid4())
        if change == "project"
        else replace(
            cmd,
            candidate=replace(
                cmd.candidate,
                **{
                    {
                        "turn": "turn_id",
                        "question": "research_question_version_id",
                        "transcript": "transcript_artifact_version_id",
                    }[change]: uuid4()
                },
            ),
        )
    )
    with pytest.raises(ResearchBaseError) as exc:
        service.promote_discussion_to_hypothesis(env[3], changed)
    assert exc.value.code is code
    assert durable(env[1]) == before


def test_expired_credentials_and_unverified_denied(b03):
    service, cmd, env, *_ = b03
    before = durable(env[1])
    env[2].enabled = False
    for principal, code in (
        (env[3], ErrorCode.FORBIDDEN),
        (None, ErrorCode.AUTHENTICATION_REQUIRED),
    ):
        with pytest.raises(ResearchBaseError) as exc:
            service.promote_discussion_to_hypothesis(principal, cmd)
        assert exc.value.code is code
    assert durable(env[1]) == before


def test_prior_head_upgrade_keeps_receipts_and_empty_downgrade(b03):
    _, _, env, *_ = b03
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", env[1].url.render_as_string(hide_password=False))
    before = durable(env[1])
    alembic_command.downgrade(config, "0068_b21_unresolved_capture")
    alembic_command.upgrade(config, "head")
    assert durable(env[1]) == before


@pytest.mark.parametrize("role", ["VIEWER", "REVIEWER", "APPROVER", "AGENT"])
def test_nonwriter_denied_but_human_replay_uses_read_entitlement(b03, role):
    service, cmd, env, *_ = b03
    principal = env[3]
    result = service.promote_discussion_to_hypothesis(principal, cmd)
    with env[1].begin() as c:
        if role == "AGENT":
            c.execute(
                text("UPDATE actors SET actor_type='AGENT' WHERE id=:id"),
                {"id": principal.actor_id},
            )
        else:
            # Preserve OWNER coverage by granting a second owner via the existing fixture helper.
            from datetime import UTC, datetime

            from tests.integration.phase2.test_pr2_00_ownership import _add_owner

            _add_owner(
                c,
                actor_id=uuid4(),
                project_id=cmd.project_id,
                now=datetime.now(UTC),
                event_kind="ACTIVATED",
                request_id=uuid4(),
            )
            at = c.execute(text("SELECT clock_timestamp()")).scalar_one()
            c.execute(
                text("""UPDATE project_role_assignments
                SET effective_until=:at,row_version=row_version+1
                WHERE actor_id=:id AND effective_until IS NULL"""),
                {"at": at, "id": principal.actor_id},
            )
            c.execute(
                text("""INSERT INTO project_role_assignments
                (id,membership_id,project_id,actor_id,role,effective_from,effective_until,
                 assigned_by,created_at,row_version)
                SELECT :rid,membership_id,project_id,actor_id,:role,:at,NULL,
                       assigned_by,:at,1 FROM project_role_assignments
                WHERE actor_id=:id ORDER BY effective_from DESC LIMIT 1"""),
                {"rid": uuid4(), "at": at, "role": role, "id": principal.actor_id},
            )
            for event_kind, time_column in (
                ("CLOSED", "effective_until"),
                ("ASSIGNED", "effective_from"),
            ):
                c.execute(
                    text(f"""INSERT INTO project_role_events
                    (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id)
                    SELECT :eid,id,actor_id,:kind,:at,'test role transition',:request
                    FROM project_role_assignments WHERE actor_id=:actor AND {time_column}=:at"""),
                    {
                        "eid": uuid4(),
                        "kind": event_kind,
                        "at": at,
                        "request": uuid4(),
                        "actor": principal.actor_id,
                    },
                )
    before = durable(env[1])
    with pytest.raises(ResearchBaseError) as exc:
        service.promote_discussion_to_hypothesis(
            principal,
            replace(
                cmd,
                request_id=uuid4(),
                candidate=replace(cmd.candidate, statement="different candidate"),
            ),
        )
    assert exc.value.code is ErrorCode.FORBIDDEN
    if role != "AGENT":
        assert service.promote_discussion_to_hypothesis(principal, cmd) == result
    assert durable(env[1]) == before


@pytest.mark.parametrize("closed", [False, True])
def test_open_or_unbound_session_rejected(b03, closed):
    service, cmd, env, *_ = b03
    discussion = env[0]
    session = _create(env).session_id
    turn = discussion.append(
        env[3], cmd.project_id, session, "human", "another turn", (), (), uuid4()
    ).turn_id
    if closed:
        discussion.close(env[3], cmd.project_id, session, uuid4())
    before = durable(env[1])
    with pytest.raises(ResearchBaseError) as exc:
        service.promote_discussion_to_hypothesis(
            env[3], replace(cmd, session_id=session, candidate=replace(cmd.candidate, turn_id=turn))
        )
    assert exc.value.code is ErrorCode.INVALID_STATE_TRANSITION
    assert durable(env[1]) == before


def test_expiry_after_candidate_wait_and_receipt_failure(b03, monkeypatch):
    service, cmd, env, *_ = b03
    before = durable(env[1])
    original = SqlAlchemyDiscussionHypothesisRepository.lock_candidate

    def expire(self, *args):
        original(self, *args)
        env[2].enabled = False

    monkeypatch.setattr(SqlAlchemyDiscussionHypothesisRepository, "lock_candidate", expire)
    with pytest.raises(ResearchBaseError) as exc:
        service.promote_discussion_to_hypothesis(env[3], cmd)
    assert exc.value.code is ErrorCode.FORBIDDEN
    assert durable(env[1]) == before


def test_failure_after_receipt_insert(b03, monkeypatch):
    from researchbase.persistence.discussion_repository import SqlAlchemyDiscussionRepository

    service, cmd, env, *_ = b03
    before = durable(env[1])
    original = SqlAlchemyDiscussionRepository.save_receipt

    def fail(self, *args):
        original(self, *args)
        raise RuntimeError("receipt inserted")

    monkeypatch.setattr(SqlAlchemyDiscussionRepository, "save_receipt", fail)
    with pytest.raises(RuntimeError, match="receipt inserted"):
        service.promote_discussion_to_hypothesis(env[3], cmd)
    assert durable(env[1]) == before


@pytest.mark.parametrize(
    "corruption", ["bytes", "role", "hash", "size", "question_hash", "initial_material"]
)
def test_corrupt_retained_closure_fails_read_and_replay(b03, corruption, monkeypatch):
    service, cmd, env, factory, store = b03
    result = service.promote_discussion_to_hypothesis(env[3], cmd)
    if corruption == "bytes":
        monkeypatch.setattr(store, "open", lambda digest: b"wrong bytes")
    else:
        with env[1].begin() as c:
            # Adversarial superuser corruption; rollback/restore by disposable database teardown.
            c.execute(text("SET LOCAL session_replication_role='replica'"))
            if corruption == "role":
                c.execute(
                    text(
                        "UPDATE artifacts SET artifact_type='concept_map' WHERE id="
                        "(SELECT artifact_id FROM artifact_versions WHERE id=:id)"
                    ),
                    {"id": cmd.candidate.transcript_artifact_version_id},
                )
            elif corruption in {"hash", "size"}:
                column = "content_hash" if corruption == "hash" else "byte_size"
                c.execute(
                    text(f"UPDATE artifact_versions SET {column}=:value WHERE id=:id"),
                    {
                        "value": "f" * 64 if corruption == "hash" else 1,
                        "id": cmd.candidate.transcript_artifact_version_id,
                    },
                )
            elif corruption == "question_hash":
                c.execute(
                    text("UPDATE research_question_versions SET content_hash=:hash WHERE id=:id"),
                    {"hash": "e" * 64, "id": cmd.candidate.research_question_version_id},
                )
            else:
                c.execute(
                    text(
                        "UPDATE discussion_hypothesis_admissions SET statement='tampered' "
                        "WHERE receipt_id=:id"
                    ),
                    {"id": result.receipt_id},
                )
    for action in (
        lambda: service.promote_discussion_to_hypothesis(env[3], cmd),
        lambda: service.get_discussion_hypothesis_admission(
            env[3], cmd.project_id, result.receipt_id
        ),
    ):
        with pytest.raises(ResearchBaseError) as exc:
            action()
        assert exc.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_empty_upgrade_to_head(discussion_database_url):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", discussion_database_url)
    alembic_command.downgrade(config, "base")
    alembic_command.upgrade(config, "head")
    from sqlalchemy import create_engine

    engine = create_engine(discussion_database_url)
    try:
        with engine.connect() as c:
            assert (
                c.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == "0073_b02_strategy_admission"
            )
            assert (
                c.execute(
                    text("SELECT count(*) FROM discussion_hypothesis_admissions")
                ).scalar_one()
                == 0
            )
    finally:
        engine.dispose()


discussion_database_url = _discussion_database_url
discussion_env = _discussion_env
pr219_discussion_env = _pr219_discussion_env


def test_cross_actor_same_request_is_duplicate_not_replay(b03):
    from datetime import UTC, datetime

    from tests.integration.phase2.test_m3_evidence import TechnicalCredentials
    from tests.integration.phase2.test_pr2_00_ownership import _add_owner

    service, cmd, env, factory, store = b03
    first = service.promote_discussion_to_hypothesis(env[3], cmd)
    aid = uuid4()
    with env[1].begin() as c:
        _add_owner(
            c,
            actor_id=aid,
            project_id=cmd.project_id,
            now=datetime.now(UTC),
            event_kind="ACTIVATED",
            request_id=uuid4(),
        )
    other = replace(
        env[3],
        actor_id=aid,
        deployment_id="test-deployment",
        subject_value=str(aid.int % 1_000_000),
        credential_id=f"uid:{aid.int}",
    )
    fresh = DiscussionHypothesisService(factory, TechnicalCredentials([env[3], other]), store)
    with pytest.raises(ResearchBaseError) as exc:
        fresh.promote_discussion_to_hypothesis(other, cmd)
    assert exc.value.code is ErrorCode.DUPLICATE_CONTENT
    assert (
        fresh.get_discussion_hypothesis_admission(other, cmd.project_id, first.receipt_id) == first
    )
    assert durable(env[1])[:3] == (1, 1, 1)


def test_frozen_output_and_archived_project_remain_readable(b03):
    from researchbase.domain.research import HypothesisVersionId
    from researchbase.foundation.time import SystemClock

    service, cmd, env, factory, _ = b03
    result = service.promote_discussion_to_hypothesis(env[3], cmd)
    with factory() as uow:
        version = uow.hypotheses.get_version(HypothesisVersionId(result.hypothesis_version_id))
        assert version is not None
        uow.hypotheses.update_version(version.freeze(SystemClock()), version.row_version)
        uow.commit()
    with env[1].begin() as c:
        c.execute(
            text("UPDATE projects SET lifecycle_status='ARCHIVED' WHERE id=:id"),
            {"id": cmd.project_id},
        )
    assert service.promote_discussion_to_hypothesis(env[3], cmd) == result
    assert (
        service.get_discussion_hypothesis_admission(env[3], cmd.project_id, result.receipt_id)
        == result
    )
    with pytest.raises(ResearchBaseError) as exc:
        service.promote_discussion_to_hypothesis(env[3], replace(cmd, request_id=uuid4()))
    assert exc.value.code is ErrorCode.FORBIDDEN
