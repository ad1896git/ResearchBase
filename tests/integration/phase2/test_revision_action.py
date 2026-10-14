"""TEST ONLY completed revision history on disposable real PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from uuid import uuid4

import pytest
from alembic import command as alembic_command
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError

from researchbase.application.internal_review import ReviewIssueRequest
from researchbase.application.revision_action import (
    RecordRevisionActionCommand,
    RevisionActionService,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker
from tests.integration.phase2.test_pr2_15_decision import (
    _review,
    _stale,
)
from tests.integration.phase2.test_pr2_15_decision import conclusion_env as _conclusion_env
from tests.integration.phase2.test_pr2_15_decision import decision_env as _decision_env
from tests.integration.phase2.test_pr2_15_decision import phase2_database_url as _database_url
from tests.integration.phase2.test_pr2_15_decision_schema import _config

pytestmark = pytest.mark.integration
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
conclusion_env = _conclusion_env
phase2_database_url = _database_url
decision_env = _decision_env


@pytest.fixture
def revision_env(decision_env):
    env = decision_env
    base = env[-1]
    review = _review(
        env,
        "MAJOR_REVISION",
        (ReviewIssueRequest("BLOCKING", "OVERCLAIM", "TEST ONLY correction"),),
    )
    scientific = base[0]
    revised = scientific.revise(
        base[3],
        base[5],
        env[3].conclusion_id,
        "TEST ONLY refined conclusion",
        SCOPE,
        "MODERATE",
        None,
        (),
        (),
        uuid4(),
    )
    # Empty support may be drafted but freeze requires support. Use existing claim.
    from researchbase.application.scientific_conclusion import ClaimInputRequest

    scientific.replace_inputs(
        base[3],
        base[5],
        revised.conclusion_id,
        revised.version_id,
        (ClaimInputRequest(base[6], "SUPPORTS"),),
        (),
        uuid4(),
    )
    scientific.freeze(base[3], base[5], revised.conclusion_id, revised.version_id, uuid4())
    service = RevisionActionService(base[1], base[-1], base[2])
    cmd = RecordRevisionActionCommand(
        uuid4(),
        base[5],
        "CONCLUSION_CHANGE",
        review.issues[0].id,
        result_scientific_conclusion_version_id=revised.version_id,
    )
    return service, cmd, env, review, revised


def _counts(engine):
    with engine.connect() as conn:
        return tuple(
            conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in (
                "review_issues",
                "review_issue_events",
                "internal_review_records",
                "decision_records",
                "manuscript_versions",
            )
        )


def test_completed_history_exact_replay_restart_roots_correction_and_no_resolution(revision_env):
    service, cmd, env, review, _ = revision_env
    base = env[-1]
    before = _counts(base[8])
    result = service.record_revision_action(base[3], cmd)
    assert result.content_hash and result.hash_scheme == "sha256-cjson-v1"
    assert result.provenance[0].id == review.id
    assert result.provenance[1].id == env[3].version_id
    assert result.result_validity == "VALID"
    assert not result.has_superseding_action
    assert service.record_revision_action(base[3], cmd) == result
    restarted = RevisionActionService(base[1], base[-1], base[2])
    assert restarted.read_revision_action(base[3], base[5], cmd.id) == result
    another = replace(cmd, id=uuid4())
    service.record_revision_action(base[3], another)
    correction = replace(cmd, id=uuid4(), supersedes_revision_action_id=cmd.id)
    corrected = service.record_revision_action(base[3], correction)
    assert corrected.provenance[-1].id == cmd.id
    assert service.read_revision_action(base[3], base[5], cmd.id).has_superseding_action
    with pytest.raises(ResearchBaseError) as caught:
        service.record_revision_action(base[3], replace(correction, id=uuid4()))
    assert caught.value.code == ErrorCode.INVALID_STATE_TRANSITION
    assert before == _counts(base[8])
    with base[8].connect() as conn:
        assert (
            conn.execute(
                text("SELECT status FROM review_issues WHERE id=:id"), {"id": cmd.review_issue_id}
            ).scalar_one()
            == "OPEN"
        )
        assert conn.execute(text("SELECT count(*) FROM revision_actions")).scalar_one() == 3
    with pytest.raises(ResearchBaseError) as caught:
        from tests.integration.phase2.test_pr2_15_decision import _command

        env[0].record_decision(env[2], _command(env))
    assert caught.value.code in {
        ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
        ErrorCode.FROZEN_REFERENCE_REQUIRED,
    }
    with base[1]() as uow:
        assert uow.decision.has_blockers(env[3].version_id, base[5])


@pytest.mark.parametrize(
    "case",
    [
        "old_result",
        "draft",
        "unrelated",
        "missing",
        "decision",
        "nochange",
        "actor",
        "project",
        "replay_payload",
        "self",
        "reparent",
    ],
)
def test_denied_paths_atomic(revision_env, case):
    service, cmd, env, review, _ = revision_env
    base = env[-1]
    actor = base[3]
    if case in {"actor", "replay_payload"}:
        service.record_revision_action(actor, cmd)
    if case == "old_result":
        cmd = replace(cmd, result_scientific_conclusion_version_id=env[3].version_id)
    elif case in {"draft", "unrelated"}:
        from researchbase.application.scientific_conclusion import ClaimInputRequest

        target = base[0].create(
            actor,
            base[5],
            "TEST ONLY unrelated",
            SCOPE,
            "MODERATE",
            None,
            (ClaimInputRequest(base[6], "SUPPORTS"),),
            (),
            uuid4(),
        )
        if case == "unrelated":
            base[0].freeze(actor, base[5], target.conclusion_id, target.version_id, uuid4())
        cmd = replace(cmd, result_scientific_conclusion_version_id=target.version_id)
    elif case == "missing":
        cmd = replace(cmd, review_issue_id=uuid4())
    elif case == "decision":
        cmd = replace(cmd, decision_record_id=uuid4())
    elif case == "nochange":
        cmd = replace(cmd, action_type="NO_CHANGE", result_scientific_conclusion_version_id=None)
    elif case == "actor":
        actor = env[2]
    elif case == "project":
        cmd = replace(cmd, project_id=uuid4())
    elif case == "replay_payload":
        cmd = replace(cmd, review_issue_id=uuid4())
    elif case == "self":
        cmd = replace(cmd, supersedes_revision_action_id=cmd.id)
    elif case == "reparent":
        previous = service.record_revision_action(actor, cmd)
        other = _review(
            env, "MAJOR_REVISION", (ReviewIssueRequest("MINOR", "OTHER", "Other"),), "COMPREHENSIVE"
        )
        cmd = replace(
            cmd,
            id=uuid4(),
            review_issue_id=other.issues[0].id,
            supersedes_revision_action_id=previous.id,
        )
    before = _counts(base[8])
    with pytest.raises(ResearchBaseError):
        service.record_revision_action(actor, cmd)
    assert _counts(base[8]) == before


def test_later_stale_historical_replay_but_new_admission_denied(revision_env):
    service, cmd, env, _, _ = revision_env
    base = env[-1]
    prior = service.record_revision_action(base[3], cmd)
    _stale(env)
    replay = service.record_revision_action(base[3], cmd)
    assert replay.content_hash == prior.content_hash
    assert replay.result_validity == "STALE"
    assert replay.target_validity == "STALE"
    assert service.read_revision_action(base[3], base[5], cmd.id) == replay
    with pytest.raises(ResearchBaseError) as caught:
        service.record_revision_action(base[3], replace(cmd, id=uuid4()))
    assert caught.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_same_uuid_and_nonforking_correction_concurrency(revision_env):
    service, cmd, env, _, _ = revision_env
    actor = env[-1][3]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: service.record_revision_action(actor, cmd), range(2)))
    assert results[0] == results[1]

    def correct(_):
        try:
            return service.record_revision_action(
                actor, replace(cmd, id=uuid4(), supersedes_revision_action_id=cmd.id)
            )
        except ResearchBaseError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(correct, range(2)))
    assert sum(outcome == ErrorCode.INVALID_STATE_TRANSITION for outcome in outcomes) == 1
    with env[-1][8].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM revision_actions")).scalar_one() == 2


def test_observed_target_wait_rechecks_credentials(revision_env):
    service, cmd, env, _, _ = revision_env
    base = env[-1]
    with ThreadPoolExecutor(max_workers=1) as pool:
        with base[8].begin() as holder:
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            holder.execute(
                text("SELECT id FROM scientific_conclusion_versions WHERE id=:id FOR UPDATE"),
                {"id": env[3].version_id},
            )
            pending = pool.submit(service.record_revision_action, base[3], cmd)
            witness = _wait_for_pg_blocker(base[8], pid, "transactionid")
            assert "scientific_conclusion_versions" in witness["query"]
            base[-1].enabled = False
        with pytest.raises(ResearchBaseError) as caught:
            pending.result(timeout=10)
        assert caught.value.code == ErrorCode.FORBIDDEN
    with base[8].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM revision_actions")).scalar_one() == 0


def test_midwrite_rollback_then_exact_uuid_recovery(revision_env):
    service, cmd, env, _, _ = revision_env
    base = env[-1]

    def fail(conn, cursor, statement, params, context, many):
        if statement.startswith("INSERT INTO revision_actions"):
            raise ResearchBaseError(ErrorCode.INVALID_STATE_TRANSITION, "TEST ONLY failure")

    event.listen(base[8], "after_cursor_execute", fail)
    try:
        with pytest.raises(ResearchBaseError):
            service.record_revision_action(base[3], cmd)
    finally:
        event.remove(base[8], "after_cursor_execute", fail)
    with base[8].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM revision_actions")).scalar_one() == 0
    assert service.record_revision_action(base[3], cmd).id == cmd.id


def test_catalog_immutable_sql_and_refused_downgrade(revision_env, phase2_database_url):
    service, cmd, env, _, _ = revision_env
    base = env[-1]
    service.record_revision_action(base[3], cmd)
    with base[8].connect() as conn:
        fks = (
            conn.execute(
                text("""SELECT confdeltype FROM pg_constraint
            WHERE conrelid='revision_actions'::regclass AND contype='f'""")
            )
            .scalars()
            .all()
        )
        assert len(fks) == 11 and set(fks) == {"r"}
        columns = set(
            conn.execute(
                text("""SELECT column_name FROM information_schema.columns
            WHERE table_name='revision_actions'""")
            ).scalars()
        )
        assert len(columns) == 16 and "project_id" not in columns
    for sql in (
        "UPDATE revision_actions SET content_hash=content_hash WHERE id=:id",
        "DELETE FROM revision_actions WHERE id=:id",
    ):
        with pytest.raises(DBAPIError) as caught, base[8].begin() as conn:
            conn.execute(text(sql), {"id": cmd.id})
        assert getattr(caught.value.orig, "sqlstate", None) == "P17F1"
    with pytest.raises(DBAPIError):
        alembic_command.downgrade(_config(phase2_database_url), "0043_pr2_04_schema_contract")
    assert service.read_revision_action(base[3], base[5], cmd.id).id == cmd.id


def test_claim_change_exact_successor(revision_env, tmp_path):
    from uuid import UUID

    from researchbase.application.commands import (
        FreezeClaimVersionCommand,
        LinkEvidenceCommand,
        ReviseClaimCommand,
    )
    from researchbase.domain.claim import ClaimVersionId
    from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock
    from tests.application_compat import LegacyApplicationService

    service, _, env, _, _ = revision_env
    base = env[-1]
    old_id = ClaimVersionId(base[6])
    review = env[1].create(
        env[2],
        base[5],
        "CLAIM_VERSION",
        base[6],
        "SCIENTIFIC",
        "MAJOR_REVISION",
        "TEST ONLY claim correction",
        (ReviewIssueRequest("MAJOR", "OTHER", "TEST ONLY"),),
        uuid4(),
    )
    app = LegacyApplicationService(
        base[1], SystemClock(), ContentAddressedFilesystemArtifactStore(tmp_path / "cas")
    )
    old = app.get_claim_version(old_id)
    parent = app.get_claim(old.claim_id)
    context = ExecutionContext(actor_id=base[3].actor_id, request_id=uuid4(), client_type="test")
    evidence = app.list_evidence_relations(old_id)[0]
    revised = app.revise_claim(
        ReviseClaimCommand(
            parent.id, "TEST ONLY corrected statement", {}, None, parent.row_version, context
        )
    )
    draft = app.get_current_claim_version(revised.id)
    app.link_evidence(
        LinkEvidenceCommand(
            revised.id,
            draft.id,
            evidence.measurement_id,
            evidence.statistical_result_id,
            "supports",
            None,
            draft.row_version,
            context,
        )
    )
    draft = app.get_current_claim_version(revised.id)
    frozen = app.freeze_claim_version(
        FreezeClaimVersionCommand(revised.id, draft.id, context, draft.row_version)
    )
    cmd = RecordRevisionActionCommand(
        uuid4(),
        base[5],
        "CLAIM_CHANGE",
        review.issues[0].id,
        result_claim_version_id=UUID(str(frozen.id)),
    )
    from threading import Event

    entered, release = Event(), Event()
    holder_pid = []

    def pause_old_target(conn, cursor, statement, parameters, context, many):
        if (
            "FROM claim_versions" in statement
            and "FOR UPDATE" in statement
            and parameters.get("id") == base[6]
        ):
            holder_pid.append(conn.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(10)

    def invalid_writer():
        with base[8].begin() as conn:
            conn.execute(
                text("UPDATE claim_versions SET statement='TEST ONLY forbidden edit' WHERE id=:id"),
                {"id": base[6]},
            )

    event.listen(base[8], "after_cursor_execute", pause_old_target)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            recording = pool.submit(service.record_revision_action, base[3], cmd)
            assert entered.wait(10)
            writer = pool.submit(invalid_writer)
            witness = _wait_for_pg_blocker(base[8], holder_pid[0], "transactionid")
            assert "UPDATE claim_versions" in witness["query"]
            release.set()
            result = recording.result(timeout=10)
            with pytest.raises(DBAPIError):
                writer.result(timeout=10)
    finally:
        release.set()
        event.remove(base[8], "after_cursor_execute", pause_old_target)
    assert result.result_claim_version_id == frozen.id
    assert result.provenance[1].id == base[6]
    assert service.read_revision_action(base[3], base[5], result.id) == result


@pytest.mark.parametrize("sqlstate", ["40001", "40P01"])
def test_aborted_retry_and_sanitized_driver_errors(revision_env, sqlstate):
    service, cmd, env, _, _ = revision_env
    base = env[-1]
    attempts = []

    def factory():
        uow = base[1]()
        attempts.append(uow)
        return uow

    def inject(conn, cursor, statement, parameters, context, many):
        if statement.startswith("INSERT INTO revision_actions") and len(attempts) == 1:
            conn.execute(
                text(
                    f"DO $$ BEGIN RAISE EXCEPTION 'TEST ONLY SECRET' "
                    f"USING ERRCODE='{sqlstate}'; END $$"
                )
            )

    event.listen(base[8], "before_cursor_execute", inject)
    try:
        retrying = RevisionActionService(factory, base[-1], base[2])
        result = retrying.record_revision_action(base[3], cmd)
    finally:
        event.remove(base[8], "before_cursor_execute", inject)
    assert len(attempts) == 2
    assert service.record_revision_action(base[3], cmd) == result


def test_commit_acknowledgement_loss_recovers_saved_uuid(revision_env):
    from psycopg import OperationalError
    from sqlalchemy.exc import OperationalError as SqlOperationalError

    service, cmd, env, _, _ = revision_env
    base = env[-1]

    def factory():
        uow = base[1]()
        commit = uow.commit

        def uncertain_commit():
            commit()
            raise SqlOperationalError(None, None, OperationalError("TEST ONLY SECRET ack loss"))

        uow.commit = uncertain_commit
        return uow

    uncertain = RevisionActionService(factory, base[-1], base[2])
    with pytest.raises(ResearchBaseError) as caught:
        uncertain.record_revision_action(base[3], cmd)
    assert "SECRET" not in str(caught.value.to_dict())
    assert service.record_revision_action(base[3], cmd).id == cmd.id
    with base[8].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM revision_actions")).scalar_one() == 1


def test_empty_additive_upgrade_downgrade_preserves_predecessor_catalog(phase2_database_url):
    from alembic.script import ScriptDirectory
    from sqlalchemy import create_engine

    from tests.integration.phase2.test_pr2_15_decision_schema import _catalog, _tables

    config = _config(phase2_database_url)
    engine = create_engine(phase2_database_url)
    try:
        alembic_command.upgrade(config, "0043_pr2_04_schema_contract")
        with engine.connect() as conn:
            tables = _tables(conn)
            catalog = _catalog(conn, tables)
        alembic_command.upgrade(config, "head")
        with engine.connect() as conn:
            assert _tables(conn) - tables == {"revision_actions"}
            assert _catalog(conn, tables) == catalog
        assert ScriptDirectory.from_config(config).get_heads() == ["0044_pr2_15_revision_action"]
        alembic_command.downgrade(config, "0043_pr2_04_schema_contract")
        with engine.connect() as conn:
            assert _tables(conn) == tables and _catalog(conn, tables) == catalog
        alembic_command.upgrade(config, "head")
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "mutation",
    [
        "empty_basis",
        "same_result",
        "draft",
        "extra",
        "decision",
        "nochange",
        "hash",
        "scheme",
        "self",
        "reparent",
        "fork",
    ],
)
def test_normal_role_sql_guards(revision_env, mutation):
    service, cmd, env, _, _ = revision_env
    base = env[-1]
    result = service.record_revision_action(base[3], cmd)
    actor = base[3].actor_id
    assignments = {"id": ":new_id", "created_at": "clock_timestamp()"}
    if mutation == "empty_basis":
        assignments["review_issue_id"] = "NULL"
    elif mutation == "same_result":
        assignments["result_scientific_conclusion_version_id"] = ":old_id"
    elif mutation == "draft":
        draft = base[0].revise(
            base[3],
            base[5],
            env[3].conclusion_id,
            "TEST ONLY draft",
            SCOPE,
            "MODERATE",
            None,
            (),
            (),
            uuid4(),
        )
        assignments["result_scientific_conclusion_version_id"] = ":draft_id"
    elif mutation == "extra":
        assignments["result_claim_version_id"] = ":claim_id"
    elif mutation == "decision":
        assignments["decision_record_id"] = ":new_id"
    elif mutation == "nochange":
        assignments.update(
            action_type="'NO_CHANGE'", result_scientific_conclusion_version_id="NULL"
        )
    elif mutation == "hash":
        assignments["content_hash"] = "repeat('X',64)"
    elif mutation == "scheme":
        assignments["hash_scheme"] = "'invalid'"
    elif mutation == "self":
        assignments["supersedes_revision_action_id"] = ":new_id"
    elif mutation == "reparent":
        other = _review(
            env,
            "MAJOR_REVISION",
            (ReviewIssueRequest("MINOR", "OTHER", "TEST ONLY"),),
            "COMPREHENSIVE",
        )
        assignments.update(review_issue_id=":other_issue", supersedes_revision_action_id=":id")
    elif mutation == "fork":
        service.record_revision_action(
            base[3], replace(cmd, id=uuid4(), supersedes_revision_action_id=result.id)
        )
        assignments["supersedes_revision_action_id"] = ":id"
    with base[8].connect() as conn:
        columns = list(
            conn.execute(
                text("""SELECT column_name FROM information_schema.columns
            WHERE table_name='revision_actions' ORDER BY ordinal_position""")
            ).scalars()
        )
    role = "task13_normal_" + uuid4().hex
    # Transaction-local role is rolled back with the denied write; no retained role.
    with pytest.raises(DBAPIError), base[8].begin() as conn:
        conn.execute(text(f"CREATE ROLE {role} NOLOGIN NOSUPERUSER"))
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        conn.execute(
            text(f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {role}")
        )
        conn.execute(text(f"SET LOCAL ROLE {role}"))
        assert not conn.execute(
            text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")
        ).scalar_one()
        selection = ",".join(assignments.get(str(key), str(key)) for key in columns)
        conn.execute(
            text(
                f"INSERT INTO revision_actions ({','.join(columns)}) SELECT {selection} "
                "FROM revision_actions WHERE id=:id"
            ),
            {
                "id": cmd.id,
                "new_id": uuid4(),
                "old_id": env[3].version_id,
                "claim_id": base[6],
                "draft_id": draft.version_id if mutation == "draft" else None,
                "other_issue": other.issues[0].id if mutation == "reparent" else None,
                "actor": actor,
            },
        )


def test_replay_after_write_loss_and_read_loss(revision_env):
    from researchbase.application.phase2_identity import AssignProjectRole, CloseProjectRole
    from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service

    service, cmd, env, _, _ = revision_env
    base = env[-1]
    actor = env[2]
    saved = service.record_revision_action(actor, cmd)
    identity, _, _ = identity_service(str(base[8].url))
    identity.assign_project_role(
        AssignProjectRole(actor, base[5], actor.actor_id, "VIEWER", "TEST ONLY read", uuid4())
    )
    with base[8].connect() as conn:
        role = conn.execute(
            text("""SELECT id FROM project_role_assignments WHERE actor_id=:actor
            AND project_id=:project AND role='OWNER' AND effective_until IS NULL"""),
            {"actor": actor.actor_id, "project": base[5]},
        ).scalar_one()
    identity.close_project_role(
        CloseProjectRole(base[3], base[5], role, "TEST ONLY write loss", uuid4())
    )
    assert service.record_revision_action(actor, cmd) == saved
    with pytest.raises(ResearchBaseError):
        service.record_revision_action(actor, replace(cmd, id=uuid4()))
    with base[8].connect() as conn:
        viewer = conn.execute(
            text("""SELECT id FROM project_role_assignments WHERE actor_id=:actor
            AND project_id=:project AND role='VIEWER' AND effective_until IS NULL"""),
            {"actor": actor.actor_id, "project": base[5]},
        ).scalar_one()
    identity.close_project_role(
        CloseProjectRole(base[3], base[5], viewer, "TEST ONLY read loss", uuid4())
    )
    with pytest.raises(ResearchBaseError) as caught:
        service.record_revision_action(actor, cmd)
    assert caught.value.code == ErrorCode.FORBIDDEN


def test_attributable_researcher_uses_same_boundary(revision_env):
    from researchbase.application.phase2_identity import AssignProjectRole, CloseProjectRole
    from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service

    service, cmd, env, _, _ = revision_env
    base = env[-1]
    actor = env[2]
    identity, _, _ = identity_service(str(base[8].url))
    identity.assign_project_role(
        AssignProjectRole(
            actor, base[5], actor.actor_id, "RESEARCHER", "TEST ONLY researcher", uuid4()
        )
    )
    with base[8].connect() as conn:
        role = conn.execute(
            text("""SELECT id FROM project_role_assignments WHERE actor_id=:actor
            AND project_id=:project AND role='OWNER' AND effective_until IS NULL"""),
            {"actor": actor.actor_id, "project": base[5]},
        ).scalar_one()
    identity.close_project_role(CloseProjectRole(base[3], base[5], role, "TEST ONLY role", uuid4()))
    result = service.record_revision_action(actor, cmd)
    assert result.created_by == actor.actor_id
    assert service.record_revision_action(actor, cmd) == result
    with pytest.raises(ResearchBaseError):
        service.record_revision_action(base[3], cmd)


def test_agent_without_existing_verified_binding_fails_closed(revision_env):
    service, cmd, env, _, _ = revision_env
    base = env[-1]
    identity = uuid4()
    with base[8].begin() as conn:
        now = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        conn.execute(
            text("""INSERT INTO actors (id,actor_type,display_name,created_at)
            VALUES (:id,'AGENT','TEST ONLY agent',:at)"""),
            {"id": identity, "at": now},
        )
    actor = replace(
        base[3],
        actor_id=identity,
        subject_value=str(identity.int % 1_000_000),
        credential_id=f"uid:{identity.int}",
    )
    base[-1].principals[identity] = actor
    with pytest.raises(ResearchBaseError) as caught:
        service.record_revision_action(actor, cmd)
    assert caught.value.code == ErrorCode.FORBIDDEN


@pytest.mark.parametrize("order", ["validity_first", "action_first"])
def test_validity_writer_commit_orders_have_actual_lock_witness(revision_env, order):
    service, cmd, env, _, _ = revision_env
    base = env[-1]
    if order == "validity_first":
        from threading import Event

        entered = Event()
        release = Event()

        def pause(conn, cursor, statement, parameters, context, many):
            if statement.lstrip().upper().startswith("INSERT INTO IMPACT_TARGETS"):
                entered.set()
                assert release.wait(10)

        event.listen(base[8], "after_cursor_execute", pause)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                stale = pool.submit(_stale, env)
                assert entered.wait(10)
                with base[8].connect() as conn:
                    pid = conn.execute(
                        text("""SELECT pid FROM pg_stat_activity
                        WHERE datname=current_database() AND state='idle in transaction'
                        AND query ILIKE 'INSERT INTO impact_targets%%'""")
                    ).scalar_one()
                pending = pool.submit(service.record_revision_action, base[3], cmd)
                witness = _wait_for_pg_blocker(base[8], pid, "relation")
                assert "LOCK TABLE" in witness["query"]
                release.set()
                stale.result(timeout=10)
                with pytest.raises(ResearchBaseError) as caught:
                    pending.result(timeout=10)
                assert caught.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
        finally:
            release.set()
            event.remove(base[8], "after_cursor_execute", pause)
    else:
        from threading import Event

        entered = Event()
        release = Event()

        def pause(conn, cursor, statement, parameters, context, many):
            if statement.startswith("INSERT INTO revision_actions"):
                entered.set()
                assert release.wait(10)

        event.listen(base[8], "after_cursor_execute", pause)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                action = pool.submit(service.record_revision_action, base[3], cmd)
                assert entered.wait(10)
                with base[8].connect() as conn:
                    pid = conn.execute(
                        text("""SELECT pid FROM pg_stat_activity WHERE datname=current_database()
                        AND query LIKE 'INSERT INTO revision_actions%%'
                        AND state='idle in transaction'""")
                    ).scalar_one()
                stale = pool.submit(_stale, env)
                witness = _wait_for_pg_blocker(base[8], pid, "relation")
                assert "audit_findings" in witness["query"]
                release.set()
                saved = action.result(timeout=10)
                stale.result(timeout=10)
        finally:
            release.set()
            event.remove(base[8], "after_cursor_execute", pause)
        assert service.record_revision_action(base[3], cmd).content_hash == saved.content_hash


def test_role_change_first_observed_snapshot_wait_denies(revision_env):
    service, cmd, env, _, _ = revision_env
    base = env[-1]
    actor = env[2]
    with base[8].connect() as conn:
        role = conn.execute(
            text("""SELECT id FROM project_role_assignments WHERE actor_id=:actor
            AND project_id=:project AND role='OWNER' AND effective_until IS NULL"""),
            {"actor": actor.actor_id, "project": base[5]},
        ).scalar_one()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with base[8].begin() as holder:
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            at = holder.execute(
                text("""UPDATE project_role_assignments
                SET effective_until=clock_timestamp(),row_version=row_version+1
                WHERE id=:id RETURNING effective_until"""),
                {"id": role},
            ).scalar_one()
            holder.execute(
                text("""INSERT INTO project_role_events
                (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id)
                VALUES (:id,:role,:actor,'CLOSED',:at,'TEST ONLY revocation',:request)"""),
                {
                    "id": uuid4(),
                    "role": role,
                    "actor": actor.actor_id,
                    "at": at,
                    "request": uuid4(),
                },
            )
            pending = pool.submit(service.record_revision_action, actor, cmd)
            witness = _wait_for_pg_blocker(base[8], pid, "relation")
            assert "LOCK TABLE" in witness["query"]
        with pytest.raises(ResearchBaseError) as caught:
            pending.result(timeout=10)
        assert caught.value.code == ErrorCode.FORBIDDEN


@pytest.mark.parametrize(
    "table,column",
    [
        ("revision_actions", "content_hash"),
        ("internal_review_records", "content_hash"),
        ("scientific_conclusion_versions", "content_hash"),
    ],
)
def test_privileged_storage_corruption_fails_historical_verification(revision_env, table, column):
    service, cmd, env, review, _ = revision_env
    base = env[-1]
    service.record_revision_action(base[3], cmd)
    identity = (
        cmd.id
        if table == "revision_actions"
        else review.id
        if table == "internal_review_records"
        else cmd.result_scientific_conclusion_version_id
    )
    # Explicit privileged corruption fixture, never a production mutation path.
    with base[8].begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER USER"))
        conn.execute(
            text(f"UPDATE {table} SET {column}=:digest WHERE id=:id"),
            {"id": identity, "digest": "0" * 64},
        )
        conn.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER USER"))
    with pytest.raises(ResearchBaseError) as caught:
        service.read_revision_action(base[3], base[5], cmd.id)
    assert caught.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    with pytest.raises(ResearchBaseError):
        service.record_revision_action(
            base[3], replace(cmd, id=uuid4(), supersedes_revision_action_id=cmd.id)
        )


def test_exact_hash_unauthorized_review_is_not_admitted_as_basis(revision_env):
    service, cmd, env, review, _ = revision_env
    base = env[-1]
    outsider = uuid4()
    review_id = uuid4()
    issue = uuid4()
    with base[8].begin() as conn:
        conn.execute(
            text("""INSERT INTO actors (id,actor_type,display_name,created_at)
            VALUES (:id,'HUMAN','TEST ONLY no project reviewer',clock_timestamp())"""),
            {"id": outsider},
        )
        digest = env[1]._hash(
            base[5],
            "ScientificConclusionVersion",
            env[3].version_id,
            review.target_content_hash,
            outsider,
            "SCIENTIFIC",
            "MAJOR_REVISION",
            "TEST ONLY forged authority",
        )
        conn.execute(
            text("""INSERT INTO internal_review_records
            (id,project_id,scientific_conclusion_version_id,target_content_hash,reviewer_actor_id,
             review_type,recommendation,summary,created_at,content_hash,hash_scheme)
            VALUES (:id,:project,:target,:hash,:actor,'SCIENTIFIC','MAJOR_REVISION',
                    'TEST ONLY forged authority',clock_timestamp(),:digest,'sha256-cjson-v1')"""),
            {
                "id": review_id,
                "project": base[5],
                "target": env[3].version_id,
                "hash": review.target_content_hash,
                "actor": outsider,
                "digest": digest,
            },
        )
        conn.execute(
            text("""INSERT INTO review_issues
            (id,review_record_id,severity,issue_type,description,status,created_at,ordinal)
            VALUES (:id,:review,'MAJOR','OTHER','TEST ONLY','OPEN',clock_timestamp(),0)"""),
            {"id": issue, "review": review_id},
        )
    with pytest.raises(ResearchBaseError) as caught:
        service.record_revision_action(base[3], replace(cmd, review_issue_id=issue))
    assert caught.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_normal_role_immutable_history(revision_env, operation):
    service, cmd, env, _, _ = revision_env
    base = env[-1]
    service.record_revision_action(base[3], cmd)
    role = "task13_normal_" + uuid4().hex
    with pytest.raises(DBAPIError) as caught, base[8].begin() as conn:
        conn.execute(text(f"CREATE ROLE {role} NOLOGIN NOSUPERUSER"))
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        conn.execute(text(f"GRANT SELECT,UPDATE,DELETE ON revision_actions TO {role}"))
        conn.execute(text(f"SET LOCAL ROLE {role}"))
        sql = (
            "UPDATE revision_actions SET action_type=action_type WHERE id=:id"
            if operation == "UPDATE"
            else "DELETE FROM revision_actions WHERE id=:id"
        )
        conn.execute(text(sql), {"id": cmd.id})
    assert getattr(caught.value.orig, "sqlstate", None) == "P17F1"


def test_observed_correction_overlap_is_nonforking(revision_env):
    from threading import Event

    service, cmd, env, _, _ = revision_env
    base = env[-1]
    service.record_revision_action(base[3], cmd)
    first = replace(cmd, id=uuid4(), supersedes_revision_action_id=cmd.id)
    second = replace(first, id=uuid4())
    entered, release = Event(), Event()

    def pause(conn, cursor, statement, parameters, context, many):
        if (
            statement.startswith("INSERT INTO revision_actions")
            and parameters.get("id") == first.id
        ):
            entered.set()
            assert release.wait(10)

    event.listen(base[8], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            winner = pool.submit(service.record_revision_action, base[3], first)
            assert entered.wait(10)
            with base[8].connect() as conn:
                pid = conn.execute(
                    text("""SELECT pid FROM pg_stat_activity WHERE datname=current_database()
                    AND query LIKE 'INSERT INTO revision_actions%%'
                        AND state='idle in transaction'""")
                ).scalar_one()
            loser = pool.submit(service.record_revision_action, base[3], second)
            witness = _wait_for_pg_blocker(base[8], pid, "transactionid")
            assert "scientific_conclusion_versions" in witness["query"]
            release.set()
            assert winner.result(timeout=10).id == first.id
            with pytest.raises(ResearchBaseError) as caught:
                loser.result(timeout=10)
            assert caught.value.code == ErrorCode.INVALID_STATE_TRANSITION
    finally:
        release.set()
        event.remove(base[8], "after_cursor_execute", pause)


def test_role_writer_after_recording_waits_then_revokes(revision_env):
    from threading import Event

    from researchbase.application.phase2_identity import CloseProjectRole
    from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service

    service, cmd, env, _, _ = revision_env
    base = env[-1]
    actor = env[2]
    identity, _, _ = identity_service(str(base[8].url))
    with base[8].connect() as conn:
        role = conn.execute(
            text("""SELECT id FROM project_role_assignments WHERE actor_id=:actor
            AND project_id=:project AND role='OWNER' AND effective_until IS NULL"""),
            {"actor": actor.actor_id, "project": base[5]},
        ).scalar_one()
    entered, release = Event(), Event()

    def pause(conn, cursor, statement, parameters, context, many):
        if statement.startswith("INSERT INTO revision_actions"):
            entered.set()
            assert release.wait(10)

    event.listen(base[8], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            recording = pool.submit(service.record_revision_action, actor, cmd)
            assert entered.wait(10)
            with base[8].connect() as conn:
                pid = conn.execute(
                    text("""SELECT pid FROM pg_stat_activity WHERE datname=current_database()
                    AND query LIKE 'INSERT INTO revision_actions%%'
                        AND state='idle in transaction'""")
                ).scalar_one()
            revoking = pool.submit(
                identity.close_project_role,
                CloseProjectRole(base[3], base[5], role, "TEST ONLY later", uuid4()),
            )
            witness = _wait_for_pg_blocker(base[8], pid, "relation")
            assert witness["pid"] != pid
            release.set()
            assert recording.result(timeout=10).id == cmd.id
            revoking.result(timeout=10)
    finally:
        release.set()
        event.remove(base[8], "after_cursor_execute", pause)
    with pytest.raises(ResearchBaseError):
        service.record_revision_action(actor, cmd)
    assert service.read_revision_action(base[3], base[5], cmd.id).created_by == actor.actor_id


def test_request_wait_rechecks_scheduled_role_expiry(revision_env):
    service, cmd, env, _, _ = revision_env
    base = env[-1]
    actor = env[2]
    with base[8].begin() as conn:
        role, until = conn.execute(
            text("""UPDATE project_role_assignments SET
            effective_until=clock_timestamp()+interval '3 seconds',row_version=row_version+1
            WHERE actor_id=:actor AND project_id=:project AND role='OWNER'
            AND effective_until IS NULL RETURNING id,effective_until"""),
            {"actor": actor.actor_id, "project": base[5]},
        ).one()
        conn.execute(
            text("""INSERT INTO project_role_events
            (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id)
            VALUES (:id,:role,:actor,'CLOSED',:until,'TEST ONLY expiry',:request)"""),
            {
                "id": uuid4(),
                "role": role,
                "actor": actor.actor_id,
                "until": until,
                "request": uuid4(),
            },
        )
    with ThreadPoolExecutor(max_workers=1) as pool:
        with base[8].begin() as holder:
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            holder.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                {"key": f"pr215:revision:{cmd.id}"},
            )
            pending = pool.submit(service.record_revision_action, actor, cmd)
            before = _wait_for_pg_blocker(base[8], pid, "advisory")
            assert before["observed_at"] < until
            holder.execute(
                text(
                    "SELECT pg_sleep(GREATEST(0,"
                    "EXTRACT(EPOCH FROM (:until-clock_timestamp()))+0.1))"
                ),
                {"until": until},
            )
            after = _wait_for_pg_blocker(base[8], pid, "advisory")
            assert after["pid"] == before["pid"] and after["observed_at"] >= until
        with pytest.raises(ResearchBaseError) as caught:
            pending.result(timeout=10)
        assert caught.value.code == ErrorCode.FORBIDDEN


def test_normal_sql_review_writer_waits_for_revision_without_lock_inversion(revision_env):
    from threading import Event

    service, cmd, env, review, _ = revision_env
    base = env[-1]
    entered, release = Event(), Event()

    def pause(conn, cursor, statement, parameters, context, many):
        if statement.startswith("INSERT INTO revision_actions"):
            entered.set()
            assert release.wait(10)

    def insert_review():
        role = "task13_normal_" + uuid4().hex
        with base[8].begin() as conn:
            conn.execute(text(f"CREATE ROLE {role} NOLOGIN NOSUPERUSER"))
            conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
            conn.execute(
                text(f"GRANT SELECT,INSERT,UPDATE ON ALL TABLES IN SCHEMA public TO {role}")
            )
            conn.execute(text(f"SET LOCAL ROLE {role}"))
            conn.execute(
                text("""INSERT INTO internal_review_records
                (id,project_id,claim_version_id,scientific_conclusion_version_id,target_content_hash,
                 reviewer_actor_id,review_type,recommendation,summary,created_at,content_hash,hash_scheme)
                SELECT :id,project_id,claim_version_id,scientific_conclusion_version_id,
                 target_content_hash,
                 reviewer_actor_id,review_type,recommendation,summary,clock_timestamp(),
                 content_hash,hash_scheme
                FROM internal_review_records WHERE id=:review"""),
                {"id": uuid4(), "review": review.id},
            )
            conn.execute(text("RESET ROLE"))
            conn.execute(text(f"DROP OWNED BY {role}"))
            conn.execute(text(f"DROP ROLE {role}"))

    event.listen(base[8], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            action = pool.submit(service.record_revision_action, base[3], cmd)
            assert entered.wait(10)
            with base[8].connect() as conn:
                pid = conn.execute(
                    text("""SELECT pid FROM pg_stat_activity WHERE datname=current_database()
                    AND query LIKE 'INSERT INTO revision_actions%%'
                    AND state='idle in transaction'""")
                ).scalar_one()
            writer = pool.submit(insert_review)
            witness = _wait_for_pg_blocker(base[8], pid, "transactionid")
            assert "INSERT INTO internal_review_records" in witness["query"]
            release.set()
            assert action.result(timeout=10).id == cmd.id
            writer.result(timeout=10)
    finally:
        release.set()
        event.remove(base[8], "after_cursor_execute", pause)


def test_foreign_predecessor_state_is_nondisclosing(revision_env, tmp_path):
    from uuid import UUID

    from researchbase.application.commands import (
        FreezeClaimVersionCommand,
        LinkEvidenceCommand,
        ReviseClaimCommand,
    )
    from researchbase.domain.organization import ProjectId
    from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock
    from tests.application_compat import LegacyApplicationService
    from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service
    from tests.integration.test_pr12_application import seed_claim, seed_measurement

    service, cmd, env, _, _ = revision_env
    base = env[-1]
    identity, _, _ = identity_service(str(base[8].url))
    project = identity.create_project_with_owner(
        base[3], name="TEST ONLY foreign", request_id=uuid4()
    )
    from tests.integration.phase2.test_pr2_00_ownership import _add_owner

    reviewer_id = uuid4()
    with base[8].begin() as conn:
        _add_owner(
            conn,
            actor_id=reviewer_id,
            project_id=project,
            now=conn.execute(text("SELECT clock_timestamp()")).scalar_one(),
            event_kind="ACTIVATED",
            request_id=uuid4(),
        )
    reviewer = replace(
        env[2],
        actor_id=reviewer_id,
        subject_value=str(reviewer_id.int % 1_000_000),
        credential_id=f"uid:{reviewer_id.int}",
    )
    base[-1].principals[reviewer_id] = reviewer
    app = LegacyApplicationService(
        base[1], SystemClock(), ContentAddressedFilesystemArtifactStore(tmp_path / "foreign-cas")
    )
    context = ExecutionContext(actor_id=base[3].actor_id, request_id=uuid4(), client_type="test")
    measurement = seed_measurement(app, ProjectId(project), context, "foreign")
    claim, draft = seed_claim(app, ProjectId(project), context)
    app.link_evidence(
        LinkEvidenceCommand(
            claim.id, draft.id, measurement, None, "supports", None, draft.row_version, context
        )
    )
    draft = app.get_current_claim_version(claim.id)
    old = app.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, draft.id, context, draft.row_version)
    )
    review = env[1].create(
        reviewer,
        project,
        "CLAIM_VERSION",
        UUID(str(old.id)),
        "SCIENTIFIC",
        "MAJOR_REVISION",
        "TEST ONLY foreign review",
        (ReviewIssueRequest("MAJOR", "OTHER", "TEST ONLY"),),
        uuid4(),
    )
    parent = app.get_claim(claim.id)
    app.revise_claim(
        ReviseClaimCommand(
            parent.id, "TEST ONLY foreign successor", {}, None, parent.row_version, context
        )
    )
    draft = app.get_current_claim_version(claim.id)
    app.link_evidence(
        LinkEvidenceCommand(
            claim.id, draft.id, measurement, None, "supports", None, draft.row_version, context
        )
    )
    draft = app.get_current_claim_version(claim.id)
    new = app.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, draft.id, context, draft.row_version)
    )
    foreign = RecordRevisionActionCommand(
        uuid4(),
        project,
        "CLAIM_CHANGE",
        review.issues[0].id,
        result_claim_version_id=UUID(str(new.id)),
    )
    service.record_revision_action(base[3], foreign)

    def denied(predecessor):
        with pytest.raises(ResearchBaseError) as caught:
            service.record_revision_action(
                base[3], replace(cmd, supersedes_revision_action_id=predecessor)
            )
        assert caught.value.code == ErrorCode.FORBIDDEN
        return caught.value.message

    missing_message = denied(uuid4())
    assert denied(foreign.id) == missing_message
    service.record_revision_action(
        base[3], replace(foreign, id=uuid4(), supersedes_revision_action_id=foreign.id)
    )
    assert denied(foreign.id) == missing_message
    with base[1]() as uow:
        assert uow.revision_action.predecessor(foreign.id, base[5]) is None


def test_frozen_claim_writer_overlap_does_not_invert_snapshot(revision_env, tmp_path):
    """A writer holding Claim parent can finish after recording releases its snapshot."""
    from threading import Event

    from researchbase.application.commands import ReviseClaimCommand
    from researchbase.domain.claim import ClaimVersionId
    from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock
    from tests.application_compat import LegacyApplicationService

    service, cmd, env, _, _ = revision_env
    base = env[-1]
    app = LegacyApplicationService(
        base[1], SystemClock(), ContentAddressedFilesystemArtifactStore(tmp_path / "writer-cas")
    )
    old = app.get_claim_version(ClaimVersionId(base[6]))
    parent = app.get_claim(old.claim_id)
    context = ExecutionContext(actor_id=base[3].actor_id, request_id=uuid4(), client_type="test")
    entered, release = Event(), Event()
    writer_pid = []

    def hold_parent(conn, cursor, statement, parameters, context, many):
        if statement.lstrip().upper().startswith("SELECT CLAIMS.") and "FOR UPDATE" in statement:
            writer_pid.append(conn.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(10)

    event.listen(base[8], "after_cursor_execute", hold_parent)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            writer = pool.submit(
                app.revise_claim,
                ReviseClaimCommand(
                    parent.id, "TEST ONLY later claim", {}, None, parent.row_version, context
                ),
            )
            assert entered.wait(10)
            # Recording may read frozen Claim closure while that parent row is held.
            saved = service.record_revision_action(base[3], cmd)
            assert not writer.done()
            release.set()
            writer.result(timeout=10)
            assert (
                service.read_revision_action(base[3], base[5], saved.id).content_hash
                == saved.content_hash
            )
    finally:
        release.set()
        event.remove(base[8], "after_cursor_execute", hold_parent)
    assert writer_pid
