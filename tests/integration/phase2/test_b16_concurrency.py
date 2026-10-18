"""Independent PostgreSQL lock witnesses, CAS, rollback and read-only replay."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import DBAPIError

from researchbase.application.prepared_submission import (
    GetOwnAuthorConsentQuery,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.prepared_submission_repository import (
    B16_SHARE_SQL,
    SqlAlchemyPreparedSubmissionRepository,
)
from tests.integration.phase2.b16_fixtures import (  # noqa: F401
    b04_env as _b04_env,
)
from tests.integration.phase2.b16_fixtures import (
    b15_env as _b15_env,
)
from tests.integration.phase2.b16_fixtures import (
    conclusion_env as _conclusion_env,
)
from tests.integration.phase2.b16_fixtures import (
    rooted,
    successor,
)
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker


@pytest.mark.parametrize("same_uuid", [False, True])
def test_successors_serialize_before_snapshot_on_publication(b15_env, monkeypatch, same_uuid):
    service, _, actor, _, engine, *_ = b15_env
    _, _, cmd, root = rooted(b15_env)
    withdrawal = successor(cmd, root)
    competing = withdrawal if same_uuid else replace(withdrawal, id=uuid4())
    entered, release = Event(), Event()
    first_pid = []
    original = SqlAlchemyPreparedSubmissionRepository.force_constraints

    def pause(self):
        original(self)
        if not first_pid:
            first_pid.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(10)

    monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, "force_constraints", pause)
    witness_engine = create_engine(engine.url)

    def second():
        try:
            return service.record_author_consent(actor, competing)
        except ResearchBaseError as exc:
            return exc.code

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(service.record_author_consent, actor, withdrawal)
            assert entered.wait(10)
            other = pool.submit(second)
            witness = _wait_for_pg_blocker(witness_engine, first_pid[0], "relation")
            assert witness["pid"] != first_pid[0]
            release.set()
            result, competitor = first.result(15), other.result(15)
        assert competitor == (result if same_uuid else ErrorCode.CONCURRENT_MODIFICATION)
    finally:
        release.set()
        witness_engine.dispose()


@pytest.mark.parametrize(
    "state,attempts", [("40001", 3), ("40P01", 3), ("55P03", 1), ("57014", 1), ("23505", 1)]
)
def test_consent_retry_budget_and_atomic_rollback(b15_env, monkeypatch, state, attempts):
    service, _, actor, _, engine, *_ = b15_env
    _, _, cmd, root = rooted(b15_env)
    calls = []
    original = SqlAlchemyPreparedSubmissionRepository.insert_consent

    from types import SimpleNamespace

    class Conflict(Exception):
        sqlstate = state
        diag = SimpleNamespace(constraint_name="uq_author_consents_successor")

    def fail(self, row):
        original(self, row)
        calls.append(row["id"])
        raise DBAPIError("insert", {}, Conflict(), False)

    monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, "insert_consent", fail)
    with pytest.raises(ResearchBaseError) as exc:
        service.record_author_consent(actor, successor(cmd, root))
    assert exc.value.code == ErrorCode.CONCURRENT_MODIFICATION and len(calls) == attempts
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM author_consents")).scalar_one() == 1


b04_env = _b04_env
b15_env = _b15_env
conclusion_env = _conclusion_env


def test_own_read_and_withdrawal_replay_never_lock(b15_env):
    service, command, actor, _, engine, *_ = b15_env
    package, _, cmd, root = rooted(b15_env)
    withdrawal = successor(cmd, root)
    saved = service.record_author_consent(actor, withdrawal)
    observed = []

    def capture(conn, cursor, statement, params, context, many):
        observed.append(statement)
        upper = statement.upper()
        assert not upper.lstrip().startswith(
            ("LOCK ", "INSERT ", "UPDATE ", "DELETE ", "SET CONSTRAINTS")
        )
        assert all(value not in upper for value in ("FOR UPDATE", "FOR SHARE", "PG_ADVISORY"))

    event.listen(engine, "before_cursor_execute", capture)
    try:
        assert service.record_author_consent(actor, withdrawal) == saved
        service.get_own_author_consent(
            actor, GetOwnAuthorConsentQuery(command.project_id, package.id, root.id)
        )
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert observed


def test_consent_first_sql_literal_inventory_and_final_modes(b15_env):
    service, _, actor, _, engine, *_ = b15_env
    _, _, cmd, root = rooted(b15_env)
    transactions = []

    def begin(conn):
        transactions.append([])
        conn.info["b16_sql"] = transactions[-1]

    def capture(conn, cursor, statement, params, context, many):
        conn.info["b16_sql"].append(statement)

    event.listen(engine, "begin", begin)
    event.listen(engine, "before_cursor_execute", capture)
    try:
        service.record_author_consent(actor, successor(cmd, root))
    finally:
        event.remove(engine, "begin", begin)
        event.remove(engine, "before_cursor_execute", capture)
    writes = [tx for tx in transactions if B16_SHARE_SQL in tx]
    assert len(writes) == 1
    assert writes[0][:3] == [
        B16_SHARE_SQL,
        "LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE",
        "LOCK TABLE approval_decisions,approval_request_reviews,approval_requests IN SHARE MODE",
    ]


@pytest.mark.parametrize(
    "case",
    [
        "grant_insert_first",
        "withdrawal_first_empty_requests",
        "withdrawal_first_empty_grants",
        "maintenance_first",
        "withdrawal_first_maintenance",
        "rollback_each_grant_event",
    ],
)
def test_prepare_grant_serialization_and_rollback(b15_env, b04_env, monkeypatch, case):
    from datetime import timedelta

    from researchbase.application.approval import EvaluateApprovalGrantCommand
    from researchbase.persistence.approval_repository import SqlAlchemyApprovalRepository
    from tests.integration.phase2.b16_fixtures import grant_context, grant_request, issue_grant

    ctx = grant_context(b15_env, b04_env[-1][4])
    service, command, author, _, engine, *_ = b15_env
    withdrawal = successor(ctx["consent"], ctx["root"])
    if case == "rollback_each_grant_event":
        grants = [issue_grant(ctx), issue_grant(ctx)]
        for phase in ("consent", "event0", "update0", "event1", "update1", "constraints"):
            seen = []

            def injected(conn, cursor, statement, params, context, many, phase=phase, seen=seen):
                operation = statement.lstrip()
                kind = (
                    "event"
                    if operation.startswith("INSERT INTO approval_grant_events")
                    else "update"
                    if operation.startswith("UPDATE approval_grants")
                    else None
                )
                if kind:
                    seen.append(kind)
                    if phase.startswith(kind) and seen.count(kind) == int(phase[-1]) + 1:
                        raise RuntimeError("injected grant boundary")

            original_insert = SqlAlchemyPreparedSubmissionRepository.insert_consent
            original_force = SqlAlchemyPreparedSubmissionRepository.force_constraints

            def fail_insert(self, row, original_insert=original_insert):
                original_insert(self, row)
                raise RuntimeError("injected consent boundary")

            def fail_force(self, original_force=original_force):
                original_force(self)
                raise RuntimeError("injected deferred boundary")

            with monkeypatch.context() as patches:
                if phase == "consent":
                    patches.setattr(
                        SqlAlchemyPreparedSubmissionRepository, "insert_consent", fail_insert
                    )
                if phase == "constraints":
                    patches.setattr(
                        SqlAlchemyPreparedSubmissionRepository, "force_constraints", fail_force
                    )
                event.listen(engine, "after_cursor_execute", injected)
                try:
                    with pytest.raises(RuntimeError, match="injected"):
                        service.record_author_consent(author, withdrawal)
                finally:
                    event.remove(engine, "after_cursor_execute", injected)
            with engine.connect() as conn:
                assert conn.execute(text("SELECT count(*) FROM author_consents")).scalar_one() == 1
                assert (
                    conn.execute(
                        text(
                            "SELECT count(*) FROM approval_grant_events "
                            "WHERE prior_status='ACTIVE' "
                            "AND grant_id IN (SELECT id FROM approval_grants "
                            "WHERE purpose='PREPARE_SUBMISSION')"
                        )
                    ).scalar_one()
                    == 0
                )
                assert dict(
                    conn.execute(
                        text(
                            "SELECT id,status FROM approval_grants "
                            "WHERE purpose='PREPARE_SUBMISSION'"
                        )
                    ).all()
                ) == {g.id: "ACTIVE" for g in grants}
        return
    maintenance = case in {"maintenance_first", "withdrawal_first_maintenance"}
    grant = None
    request = None
    if maintenance:
        with engine.connect() as conn:
            until = conn.execute(text("SELECT clock_timestamp()")).scalar_one() + timedelta(
                seconds=1
            )
        grant = issue_grant(ctx, valid_until=until)
        with engine.connect() as conn:
            conn.execute(
                text(
                    "SELECT pg_sleep(greatest(0,extract(epoch FROM "
                    "(:until-clock_timestamp())))+0.02)"
                ),
                {"until": until},
            )
    elif case == "withdrawal_first_empty_grants":
        request = grant_request(ctx)
        ctx["approval"].request_approval(ctx["requester"], request)
    entered, release = Event(), Event()
    holder = []
    first_is_withdrawal = case.startswith("withdrawal_first")
    original_consent = SqlAlchemyPreparedSubmissionRepository.force_constraints
    original_approval = SqlAlchemyApprovalRepository.force_constraints

    def hold(self):
        if not holder:
            holder.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(10)

    def consent_force(self):
        original_consent(self)
        if first_is_withdrawal:
            hold(self)

    def approval_force(self):
        original_approval(self)
        if not first_is_withdrawal and (
            maintenance
            or self._session.execute(
                text("SELECT count(*) FROM approval_grants WHERE purpose='PREPARE_SUBMISSION'")
            ).scalar_one()
        ):
            hold(self)

    monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, "force_constraints", consent_force)
    monkeypatch.setattr(SqlAlchemyApprovalRepository, "force_constraints", approval_force)

    def withdraw():
        return service.record_author_consent(author, withdrawal)

    def other() -> Any:
        if maintenance:
            assert grant is not None
            return ctx["approval"].evaluate_approval_grant(
                author, EvaluateApprovalGrantCommand(command.project_id, grant.id)
            )
        return issue_grant(ctx, request)

    witness_engine = create_engine(engine.url)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(withdraw if first_is_withdrawal else other)
            assert entered.wait(10)
            second = pool.submit(other if first_is_withdrawal else withdraw)
            witness = _wait_for_pg_blocker(witness_engine, holder[0], "relation")
            assert witness["pid"] != holder[0]
            release.set()
            a, b = first.result(15), second.result(15)
        result = b if first_is_withdrawal else a
        if maintenance:
            assert grant is not None
            identity = grant.id
        else:
            identity = result.id
        expected = (
            "EXPIRED"
            if case == "maintenance_first"
            else "STALE"
            if maintenance or case == "grant_insert_first"
            else "ACTIVE"
        )
        with engine.connect() as conn:
            assert (
                conn.execute(
                    text("SELECT status FROM approval_grants WHERE id=:id"), {"id": identity}
                ).scalar_one()
                == expected
            )
            assert (
                conn.execute(
                    text("SELECT count(*) FROM author_consents WHERE consent_state='WITHDRAWN'")
                ).scalar_one()
                == 1
            )
        # Replaying the completed withdrawal must not sweep later grants.
        service.record_author_consent(author, withdrawal)
        with engine.connect() as conn:
            assert (
                conn.execute(
                    text("SELECT status FROM approval_grants WHERE id=:id"), {"id": identity}
                ).scalar_one()
                == expected
            )
    finally:
        release.set()
        witness_engine.dispose()


@pytest.mark.parametrize(
    "wait_at", ["inventory", "publication_table", "advisory", "manuscript", "package"]
)
def test_withdrawal_credential_expiry_after_observed_wait_rolls_back(b15_env, wait_at):
    service, _, actor, _, engine, _, original_credentials = b15_env
    package, _, cmd, root = rooted(b15_env)
    withdrawal = successor(cmd, root)

    class Expiring:
        expiry = None

        def is_valid(self, principal, at):
            return original_credentials.is_valid(principal, at) and (
                self.expiry is None or at < self.expiry
            )

    credentials = Expiring()
    service._credentials = credentials
    holder_engine = create_engine(engine.url)
    try:
        with holder_engine.connect() as holder:
            tx = holder.begin()
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            if wait_at == "inventory":
                holder.execute(text("LOCK TABLE actors IN ROW EXCLUSIVE MODE"))
            elif wait_at == "publication_table":
                holder.execute(text("LOCK TABLE publications IN SHARE MODE"))
            elif wait_at == "advisory":
                holder.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                    {"key": f"b15:consent:{withdrawal.id}"},
                )
            else:
                table = (
                    "manuscript_versions"
                    if wait_at == "manuscript"
                    else "prepared_submission_versions"
                )
                identity = package.manuscript_version_id if wait_at == "manuscript" else package.id
                holder.execute(
                    text(f"SELECT id FROM {table} WHERE id=:id FOR UPDATE"), {"id": identity}
                )
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(service.record_author_consent, actor, withdrawal)
                kind = (
                    "relation"
                    if wait_at in {"inventory", "publication_table"}
                    else "advisory"
                    if wait_at == "advisory"
                    else "transactionid"
                )
                _wait_for_pg_blocker(engine, pid, kind)
                with engine.connect() as observer:
                    credentials.expiry = observer.execute(
                        text("SELECT clock_timestamp()")
                    ).scalar_one()
                tx.commit()
                with pytest.raises(ResearchBaseError) as exc:
                    future.result(15)
                assert exc.value.code == ErrorCode.FORBIDDEN
        with engine.connect() as observer:
            assert observer.execute(text("SELECT count(*) FROM author_consents")).scalar_one() == 1
    finally:
        holder_engine.dispose()


@pytest.mark.parametrize("author_first", [True, False])
def test_owner_package_withdrawal_and_author_withdrawal_both_orders(
    b15_env, monkeypatch, author_first
):
    from researchbase.application.prepared_submission import WithdrawPreparedSubmissionCommand

    service, command, actor, _, engine, *_ = b15_env
    package, query, cmd, root = rooted(b15_env)
    entered, release = Event(), Event()
    first_pid = []
    original = SqlAlchemyPreparedSubmissionRepository.force_constraints

    def pause(self):
        original(self)
        if not first_pid:
            first_pid.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(10)

    monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, "force_constraints", pause)

    def author():
        return service.record_author_consent(actor, successor(cmd, root))

    def owner():
        return service.withdraw_prepared_submission(
            actor, WithdrawPreparedSubmissionCommand(command.project_id, package.id, "owner end")
        )

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(author if author_first else owner)
            assert entered.wait(10)
            second = pool.submit(owner if author_first else author)
            _wait_for_pg_blocker(engine, first_pid[0], "relation")
            release.set()
            first.result(15)
            second.result(15)
        result = service.get_prepared_submission(actor, query)
        assert result.status == "WITHDRAWN" and len(result.events) == 2
        assert [c.consent_state for c in result.consents] == ["GRANTED", "WITHDRAWN"]
    finally:
        release.set()


@pytest.mark.parametrize("expire_at", ["evidence", "constraints"])
def test_new_evidence_withdrawal_rechecks_entitlement_before_effect_and_commit(
    b15_env, monkeypatch, expire_at
):
    from tests.integration.phase2.test_pr2_10_binding_contract import _artifact

    service, command, actor, factory, engine, store, _ = b15_env
    _, _, cmd, root = rooted(b15_env)
    new_evidence = _artifact(
        factory, store, actor, command.project_id, b"fresh withdrawal evidence"
    )
    withdrawal = replace(successor(cmd, root), evidence_artifact_version_id=new_evidence)
    expired = False
    authorize = service._authorize
    evidence = service._evidence
    constraints = SqlAlchemyPreparedSubmissionRepository.force_constraints

    def authorization(*args, **kwargs):
        result = authorize(*args, **kwargs)
        if expired:
            raise ResearchBaseError(ErrorCode.FORBIDDEN, "scheduled reader expiry")
        return result

    def verify(*args, **kwargs):
        nonlocal expired
        result = evidence(*args, **kwargs)
        if expire_at == "evidence":
            expired = True
        return result

    def force(self):
        nonlocal expired
        constraints(self)
        if expire_at == "constraints":
            expired = True

    monkeypatch.setattr(service, "_authorize", authorization)
    monkeypatch.setattr(service, "_evidence", verify)
    monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, "force_constraints", force)
    with pytest.raises(ResearchBaseError) as exc:
        service.record_author_consent(actor, withdrawal)
    assert exc.value.code == ErrorCode.FORBIDDEN
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM author_consents")).scalar_one() == 1


def test_regrant_rechecks_credential_after_final_context_verification(b15_env, monkeypatch):
    service, _, actor, _, engine, _, original_credentials = b15_env
    _, _, cmd, root = rooted(b15_env)
    withdrawn = service.record_author_consent(actor, successor(cmd, root))

    class Expiring:
        expired = False

        def is_valid(self, principal, at):
            return not self.expired and original_credentials.is_valid(principal, at)

    credentials = Expiring()
    service._credentials = credentials
    original = service._context
    checks = []

    def context(*args, **kwargs):
        result = original(*args, **kwargs)
        checks.append(True)
        if len(checks) == 2:
            credentials.expired = True
        return result

    monkeypatch.setattr(service, "_context", context)
    with pytest.raises(ResearchBaseError) as exc:
        service.record_author_consent(actor, successor(cmd, withdrawn, "GRANTED"))
    assert exc.value.code == ErrorCode.FORBIDDEN and len(checks) == 2
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM author_consents")).scalar_one() == 2


@pytest.mark.parametrize("decision_first", [True, False])
def test_ready_decision_prefix_excludes_publication_insert_phantoms(
    b15_env, b04_env, monkeypatch, decision_first
):
    from threading import current_thread

    from researchbase.application.approval import DecideApprovalCommand
    from researchbase.persistence.approval_repository import B09_DECIDE_SHARE_SQL
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork
    from tests.integration.phase2.b16_fixtures import grant_context

    ctx = grant_context(b15_env, b04_env[-1][4], consume_ready=False)
    _, command, author, _, engine, *_ = b15_env
    request = replace(ctx["ready_request"], id=uuid4())
    ctx["approval"].request_approval(ctx["requester"], request)
    entered, release = Event(), Event()
    holder = []
    transactions = []
    original = SqlAlchemyUnitOfWork.commit

    def commit(self):
        if current_thread().name.startswith("b16-first") and not holder:
            self._session.flush()
            holder.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(10)
        return original(self)

    def begin(conn):
        conn.info["b16_ready_sql"] = []
        transactions.append(conn.info["b16_ready_sql"])

    def capture(conn, cursor, statement, params, context, many):
        conn.info["b16_ready_sql"].append(statement)

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", commit)
    event.listen(engine, "begin", begin)
    event.listen(engine, "before_cursor_execute", capture)

    def decide():
        return ctx["approval"].decide_approval(
            ctx["approver"],
            DecideApprovalCommand(uuid4(), command.project_id, request.id, "APPROVE", "READY"),
        )

    def insert():
        # Use guarded SQL so an earlier project-row lock in create_publication
        # cannot hide the Publication INSERT relation-lock phantom witness.
        identity = uuid4()
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO publications(id,project_id,publication_type,title,"
                    "lifecycle_status,row_version,created_at,created_by) "
                    "VALUES(:id,:project,'PAPER','Concurrent publication','DRAFTING',"
                    "1,clock_timestamp(),:actor)"
                ),
                {"id": identity, "project": command.project_id, "actor": author.actor_id},
            )
            conn.execute(
                text(
                    "INSERT INTO publication_lifecycle_events(id,publication_id,actor_id,"
                    "prior_status,new_status,occurred_at) "
                    "SELECT :event,id,created_by,NULL,'DRAFTING',created_at "
                    "FROM publications WHERE id=:id"
                ),
                {"id": identity, "event": uuid4()},
            )
            if not decision_first:
                holder.append(conn.execute(text("SELECT pg_backend_pid()")).scalar_one())
                entered.set()
                assert release.wait(10)
        return identity

    try:
        with (
            ThreadPoolExecutor(1, thread_name_prefix="b16-first") as first_pool,
            ThreadPoolExecutor(1) as second_pool,
        ):
            first = first_pool.submit(decide if decision_first else insert)
            assert entered.wait(10)
            second = second_pool.submit(insert if decision_first else decide)
            try:
                try:
                    witness = _wait_for_pg_blocker(engine, holder[0], "relation")
                except BaseException:
                    if second.done():
                        second.result()
                    raise
                assert witness["pid"] != holder[0]
                assert witness["relation"] == "publications"
            finally:
                release.set()
            first.result(15)
            second.result(15)
        writer = next(tx for tx in transactions if B09_DECIDE_SHARE_SQL in tx)
        assert writer[:2] == [
            B09_DECIDE_SHARE_SQL,
            "LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE",
        ]
        request_lock = next(i for i, sql in enumerate(writer) if "pg_advisory_xact_lock" in sql)
        assert request_lock > 1
        assert "LOCK TABLE publications IN SHARE MODE" not in writer
        with engine.connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM publications")).scalar_one() == 2
    finally:
        release.set()
        event.remove(engine, "begin", begin)
        event.remove(engine, "before_cursor_execute", capture)


@pytest.mark.parametrize("withdrawal_first", [True, False])
def test_ready_consumption_and_same_manuscript_consent_withdrawal(
    b15_env, b04_env, monkeypatch, withdrawal_first
):
    from threading import current_thread

    from researchbase.application.decision import (
        DecisionService,
        RecordPrepareSubmissionDecisionCommand,
    )
    from researchbase.application.literature_evidence import LiteratureEvidenceService
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork
    from tests.integration.phase2.b16_fixtures import grant_context, issue_grant

    ctx = grant_context(b15_env, b04_env[-1][4], consume_ready=False)
    service, command, author, factory, engine, store, credentials = b15_env
    withdrawal = successor(ctx["consent"], ctx["root"])
    entered, release = Event(), Event()
    holder = []
    original = SqlAlchemyUnitOfWork.commit

    def commit(self):
        if current_thread().name.startswith("b16-first") and not holder:
            self._session.flush()
            holder.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(10)
        return original(self)

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", commit)

    def withdraw():
        return service.record_author_consent(author, withdrawal)

    def consume():
        return ctx["ready_app"].transition_publication_ready(author, ctx["ready_command"])

    try:
        with (
            ThreadPoolExecutor(1, thread_name_prefix="b16-first") as first_pool,
            ThreadPoolExecutor(1) as second_pool,
        ):
            first = first_pool.submit(withdraw if withdrawal_first else consume)
            assert entered.wait(10)
            second = second_pool.submit(consume if withdrawal_first else withdraw)
            try:
                _wait_for_pg_blocker(engine, holder[0], "relation")
            finally:
                release.set()
            a, b = first.result(15), second.result(15)
        consumed = b if withdrawal_first else a
        withdrawn = a if withdrawal_first else b
        assert consumed.grant_id == ctx["ready_command"].grant_id
        # PREPARE is legal only after READY. Issue real grants at that point,
        # then prove a new withdrawal stales them without altering READY history.
        ctx["basis"] = DecisionService(
            factory, credentials, LiteratureEvidenceService(factory, credentials, store), store
        ).record_prepare_submission_decision(
            ctx["decider"],
            RecordPrepareSubmissionDecisionCommand(
                uuid4(),
                command.project_id,
                command.manuscript_version_id,
                "Prepare?",
                "Independent preparation basis",
            ),
        )
        grants = [issue_grant(ctx), issue_grant(ctx)]
        regrant = service.record_author_consent(
            author, successor(ctx["consent"], withdrawn, "GRANTED")
        )
        # Also overlap exact consumption replay with the withdrawal that has
        # nonempty PREPARE scope. The retained READY receipt stays readable while
        # the withdrawal transaction holds its locks and stales those grants.
        staling, finish = Event(), Event()
        constraints = SqlAlchemyPreparedSubmissionRepository.force_constraints

        def pause_staling(self):
            constraints(self)
            staling.set()
            assert finish.wait(10)

        monkeypatch.setattr(
            SqlAlchemyPreparedSubmissionRepository, "force_constraints", pause_staling
        )
        with ThreadPoolExecutor(2) as pool:
            pending = pool.submit(
                service.record_author_consent, author, successor(ctx["consent"], regrant)
            )
            try:
                assert staling.wait(10)
                assert pool.submit(consume).result(5) == consumed
            finally:
                finish.set()
            pending.result(15)
        assert consume() == consumed
        with engine.connect() as conn:
            states = dict(conn.execute(text("SELECT id,status FROM approval_grants")).all())
            assert states[consumed.grant_id] == "CONSUMED"
            assert all(states[g.id] == "STALE" for g in grants)
            assert (
                conn.execute(
                    text("SELECT lifecycle_status FROM publications WHERE id=:id"),
                    {"id": command.publication_id},
                ).scalar_one()
                == "READY"
            )
            assert (
                conn.execute(text("SELECT count(*) FROM approval_grant_consumptions")).scalar_one()
                == 1
            )
    finally:
        release.set()
