"""B15 real backend wait witnesses, snapshots, atomic retries and parent exclusion."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from functools import partial
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError

from researchbase.application.prepared_submission import (
    GetAuthorConsentQuery,
    GetPreparedSubmissionQuery,
    WithdrawPreparedSubmissionCommand,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.prepared_submission_repository import (
    B15_SHARE_SQL,
    SqlAlchemyPreparedSubmissionRepository,
)
from tests.integration.phase2.b15_support import (  # noqa: F401
    b04_env as _b04_env,
)
from tests.integration.phase2.b15_support import (
    b15_env as _b15_env,
)
from tests.integration.phase2.b15_support import (
    conclusion_env as _conclusion_env,
)
from tests.integration.phase2.b15_support import (
    consent_command,
    prepared,
)
from tests.integration.phase2.test_b13_grant_consumption import approval_env as _approval_env
from tests.integration.phase2.test_b13_grant_consumption import decision_env as _decision_env
from tests.integration.phase2.test_b13_grant_consumption import issued
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

b04_env = _b04_env
b15_env = _b15_env
conclusion_env = _conclusion_env
approval_env = _approval_env
decision_env = _decision_env

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "kind",
    [
        "package",
        "history",
        "preview",
        "consent",
        "prepare_replay",
        "consent_replay",
        "withdraw_replay",
    ],
)
def test_all_reads_and_nested_verifiers_are_lock_free(b15_env, kind):
    service, command, actor, _, engine, *_ = b15_env
    package, query = prepared(b15_env)
    cmd = consent_command(b15_env, package.id)
    root = service.record_author_consent(actor, cmd)
    withdraw = WithdrawPreparedSubmissionCommand(command.project_id, package.id, "withdraw")
    if kind == "withdraw_replay":
        service.withdraw_prepared_submission(actor, withdraw)
    operations = {
        "package": lambda: service.get_prepared_submission(actor, query),
        "history": lambda: service.get_prepared_submission_history(actor, query),
        "preview": lambda: service.preview_prepared_submission(actor, query),
        "consent": lambda: service.get_author_consent(
            actor, GetAuthorConsentQuery(command.project_id, root.id)
        ),
        "prepare_replay": lambda: service.prepare_submission(actor, command),
        "consent_replay": lambda: service.record_author_consent(actor, cmd),
        "withdraw_replay": lambda: service.withdraw_prepared_submission(actor, withdraw),
    }
    observed = []

    def capture(conn, cursor, statement, params, context, many):
        observed.append(statement)
        assert (
            not statement.lstrip()
            .upper()
            .startswith(("LOCK ", "INSERT ", "UPDATE ", "DELETE ", "SET CONSTRAINTS"))
        )
        assert "FOR UPDATE" not in statement.upper() and "FOR SHARE" not in statement.upper()
        assert "PG_ADVISORY" not in statement.upper()

    event.listen(engine, "before_cursor_execute", capture)
    try:
        operations[kind]()
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert len(observed) > 3


@pytest.mark.parametrize("operation", ["prepare", "consent", "withdraw"])
def test_write_first_sql_inventory_and_read_committed(b15_env, monkeypatch, operation):
    service, command, actor, _, engine, *_ = b15_env
    action: Callable[[], object]
    if operation == "prepare":
        action = partial(service.prepare_submission, actor, command)
    else:
        package, _ = prepared(b15_env)
        if operation == "consent":
            consent = consent_command(b15_env, package.id)
            action = partial(service.record_author_consent, actor, consent)
        else:
            withdrawal = WithdrawPreparedSubmissionCommand(command.project_id, package.id, "stop")
            action = partial(service.withdraw_prepared_submission, actor, withdrawal)
    original = SqlAlchemyPreparedSubmissionRepository.prepare_write
    transactions = []

    def begin(conn):
        transactions.append([])
        conn.info["b15_sql"] = transactions[-1]

    def capture(conn, cursor, statement, params, context, many):
        conn.info["b15_sql"].append(statement)

    def prepare(self):
        original(self)
        assert (
            self._session.execute(text("SHOW transaction_isolation")).scalar_one()
            == "read committed"
        )

    event.listen(engine, "begin", begin)
    event.listen(engine, "before_cursor_execute", capture)
    monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, "prepare_write", prepare)
    try:
        action()
    finally:
        event.remove(engine, "begin", begin)
        event.remove(engine, "before_cursor_execute", capture)
    writes = [tx for tx in transactions if B15_SHARE_SQL in tx]
    assert len(writes) == 1 and writes[0][0] == B15_SHARE_SQL


@pytest.mark.parametrize("same_uuid", [True, False])
def test_prepare_serialization_with_observed_parent_wait(b15_env, same_uuid):
    service, command, actor, _, engine, *_ = b15_env
    other = command if same_uuid else replace(command, id=uuid4())
    with engine.connect() as holder:
        tx = holder.begin()
        holder_pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        holder.execute(
            text("SELECT id FROM manuscript_versions WHERE id=:id FOR UPDATE"),
            {"id": command.manuscript_version_id},
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(service.prepare_submission, actor, command)
            witness = _wait_for_pg_blocker(engine, holder_pid, "transactionid")
            b = pool.submit(service.prepare_submission, actor, other)
            if same_uuid:
                _wait_for_pg_blocker(engine, witness["pid"], "advisory")
            tx.commit()
            results = [a.result(15), b.result(15)]
    if same_uuid:
        assert results[0] == results[1]
    else:
        assert sorted(r.version_number for r in results) == [1, 2]


@pytest.mark.parametrize("first", ["consent", "withdraw"])
def test_consent_withdrawal_both_orders(b15_env, first, monkeypatch):
    service, command, actor, _, engine, *_ = b15_env
    package, query = prepared(b15_env)
    cmd = consent_command(b15_env, package.id)
    withdraw = WithdrawPreparedSubmissionCommand(command.project_id, package.id, "terminal")
    entered, release = Event(), Event()
    original = SqlAlchemyPreparedSubmissionRepository.force_constraints
    first_pid = []

    def pause(self):
        original(self)
        if not entered.is_set():
            first_pid.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(10)

    monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, "force_constraints", pause)
    actions = {
        "consent": lambda: service.record_author_consent(actor, cmd),
        "withdraw": lambda: service.withdraw_prepared_submission(actor, withdraw),
    }

    def run(kind):
        try:
            return actions[kind]()
        except ResearchBaseError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(run, first)
        assert entered.wait(10)
        b = pool.submit(run, "withdraw" if first == "consent" else "consent")
        try:
            _wait_for_pg_blocker(engine, first_pid[0], "transactionid")
        finally:
            release.set()
        a.result(15)
        second = b.result(15)
    saved = service.get_prepared_submission(actor, query)
    assert saved.status == "WITHDRAWN"
    assert len(saved.consents) == (1 if first == "consent" else 0)
    if first == "withdraw":
        assert second == ErrorCode.INVALID_STATE_TRANSITION


@pytest.mark.parametrize(
    "state,expected_attempts", [("40001", 3), ("40P01", 3), ("55P03", 1), ("23505", 1)]
)
def test_exact_retry_budget_and_zero_partial_rows(b15_env, monkeypatch, state, expected_attempts):
    service, command, actor, _, engine, *_ = b15_env
    attempts = []
    original = SqlAlchemyPreparedSubmissionRepository.insert_package

    class Conflict(Exception):
        sqlstate = state

    def injected(self, row):
        original(self, row)
        attempts.append(row["id"])
        raise DBAPIError("insert", {}, Conflict(), False)

    monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, "insert_package", injected)
    with pytest.raises(ResearchBaseError) as exc:
        service.prepare_submission(actor, command)
    assert exc.value.code == ErrorCode.CONCURRENT_MODIFICATION
    assert len(attempts) == expected_attempts
    with engine.connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM prepared_submission_versions")).scalar_one()
            == 0
        )


@pytest.mark.parametrize("wait_at", ["inventory", "manuscript"])
def test_credentials_expire_during_observed_required_wait(b15_env, wait_at, monkeypatch):
    from researchbase.application.prepared_submission import PreparedSubmissionService

    service, command, actor, factory, engine, store, original_credentials = b15_env
    timeline = {}

    class Expiring:
        expiry = None

        def is_valid(self, principal, at):
            timeline["authorization_checked_at"] = at
            return original_credentials.is_valid(principal, at) and (
                self.expiry is None or at < self.expiry
            )

    credentials = Expiring()
    original_parent = SqlAlchemyPreparedSubmissionRepository.parent
    original_coordinate = SqlAlchemyPreparedSubmissionRepository.coordinate

    def parent(self, identity, *, lock=False):
        result = original_parent(self, identity, lock=lock)
        if lock and wait_at == "manuscript":
            timeline["lock_acquired_at"] = self.at()
        return result

    def coordinate(self, key):
        if wait_at == "inventory":
            timeline["lock_acquired_at"] = self.at()
        return original_coordinate(self, key)

    monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, "parent", parent)
    monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, "coordinate", coordinate)
    service = PreparedSubmissionService(factory, credentials, store)
    with engine.connect() as holder:
        tx = holder.begin()
        holder_pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        if wait_at == "inventory":
            holder.execute(text("LOCK TABLE actors IN ROW EXCLUSIVE MODE"))
        else:
            holder.execute(
                text("SELECT id FROM manuscript_versions WHERE id=:id FOR UPDATE"),
                {"id": command.manuscript_version_id},
            )
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(service.prepare_submission, actor, command)
            witness = _wait_for_pg_blocker(
                engine, holder_pid, "relation" if wait_at == "inventory" else "transactionid"
            )
            with engine.connect() as observer:
                tx_started = observer.execute(
                    text("SELECT xact_start FROM pg_stat_activity WHERE pid=:pid"),
                    {"pid": witness["pid"]},
                ).scalar_one()
                expiry = observer.execute(text("SELECT clock_timestamp()")).scalar_one()
            credentials.expiry = expiry
            timeline.update(
                tx_started_at=tx_started,
                expiry_at=expiry,
                lock_wait_started_at=witness["observed_at"],
            )
            tx.commit()
            with pytest.raises(ResearchBaseError) as exc:
                future.result(15)
        assert exc.value.code == ErrorCode.AUTHENTICATION_REQUIRED
    assert (
        timeline["tx_started_at"]
        < timeline["expiry_at"]
        <= timeline["lock_acquired_at"]
        <= timeline["authorization_checked_at"]
    )
    with engine.connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM prepared_submission_versions")).scalar_one()
            == 0
        )
    print("B15_R4_WAIT", {**{k: str(v) for k, v in timeline.items()}, "failed_effect_count": 0})


def test_competing_consent_roots_have_one_winner(b15_env):
    from threading import Barrier

    service, _, actor, _, engine, *_ = b15_env
    package, _ = prepared(b15_env)
    cmd = consent_command(b15_env, package.id)
    barrier = Barrier(2)

    def run(command):
        barrier.wait(5)
        try:
            return service.record_author_consent(actor, command)
        except ResearchBaseError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, c) for c in (cmd, replace(cmd, id=uuid4()))]
        results = [f.result(15) for f in futures]
    assert sum(r == ErrorCode.CONCURRENT_MODIFICATION for r in results) == 1
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM author_consents")).scalar_one() == 1


@pytest.mark.parametrize("writer", ["artifact", "source", "authority"])
@pytest.mark.parametrize("package_first", [True, False])
def test_participating_writer_inventory_excludes_phantoms(
    b15_env, b04_env, monkeypatch, writer, package_first
):
    """Accepted writers commit on either side of the package snapshot."""
    from threading import current_thread

    from researchbase.application.phase2_identity import AssignProjectRole
    from researchbase.application.source_identity import (
        RegisterLiteratureSource,
        SourceIdentityService,
    )
    from researchbase.domain.source_identity import SourceKind
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork
    from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service
    from tests.integration.phase2.test_pr2_10_binding_contract import _artifact

    service, command, actor, factory, engine, store, _ = b15_env
    entered, release = Event(), Event()
    holder_pid = []
    original = SqlAlchemyUnitOfWork.commit

    def commit(self):
        if current_thread().name.startswith("b15-first") and not entered.is_set():
            self._session.flush()
            holder_pid.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(10)
        return original(self)

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", commit)
    identity, _, _ = identity_service(engine.url.render_as_string(hide_password=False))
    sources = SourceIdentityService(factory, b15_env[-1])
    actions = {
        "package": lambda: service.prepare_submission(actor, command),
        "artifact": lambda: _artifact(
            factory, store, actor, command.project_id, b"concurrent science artifact"
        ),
        "source": lambda: sources.register_literature_source(
            RegisterLiteratureSource(
                actor, command.project_id, SourceKind.PAPER, "Concurrent source", uuid4()
            )
        ),
        "authority": lambda: identity.assign_project_role(
            AssignProjectRole(
                actor,
                command.project_id,
                actor.actor_id,
                "VIEWER",
                "concurrent entitlement",
                uuid4(),
            )
        ),
    }
    first = "package" if package_first else writer
    second = writer if package_first else "package"
    with (
        ThreadPoolExecutor(max_workers=1, thread_name_prefix="b15-first") as owner,
        ThreadPoolExecutor(max_workers=1) as other,
    ):
        a = owner.submit(actions[first])
        assert entered.wait(10)
        b = other.submit(actions[second])
        try:
            witness = _wait_for_pg_blocker(
                engine,
                holder_pid[0],
                "transactionid" if package_first and writer == "authority" else "relation",
            )
            assert witness["pid"] != holder_pid[0]
        finally:
            release.set()
        a.result(15)
        b.result(15)
    assert (
        service.get_prepared_submission(
            actor, GetPreparedSubmissionQuery(command.project_id, command.id)
        ).id
        == command.id
    )


@pytest.mark.parametrize("first", ["package", "decision"])
def test_b12_participates_in_shared_parent_order(b15_env, b04_env, first, monkeypatch):
    from threading import current_thread

    from researchbase.application.decision import (
        DecisionService,
        RecordPrepareSubmissionDecisionCommand,
    )
    from researchbase.persistence.internal_review_repository import (
        SqlAlchemyInternalReviewRepository,
    )
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    service, command, actor, factory, engine, _, credentials = b15_env
    policy = DecisionService(factory, credentials, b04_env[-1][2], b15_env[5])
    decision = RecordPrepareSubmissionDecisionCommand(
        uuid4(),
        command.project_id,
        command.manuscript_version_id,
        "Prepare",
        "Independent judgment",
    )
    entered, release = Event(), Event()
    holder = []

    def pause(session):
        holder.append(session.execute(text("SELECT pg_backend_pid()")).scalar_one())
        entered.set()
        assert release.wait(10)

    original_commit = SqlAlchemyUnitOfWork.commit
    original_lock = SqlAlchemyInternalReviewRepository.lock_publication

    def commit(self):
        if (
            first == "package"
            and current_thread().name.startswith("b15-first")
            and not entered.is_set()
        ):
            pause(self._session)
        return original_commit(self)

    def lock(self, *args, **kwargs):
        result = original_lock(self, *args, **kwargs)
        if (
            first == "decision"
            and current_thread().name.startswith("b15-first")
            and not entered.is_set()
        ):
            pause(self._session)
        return result

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", commit)
    monkeypatch.setattr(SqlAlchemyInternalReviewRepository, "lock_publication", lock)

    def record():
        try:
            return policy.record_prepare_submission_decision(actor, decision)
        except ResearchBaseError as error:
            return error.code

    actions = {"package": lambda: service.prepare_submission(actor, command), "decision": record}
    with (
        ThreadPoolExecutor(1, thread_name_prefix="b15-first") as owner,
        ThreadPoolExecutor(1) as other,
    ):
        a = owner.submit(actions[first])
        assert entered.wait(10)
        b = other.submit(actions["decision" if first == "package" else "package"])
        try:
            _wait_for_pg_blocker(engine, holder[0], "transactionid")
        finally:
            release.set()
        results = [a.result(15), b.result(15)]
    assert ErrorCode.INVALID_STATE_TRANSITION in results
    with engine.connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM prepared_submission_versions")).scalar_one()
            == 1
        )
        assert conn.execute(text("SELECT count(*) FROM decision_records")).scalar_one() == 0


@pytest.mark.parametrize("first", ["package", "grant"])
def test_b13_maintenance_and_package_both_commit_orders(b15_env, approval_env, first, monkeypatch):
    from threading import current_thread

    from researchbase.application.approval import EvaluateApprovalGrantCommand
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    service, command, actor, _, engine, *_ = b15_env
    _, grant_actor, grant_command, grant = issued(approval_env)
    entered, release = Event(), Event()
    holder = []
    original = SqlAlchemyUnitOfWork.commit

    def commit(self):
        if current_thread().name.startswith("b15-first") and not entered.is_set():
            holder.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(10)
        return original(self)

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", commit)
    actions = {
        "package": lambda: service.prepare_submission(actor, command),
        "grant": lambda: approval_env[0].evaluate_approval_grant(
            grant_actor, EvaluateApprovalGrantCommand(grant_command.project_id, grant.id)
        ),
    }
    with (
        ThreadPoolExecutor(1, thread_name_prefix="b15-first") as owner,
        ThreadPoolExecutor(1) as other,
    ):
        a = owner.submit(actions[first])
        assert entered.wait(10)
        b = other.submit(actions["grant" if first == "package" else "package"])
        try:
            witness = _wait_for_pg_blocker(engine, holder[0], "relation")
            assert witness["relation"] == "publications"
        finally:
            release.set()
        a.result(15)
        b.result(15)
    with engine.connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM prepared_submission_versions")).scalar_one()
            == 1
        )
        assert (
            conn.execute(text("SELECT count(*) FROM approval_grant_consumptions")).scalar_one() == 0
        )
        assert conn.execute(text("SELECT count(*) FROM approval_grant_events")).scalar_one() == 1


def test_target_first_writer_deadlock_recovers_without_partial_package(b15_env, monkeypatch):
    service, command, actor, _, engine, *_ = b15_env
    attempts = []
    deadlocks = []
    original = SqlAlchemyPreparedSubmissionRepository.prepare_write

    def prepare(self):
        attempts.append(self._session)
        return original(self)

    def error(context):
        if getattr(context.original_exception, "sqlstate", None) == "40P01":
            deadlocks.append(True)

    monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, "prepare_write", prepare)
    event.listen(engine, "handle_error", error)
    try:
        with engine.connect() as holder:
            tx = holder.begin()
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            holder.execute(
                text("SELECT id FROM manuscript_versions WHERE id=:id FOR UPDATE"),
                {"id": command.manuscript_version_id},
            )
            with ThreadPoolExecutor(1) as pool:
                future = pool.submit(service.prepare_submission, actor, command)
                _wait_for_pg_blocker(engine, pid, "transactionid")
                try:
                    holder.execute(
                        text(
                            "INSERT INTO actors(id,actor_type,display_name,created_at) "
                            "VALUES(:id,'HUMAN','deadlock writer',clock_timestamp())"
                        ),
                        {"id": uuid4()},
                    )
                    tx.commit()
                except DBAPIError as exc:
                    assert getattr(exc.orig, "sqlstate", None) == "40P01"
                    tx.rollback()
                result = future.result(20)
        assert result.id == command.id and 1 <= len(attempts) <= 3 and deadlocks
        with engine.connect() as conn:
            assert (
                conn.execute(text("SELECT count(*) FROM prepared_submission_versions")).scalar_one()
                == 1
            )
            assert (
                conn.execute(text("SELECT count(*) FROM prepared_submission_events")).scalar_one()
                == 1
            )
    finally:
        event.remove(engine, "handle_error", error)


def test_read_nested_material_and_entitlement_share_one_snapshot(b15_env, monkeypatch):
    from threading import current_thread

    from researchbase.persistence.authorship_repository import SqlAlchemyAuthorshipRepository

    service, _, actor, _, engine, *_ = b15_env
    package, query = prepared(b15_env)
    entered, release = Event(), Event()
    phantom = uuid4()
    original = SqlAlchemyAuthorshipRepository.authority
    reader_pid = []

    def authority(self, *args):
        rows = original(self, *args)
        if current_thread().name.startswith("b15-reader") and not entered.is_set():
            assert (
                self._session.execute(text("SHOW transaction_isolation")).scalar_one()
                == "repeatable read"
            )
            assert self._session.execute(text("SHOW transaction_read_only")).scalar_one() == "on"
            reader_pid.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(10)
            assert (
                self._session.execute(
                    text("SELECT count(*) FROM actors WHERE id=:id"), {"id": phantom}
                ).scalar_one()
                == 0
            )
        return rows

    monkeypatch.setattr(SqlAlchemyAuthorshipRepository, "authority", authority)
    with ThreadPoolExecutor(1, thread_name_prefix="b15-reader") as pool:
        future = pool.submit(service.get_prepared_submission, actor, query)
        assert entered.wait(10)
        try:
            with engine.begin() as conn:
                assert conn.execute(text("SELECT pg_backend_pid()")).scalar_one() != reader_pid[0]
                modes = conn.execute(
                    text(
                        "SELECT mode FROM pg_locks WHERE pid=:pid AND (locktype='advisory' "
                        "OR mode IN ('ShareLock','RowShareLock','RowExclusiveLock'))"
                    ),
                    {"pid": reader_pid[0]},
                ).all()
                assert modes == []
                conn.execute(
                    text(
                        "INSERT INTO actors(id,actor_type,display_name,created_at) "
                        "VALUES(:id,'HUMAN','snapshot phantom',clock_timestamp())"
                    ),
                    {"id": phantom},
                )
        finally:
            release.set()
        assert future.result(15) == package


def test_expiry_at_equality_after_deferred_checks_denies_effect(b15_env, monkeypatch):
    from researchbase.application.prepared_submission import PreparedSubmissionService
    from researchbase.persistence.authorship_repository import SqlAlchemyAuthorshipRepository

    _, command, actor, factory, engine, store, original_credentials = b15_env
    observed = {}

    class Expiring:
        def is_valid(self, principal, at):
            observed["authorization_checked_at"] = at
            return original_credentials.is_valid(principal, at) and (
                "expiry_at" not in observed or at < observed["expiry_at"]
            )

    service = PreparedSubmissionService(factory, Expiring(), store)
    original_at = SqlAlchemyAuthorshipRepository.at
    original_constraints = SqlAlchemyPreparedSubmissionRepository.force_constraints

    def at(self):
        return observed.get("expiry_at") or original_at(self)

    def constraints(self):
        original_constraints(self)
        observed["expiry_at"] = original_at(self)

    monkeypatch.setattr(SqlAlchemyAuthorshipRepository, "at", at)
    monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, "force_constraints", constraints)
    with pytest.raises(ResearchBaseError) as exc:
        service.prepare_submission(actor, command)
    assert exc.value.code == ErrorCode.AUTHENTICATION_REQUIRED
    assert observed["authorization_checked_at"] == observed["expiry_at"]
    with engine.connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM prepared_submission_versions")).scalar_one()
            == 0
        )
