"""Observed PostgreSQL waits, full UoW retries and atomic failure recovery."""

# Literal SQL instrumentation retains the reviewed lock protocol.
# ruff: noqa: E501

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import DBAPIError

from researchbase.application.prepared_submission import WithdrawPreparedSubmissionCommand
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.approval_repository import SqlAlchemyApprovalRepository
from researchbase.persistence.prepared_submission_repository import (
    B17_SHARE_SQL,
    SqlAlchemyPreparedSubmissionRepository,
)
from tests.integration.phase2.b17_fixtures import (
    b04_env,
    b05_env,
    b17_env,
    conclusion_env,
    counts,
    decision_env,
    next_package,
    phase2_database_url,
    revision_env,
    withdraw_consent,
)
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

_FIXTURES = (
    b04_env,
    b05_env,
    b17_env,
    conclusion_env,
    decision_env,
    phase2_database_url,
    revision_env,
)
pytestmark = pytest.mark.integration


def test_literal_first_sql_and_lock_order(b17_env):
    f = b17_env
    observed = []

    def capture(conn, cursor, sql, params, context, many):
        if cursor.connection.isolation_level.name == "SERIALIZABLE":
            observed.append(sql)

    event.listen(f.engine, "before_cursor_execute", capture)
    try:
        f.app.freeze_prepared_submission(f.actor, f.command)
    finally:
        event.remove(f.engine, "before_cursor_execute", capture)
    assert observed[:4] == [
        B17_SHARE_SQL,
        "LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE",
        "LOCK TABLE prepared_submission_versions IN SHARE ROW EXCLUSIVE MODE",
        "LOCK TABLE approval_decisions,approval_request_reviews,approval_requests IN SHARE MODE",
    ]
    manuscript = next(
        i for i, s in enumerate(observed) if "FROM manuscript_versions" in s and "FOR UPDATE" in s
    )
    parent = next(
        i for i, s in enumerate(observed) if "FROM publications" in s and "FOR UPDATE" in s
    )
    chain = next(
        i for i, s in enumerate(observed) if "FROM author_consents" in s and "FOR UPDATE" in s
    )
    grant = next(
        i for i, s in enumerate(observed) if "FROM approval_grants" in s and "FOR UPDATE" in s
    )
    assert manuscript < parent < chain < grant


@pytest.mark.parametrize(
    "stage",
    [
        "insert_item",
        "seal",
        "insert_event",
        "insert_consumption",
        "terminalize",
        "force_constraints",
    ],
)
def test_failure_after_each_effect_stage_rolls_back(b17_env, monkeypatch, stage):
    f = b17_env
    before = counts(f)
    cls = (
        SqlAlchemyPreparedSubmissionRepository
        if stage in {"insert_item", "seal", "insert_event"}
        else SqlAlchemyApprovalRepository
    )
    original = getattr(cls, stage)

    def fail(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise RuntimeError("injected after B17 stage")

    monkeypatch.setattr(cls, stage, fail)
    with pytest.raises(RuntimeError, match="injected"):
        f.app.freeze_prepared_submission(f.actor, f.command)
    assert counts(f) == before
    assert f.app.get_prepared_submission(f.actor, f.query).status == "PREPARED"


@pytest.mark.parametrize(
    "state,attempts", [("40001", 3), ("40P01", 3), ("55P03", 1), ("57014", 1), ("23505", 1)]
)
def test_only_serialization_and_deadlock_get_three_fresh_attempts(
    b17_env, monkeypatch, state, attempts
):
    f = b17_env
    calls = []
    before = counts(f)

    class Failure(Exception):
        sqlstate = state
        diag = SimpleNamespace(constraint_name="uq_b17_package_consumption")

    original = SqlAlchemyPreparedSubmissionRepository.seal

    def fail(self, *args):
        original(self, *args)
        calls.append(self._session)
        raise DBAPIError("seal", {}, Failure(), False)

    monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, "seal", fail)
    with pytest.raises(ResearchBaseError) as exc:
        f.app.freeze_prepared_submission(f.actor, f.command)
    assert exc.value.code == ErrorCode.CONCURRENT_MODIFICATION
    assert len(calls) == len({id(session) for session in calls}) == attempts
    assert counts(f) == before


@pytest.mark.parametrize("first_operation", ["freeze", "withdraw", "owner", "freeze_owner"])
def test_author_withdrawal_and_owner_withdrawal_observe_publication_exclusion(
    b17_env, monkeypatch, first_operation
):
    f = b17_env
    entered, release = Event(), Event()
    pids = []

    def freeze():
        return f.app.freeze_prepared_submission(f.actor, f.command)

    def withdraw():
        return withdraw_consent(f)

    def owner():
        return f.app.withdraw_prepared_submission(
            f.env[3],
            WithdrawPreparedSubmissionCommand(
                f.command.project_id, f.command.result_id, "Owner stop"
            ),
        )

    first, second = (
        (freeze, owner)
        if first_operation == "freeze_owner"
        else (freeze, withdraw)
        if first_operation == "freeze"
        else (withdraw, freeze)
        if first_operation == "withdraw"
        else (owner, freeze)
    )
    cls = (
        SqlAlchemyApprovalRepository
        if first_operation in {"freeze", "freeze_owner"}
        else SqlAlchemyPreparedSubmissionRepository
    )
    original = cls.force_constraints

    def pause(self):
        original(self)
        if not pids:
            pids.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(15)

    monkeypatch.setattr(cls, "force_constraints", pause)
    witness = create_engine(f.engine.url)

    def safe(call):
        try:
            return call()
        except ResearchBaseError as exc:
            return exc.code

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            one = pool.submit(first)
            assert entered.wait(15)
            two = pool.submit(safe, second)
            blocked = _wait_for_pg_blocker(witness, pids[0], "relation")
            assert blocked["pid"] != pids[0]
            # Snapshot reads remain available while the uncommitted writer is paused.
            assert f.app.get_prepared_submission(f.actor, f.query).status == "PREPARED"
            release.set()
            one.result(20)
            result = two.result(20)
        if first_operation in {"freeze", "freeze_owner"}:
            assert not isinstance(result, ErrorCode)
            saved = f.app.get_prepared_submission(f.actor, f.query)
            if first_operation == "freeze_owner":
                assert saved.status == "WITHDRAWN"
            else:
                assert saved.current_validity == "STALE"
        else:
            assert isinstance(result, ErrorCode)
            assert result in {
                ErrorCode.APPROVAL_GATE_FAILED,
                ErrorCode.GRANT_STALE,
                ErrorCode.INVALID_STATE_TRANSITION,
            }
    finally:
        release.set()
        witness.dispose()


@pytest.mark.parametrize("same_key", [False, True])
def test_same_package_freezes_serialize_without_duplicate_effect(b17_env, monkeypatch, same_key):
    f = b17_env
    entered, release = Event(), Event()
    pids = []
    original = SqlAlchemyApprovalRepository.force_constraints

    def pause(self):
        original(self)
        if not pids:
            pids.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(15)

    monkeypatch.setattr(SqlAlchemyApprovalRepository, "force_constraints", pause)
    command = f.command if same_key else replace(f.command, command_key=uuid4())

    def competitor():
        try:
            return f.app.freeze_prepared_submission(f.actor, command)
        except ResearchBaseError as exc:
            return exc.code

    witness = create_engine(f.engine.url)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            one = pool.submit(f.app.freeze_prepared_submission, f.actor, f.command)
            assert entered.wait(15)
            two = pool.submit(competitor)
            _wait_for_pg_blocker(witness, pids[0], "relation")
            release.set()
            first, second = one.result(20), two.result(20)
        assert second == (first if same_key else ErrorCode.GRANT_INVALID)
        assert len(f.app.get_prepared_submission(f.actor, f.query).events) == 2
    finally:
        release.set()
        witness.dispose()


def test_supersession_failure_restores_older_frozen_package(b17_env, monkeypatch):
    f = b17_env
    f.app.freeze_prepared_submission(f.actor, f.command)
    newer = next_package(f)
    before = counts(f)
    original = SqlAlchemyPreparedSubmissionRepository.supersede

    def fail(self, *args):
        original(self, *args)
        raise RuntimeError("after supersession")

    monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, "supersede", fail)
    with pytest.raises(RuntimeError, match="supersession"):
        newer.app.freeze_prepared_submission(newer.actor, newer.command)
    assert counts(f) == before
    assert f.app.get_prepared_submission(f.actor, f.query).status == "FROZEN"
    assert newer.app.get_prepared_submission(newer.actor, newer.query).status == "PREPARED"


@pytest.mark.parametrize("wait_at", ["table", "grant", "deferred"])
def test_actual_required_wait_crosses_grant_expiry(b05_env, monkeypatch, wait_at):
    from time import monotonic, sleep

    from tests.integration.phase2.b17_fixtures import build

    f = build(b05_env, lifetime=10)
    from researchbase.application.approval import ApprovalService

    authorizations = []
    acquisitions = []
    authorize = ApprovalService._authorize

    def observe_authorization(self, uow, *args, **kwargs):
        at = authorize(self, uow, *args, **kwargs)
        if (
            uow.approval._session.connection().get_execution_options().get("isolation_level")
            == "SERIALIZABLE"
        ):
            authorizations.append(at)
        return at

    monkeypatch.setattr(ApprovalService, "_authorize", observe_authorization)
    from researchbase.application.prepared_submission import PreparedSubmissionService

    package_authorize = PreparedSubmissionService._authorize

    def observe_package_authorization(self, uow, *args, **kwargs):
        at = package_authorize(self, uow, *args, **kwargs)
        if (
            uow.approval._session.connection().get_execution_options().get("isolation_level")
            == "SERIALIZABLE"
        ):
            authorizations.append(at)
        return at

    monkeypatch.setattr(PreparedSubmissionService, "_authorize", observe_package_authorization)
    noticed = set()

    def notice(value):
        from datetime import datetime

        if value.message_primary.startswith("B17_ACQUIRED:"):
            acquisitions.append(datetime.fromisoformat(value.message_primary.split(":", 1)[1]))

    def attach(conn, cursor, sql, params, context, many):
        raw = cursor.connection
        if raw.info.backend_pid not in noticed:
            raw.add_notice_handler(notice)
            noticed.add(raw.info.backend_pid)

    event.listen(f.engine, "before_cursor_execute", attach)
    cls = (
        SqlAlchemyPreparedSubmissionRepository
        if wait_at == "table"
        else SqlAlchemyApprovalRepository
    )
    method = (
        "prepare_freeze_write"
        if wait_at == "table"
        else "lock_grant"
        if wait_at == "grant"
        else "force_constraints"
    )
    original = getattr(cls, method)

    def observe_acquisition(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        acquisitions.append(self._session.execute(text("SELECT clock_timestamp()")).scalar_one())
        return result

    monkeypatch.setattr(cls, method, observe_acquisition)
    before = counts(f)
    with f.engine.connect() as conn:
        until = conn.execute(
            text("SELECT valid_until FROM approval_grants WHERE id=:id"), {"id": f.command.grant_id}
        ).scalar_one()
    with f.engine.connect() as holder, ThreadPoolExecutor(1) as pool:
        if wait_at == "table":
            holder.execute(text("LOCK TABLE internal_review_records IN ROW EXCLUSIVE MODE"))
        elif wait_at == "grant":
            holder.execute(
                text("SELECT id FROM approval_grants WHERE id=:id FOR UPDATE"),
                {"id": f.command.grant_id},
            )
        else:
            with f.engine.begin() as ddl:
                ddl.execute(
                    text(
                        "CREATE FUNCTION test_b17_wait() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN PERFORM pg_advisory_xact_lock(917065); RAISE NOTICE 'B17_ACQUIRED:%',clock_timestamp(); RETURN NULL; END $$"
                    )
                )
                ddl.execute(
                    text(
                        "CREATE CONSTRAINT TRIGGER test_b17_wait AFTER INSERT ON approval_grant_consumptions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION test_b17_wait()"
                    )
                )
            holder.execute(text("SELECT pg_advisory_xact_lock(917065)"))
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        future = pool.submit(f.app.freeze_prepared_submission, f.actor, f.command)
        witness = _wait_for_pg_blocker(
            f.engine,
            pid,
            "relation"
            if wait_at == "table"
            else "transactionid"
            if wait_at == "grant"
            else "advisory",
        )
        with f.engine.connect() as observer:
            started, waiting = observer.execute(
                text("SELECT xact_start,clock_timestamp() FROM pg_stat_activity WHERE pid=:pid"),
                {"pid": witness["pid"]},
            ).one()
        assert started < until and waiting < until
        deadline = monotonic() + 20
        while True:
            with f.engine.connect() as observer:
                observed = observer.execute(text("SELECT clock_timestamp()")).scalar_one()
            if observed >= until:
                break
            assert monotonic() < deadline
            sleep(0.01)
        holder.rollback()
        with pytest.raises(ResearchBaseError) as exc:
            future.result(15)
        assert exc.value.code == ErrorCode.GRANT_INVALID
        with f.engine.connect() as observer:
            final = observer.execute(text("SELECT clock_timestamp()")).scalar_one()
        context_error = exc.value.__context__
        detail = getattr(
            getattr(getattr(context_error, "orig", None), "diag", None), "message_detail", None
        )
        if detail and detail.startswith("b17_authorization_checked_at="):
            from datetime import datetime

            authorizations.append(datetime.fromisoformat(detail.split("=", 1)[1]))
        assert acquisitions and authorizations
        acquired = acquisitions[-1]
        checked = authorizations[-1]
        assert acquired >= until and checked >= acquired and checked > until
        if wait_at != "table":
            assert any(at < until for at in authorizations)
        print(
            "B17_EXPIRY",
            dict(
                tx_started_at=started,
                expiry_at=until,
                lock_wait_started_at=waiting,
                lock_acquired_at=acquired,
                authorization_checked_at=checked,
                observation_completed_at=final,
                outcome=exc.value.code.value,
                protected_counts=counts(f),
            ),
        )
    assert counts(f) == before
    event.remove(f.engine, "before_cursor_execute", attach)


def observed_order(f, first, second, pause_prefix, *, other_engines=()):
    """Hold the first real transaction and witness the second backend's wait."""
    entered, release = Event(), Event()
    holder = []

    def pause(conn, cursor, sql, params, context, many):
        if not holder and " ".join(sql.upper().split()).startswith(pause_prefix):
            holder.append(cursor.connection.info.backend_pid)
            entered.set()
            assert release.wait(20)

    def safe(call):
        try:
            return call()
        except ResearchBaseError as exc:
            return exc.code

    engines = (f.engine, *other_engines)
    for engine in engines:
        event.listen(engine, "after_cursor_execute", pause)
    witness = create_engine(f.engine.url)
    try:
        with ThreadPoolExecutor(2) as pool:
            one = pool.submit(safe, first)
            assert entered.wait(20)
            two = pool.submit(safe, second)
            try:
                blocked = _wait_for_pg_blocker(witness, holder[0], "relation")
                assert blocked["pid"] != holder[0]
            finally:
                release.set()
            return one.result(25), two.result(25)
    finally:
        release.set()
        for engine in engines:
            event.remove(engine, "after_cursor_execute", pause)
        witness.dispose()


FREEZE_PAUSE = "LOCK TABLE APPROVAL_DECISIONS,APPROVAL_REQUEST_REVIEWS,APPROVAL_REQUESTS"


@pytest.mark.parametrize("newer_first", [False, True])
@pytest.mark.parametrize("same_grant", [False, True])
def test_two_package_freezes_observe_supersession_and_single_use(b17_env, newer_first, same_grant):
    f = b17_env
    newer = next_package(f)
    if same_grant:
        newer = replace(newer, command=replace(newer.command, grant_id=f.command.grant_id))

    def old_call():
        return f.app.freeze_prepared_submission(f.actor, f.command)

    def new_call():
        return newer.app.freeze_prepared_submission(newer.actor, newer.command)

    first, second = observed_order(
        f,
        new_call if newer_first else old_call,
        old_call if newer_first else new_call,
        FREEZE_PAUSE,
    )
    assert not isinstance(first, ErrorCode)
    if same_grant:
        assert second == ErrorCode.GRANT_INVALID
    elif newer_first:
        assert second == ErrorCode.INVALID_STATE_TRANSITION
    else:
        assert not isinstance(second, ErrorCode)
    with f.engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id,status FROM prepared_submission_versions ORDER BY version_number")
        ).all()
        assert sum(status == "FROZEN" for _, status in rows) == 1
        assert conn.execute(
            text(
                "SELECT count(*) FROM approval_grant_consumptions WHERE command='FREEZE_PREPARED_SUBMISSION'"
            )
        ).scalar_one() == (2 if not same_grant and not newer_first else 1)
    assert rows[0][1] == (
        "SUPERSEDED"
        if not same_grant and not newer_first
        else "PREPARED"
        if newer_first
        else "FROZEN"
    )


@pytest.mark.parametrize("freeze_first", [False, True])
@pytest.mark.parametrize("maintenance", ["evaluate", "revoke"])
def test_grant_maintenance_and_freeze_both_commit_orders(b17_env, freeze_first, maintenance):
    from researchbase.application.approval import (
        EvaluateApprovalGrantCommand,
        RevokeApprovalGrantCommand,
    )

    f = b17_env

    def freeze():
        return f.app.freeze_prepared_submission(f.actor, f.command)

    def maintain():
        if maintenance == "evaluate":
            return f.approval.evaluate_approval_grant(
                f.actor, EvaluateApprovalGrantCommand(f.command.project_id, f.command.grant_id)
            )
        return f.approval.revoke_approval_grant(
            f.env[3],
            RevokeApprovalGrantCommand(
                f.command.project_id, f.command.grant_id, "Owner revocation"
            ),
        )

    first, second = observed_order(
        f,
        freeze if freeze_first else maintain,
        maintain if freeze_first else freeze,
        FREEZE_PAUSE if freeze_first else "SET CONSTRAINTS ALL IMMEDIATE",
    )
    frozen = freeze_first or maintenance == "evaluate"
    assert not isinstance(first, ErrorCode)
    if not frozen:
        assert second == ErrorCode.GRANT_INVALID
    assert f.app.get_prepared_submission(f.actor, f.query).status == (
        "FROZEN" if frozen else "PREPARED"
    )
    assert f.approval.get_grant(f.actor, f.command.project_id, f.command.grant_id).status == (
        "CONSUMED" if frozen else "REVOKED"
    )


@pytest.mark.parametrize("freeze_first", [False, True])
@pytest.mark.parametrize("mutation", ["issue", "scientific"])
def test_issue_insert_and_scientific_invalidation_both_commit_orders(
    b17_env, freeze_first, mutation
):
    from researchbase.application.governance import (
        CreateImpactAssessmentCommand,
        GovernanceService,
        ProposedImpactTarget,
    )
    from researchbase.application.internal_review import ReviewIssueRequest
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock
    from tests.integration.phase2.test_b05_manuscript_review import create

    f = b17_env
    with f.engine.connect() as conn:
        document = conn.execute(
            text("SELECT document_artifact_version_id FROM manuscript_versions WHERE id=:id"),
            {"id": f.package_command.manuscript_version_id},
        ).scalar_one()

    def mutate():
        if mutation == "issue":
            return create(
                f.env, issues=(ReviewIssueRequest("BLOCKING", "OTHER", "Concurrent blocker"),)
            )
        return GovernanceService(f.env[4], SystemClock()).create_impact_assessment(
            CreateImpactAssessmentCommand(
                f.command.project_id,
                None,
                {"test": "Observed invalidation race"},
                "invalid",
                (ProposedImpactTarget("artifact_version", document, "invalid"),),
                ExecutionContext(actor_id=f.actor.actor_id, request_id=uuid4(), client_type="test"),
            )
        )

    def freeze():
        return f.app.freeze_prepared_submission(f.actor, f.command)

    first, second = observed_order(
        f,
        freeze if freeze_first else mutate,
        mutate if freeze_first else freeze,
        FREEZE_PAUSE
        if freeze_first
        else "INSERT INTO REVIEW_ISSUES"
        if mutation == "issue"
        else "INSERT INTO IMPACT_ASSESSMENTS",
    )
    assert not isinstance(first, ErrorCode)
    if freeze_first:
        assert not isinstance(second, ErrorCode)
        saved = f.app.get_prepared_submission(f.actor, f.query)
        assert saved.status == "FROZEN" and saved.consumption_id is not None
        assert saved.package_manifest_hash == f.command.expected_package_manifest_hash
        if mutation == "scientific":
            assert saved.current_validity in {"STALE", "INVALID"}
    else:
        assert second == (
            ErrorCode.APPROVAL_GATE_FAILED
            if mutation == "issue"
            else ErrorCode.APPROVAL_TARGET_STALE
        )
        assert f.app.get_prepared_submission(f.actor, f.query).status == "PREPARED"


@pytest.mark.parametrize("wait_at", ["prefix", "deferred"])
def test_actual_issuer_revocation_at_observed_wait_rolls_back(b17_env, monkeypatch, wait_at):
    f = b17_env
    before = counts(f)
    if wait_at == "deferred":
        original = SqlAlchemyApprovalRepository.force_constraints

        def revoke(self):
            original(self)
            del f.env[9].principals[f.approver.actor_id]

        monkeypatch.setattr(SqlAlchemyApprovalRepository, "force_constraints", revoke)
        with pytest.raises(ResearchBaseError) as exc:
            f.app.freeze_prepared_submission(f.actor, f.command)
    else:
        with f.engine.connect() as holder, ThreadPoolExecutor(1) as pool:
            holder.execute(text("LOCK TABLE project_role_assignments IN ROW EXCLUSIVE MODE"))
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            future = pool.submit(f.app.freeze_prepared_submission, f.actor, f.command)
            _wait_for_pg_blocker(f.engine, pid, "relation")
            del f.env[9].principals[f.approver.actor_id]
            holder.rollback()
            with pytest.raises(ResearchBaseError) as exc:
                future.result(20)
    assert exc.value.code == ErrorCode.GRANT_STALE
    assert counts(f) == before


@pytest.mark.parametrize("freeze_first", [False, True])
def test_upstream_issue_disposition_and_freeze_both_commit_orders(
    b05_env, revision_env, freeze_first
):
    from researchbase.application.manuscript_placement import ClaimPlacementService
    from tests.integration.phase2.b08_support import current_disposition_case
    from tests.integration.phase2.b17_fixtures import build

    env = b05_env
    ClaimPlacementService(env[4], env[9]).add(
        env[2],
        env[1].project_id,
        env[1].publication_id,
        env[1].manuscript_version_id,
        None,
        revision_env[4].version_id,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "p1"},
        "SUPPORTED",
        0,
        uuid4(),
    )
    f = build(env)
    reviews, actor, cmd, _, _ = current_disposition_case(revision_env, dismiss=True)

    def freeze():
        return f.app.freeze_prepared_submission(f.actor, f.command)

    def dispose():
        return reviews.record_issue_disposition(actor, cmd)

    first, second = observed_order(
        f,
        freeze if freeze_first else dispose,
        dispose if freeze_first else freeze,
        FREEZE_PAUSE if freeze_first else "INSERT INTO REVIEW_ISSUE_EVENTS",
        other_engines=(revision_env[2][-1][8],),
    )
    if freeze_first:
        assert first == ErrorCode.APPROVAL_GATE_FAILED
    else:
        assert not isinstance(second, ErrorCode)
    assert not isinstance(second if freeze_first else first, ErrorCode)
    assert f.app.get_prepared_submission(f.actor, f.query).status == (
        "PREPARED" if freeze_first else "FROZEN"
    )


@pytest.mark.parametrize("consent_index", [0, 1])
def test_failure_after_each_of_two_authored_consent_items_is_atomic(
    b05_env, monkeypatch, consent_index
):
    from tests.integration.phase2.b17_fixtures import build
    from tests.integration.phase2.test_b14r_ready_approval import approver

    f = build(b05_env, coauthors=(approver(b05_env),))
    before = counts(f)
    inserted = []
    original = SqlAlchemyPreparedSubmissionRepository.insert_item

    def fail(self, row):
        original(self, row)
        if row["category"] == "AUTHOR_CONSENT":
            inserted.append(row["author_consent_id"])
            if len(inserted) == consent_index + 1:
                raise RuntimeError("after authored consent item")

    monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, "insert_item", fail)
    with pytest.raises(RuntimeError, match="authored consent"):
        f.app.freeze_prepared_submission(f.actor, f.command)
    assert len(inserted) == consent_index + 1
    assert counts(f) == before
    assert f.app.get_prepared_submission(f.actor, f.query).status == "PREPARED"


def test_observed_table_wait_crosses_scheduled_issuer_credential_expiry(b17_env, monkeypatch):
    from time import monotonic, sleep

    f = b17_env
    before = counts(f)
    with f.engine.connect() as conn:
        expiry = conn.execute(text("SELECT clock_timestamp()+interval '2 seconds'")).scalar_one()
    credentials = f.env[9]
    original = credentials.is_valid
    checks = []

    def is_valid(principal, at):
        if principal.actor_id == f.approver.actor_id:
            checks.append(at)
            return at < expiry and original(principal, at)
        return original(principal, at)

    monkeypatch.setattr(credentials, "is_valid", is_valid)
    with f.engine.connect() as holder, ThreadPoolExecutor(1) as pool:
        holder.execute(text("LOCK TABLE internal_review_records IN ROW EXCLUSIVE MODE"))
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        future = pool.submit(f.app.freeze_prepared_submission, f.actor, f.command)
        waiting = _wait_for_pg_blocker(f.engine, pid, "relation")
        with f.engine.connect() as conn:
            started, observed_wait = conn.execute(
                text("SELECT xact_start,clock_timestamp() FROM pg_stat_activity WHERE pid=:pid"),
                {"pid": waiting["pid"]},
            ).one()
        assert started < observed_wait < expiry
        deadline = monotonic() + 20
        while True:
            with f.engine.connect() as conn:
                observed = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
            if observed >= expiry:
                break
            assert monotonic() < deadline
            sleep(0.01)
        holder.rollback()
        with pytest.raises(ResearchBaseError) as exc:
            future.result(20)
    assert exc.value.code == ErrorCode.GRANT_STALE and any(at >= expiry for at in checks)
    assert counts(f) == before
