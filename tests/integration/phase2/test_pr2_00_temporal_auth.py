from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event, get_ident
from time import monotonic
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine

from researchbase.application.phase2_identity import BootstrapAuthority, CloseProjectRole
from researchbase.application.strategy_candidate_promotion import ExactStrategyQuery
from researchbase.domain.phase2_identity import VerifiedPrincipal, effective_owner
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.strategy_candidate_promotion_repository import S
from researchbase.persistence.strategy_candidate_promotion_repository import (
    SqlAlchemyStrategyCandidatePromotionRepository as Repository,
)
from tests.integration.phase2.b02_support import capture, count, qcommand
from tests.integration.phase2.r1_support import (
    _BootstrapProofVerifier,
    _ExpiringCredentialVerifier,
    _service,
    _witness,
)


def test_owner_credential_expiry_changes_effective_authority_without_database_mutation(
    phase2_database_url: str,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    with engine.connect() as connection:
        expires_at = connection.execute(
            text("SELECT clock_timestamp() + interval '2 minutes'")
        ).scalar_one()

    operator = VerifiedPrincipal(
        actor_id=uuid4(),
        deployment_id="deployment-temporal-owner",
        subject_kind="OS_UID",
        subject_value="901",
        credential_id="os-credential-901",
        verified_at=datetime.now(UTC),
    )
    verifier = _ExpiringCredentialVerifier(expires_at)
    service, _unused_operator, _unused_subject = _service(
        phase2_database_url,
        credential_verifier=verifier,
        bootstrap_proof_verifier=_BootstrapProofVerifier(),
    )
    try:
        result = service.bootstrap_first_owner(
            BootstrapAuthority(
                deployment_id=operator.deployment_id,
                operator=operator,
                verified_os_uid=901,
                subject_credential_id=operator.credential_id,
                secret_digest_id="secret-digest-ref",
                proof_sha256="1" * 64,
                proof_record_ref="audit/sha256/temporal-owner",
            ),
            request_id=uuid4(),
            display_name="Temporal Owner",
            project_name="Temporal project",
        )
        principal = VerifiedPrincipal(
            actor_id=result.actor_id,
            deployment_id=operator.deployment_id,
            subject_kind=operator.subject_kind,
            subject_value=operator.subject_value,
            credential_id=operator.credential_id,
            verified_at=operator.verified_at,
        )
        with engine.connect() as connection:
            role = (
                connection.execute(
                    text(
                        "SELECT r.effective_from, r.effective_until, m.started_at, m.status, "
                        "a.retired_at, b.status AS binding_status, b.bound_at, b.revoked_at "
                        "FROM project_role_assignments r "
                        "JOIN project_memberships m ON m.id = r.membership_id "
                        "JOIN actors a ON a.id = r.actor_id "
                        "JOIN actor_subject_bindings b ON b.actor_id = a.id "
                        "WHERE r.id = :id"
                    ),
                    {"id": result.role_assignment_id},
                )
                .mappings()
                .one()
            )
            before = connection.execute(
                text(
                    "SELECT (SELECT count(*) FROM project_role_assignments), "
                    "(SELECT count(*) FROM project_role_events)"
                )
            ).one()

        def role_valid_at(at: datetime) -> bool:
            return bool(
                role["effective_from"] <= at
                and (role["effective_until"] is None or role["effective_until"] > at)
                and role["status"] == "ACTIVE"
                and role["started_at"] <= at
                and role["binding_status"] == "ACTIVE"
                and role["bound_at"] <= at
                and (role["revoked_at"] is None or role["revoked_at"] > at)
                and role["retired_at"] is None
            )

        assert effective_owner(
            role_valid=role_valid_at(expires_at - timedelta(microseconds=1)),
            membership_valid=True,
            actor_retired=False,
            principal=principal,
            verifier=verifier,
            at=expires_at - timedelta(microseconds=1),
        )
        assert not effective_owner(
            role_valid=role_valid_at(expires_at + timedelta(microseconds=1)),
            membership_valid=True,
            actor_retired=False,
            principal=principal,
            verifier=verifier,
            at=expires_at + timedelta(microseconds=1),
        )
        with engine.connect() as connection:
            after = connection.execute(
                text(
                    "SELECT (SELECT count(*) FROM project_role_assignments), "
                    "(SELECT count(*) FROM project_role_events)"
                )
            ).one()
            assert after == before
            assert (
                connection.execute(
                    text("SELECT effective_until FROM project_role_assignments WHERE id = :id"),
                    {"id": result.role_assignment_id},
                ).scalar_one()
                is None
            )
    finally:
        engine.dispose()


def _schedule_capture_owner_expiry(e, seconds=3):
    with e["engine"].connect() as connection:
        role = connection.execute(
            text(
                "SELECT id FROM project_role_assignments WHERE project_id=:project "
                "AND actor_id=:actor AND role='OWNER' AND effective_until IS NULL"
            ),
            {"project": e["project"], "actor": e["principal"].actor_id},
        ).scalar_one()
        expiry = connection.execute(
            text("SELECT clock_timestamp() + make_interval(secs => :seconds)"),
            {"seconds": seconds},
        ).scalar_one()
    identity, _, _ = _service(
        e["engine"].url.render_as_string(hide_password=False),
        credential_verifier=e["credentials"],
    )
    identity.close_project_role(
        CloseProjectRole(e["principal"], e["project"], role, "R1 expiry", uuid4(), expiry)
    )
    return expiry


def test_scheduled_expiry_denies_writer_after_observed_share_lock_wait(b02_env, monkeypatch):
    e = b02_env
    saved = capture(e)
    expiry = _schedule_capture_owner_expiry(e)
    samples, acquired, statements = [], [], []
    original_at, original_prepare = Repository.at, Repository.prepare_write

    observer_thread = get_ident()

    def observe(conn, cursor, statement, parameters, context, executemany):
        if get_ident() != observer_thread:
            statements.append(statement)

    def at(repo):
        value = original_at(repo)
        samples.append(value)
        return value

    def prepare(repo, *args):
        original_prepare(repo, *args)
        acquired.append(original_at(repo))
        assert repo._session.execute(text("SHOW transaction_isolation")).scalar_one() == (
            "read committed"
        )

    monkeypatch.setattr(Repository, "at", at)
    monkeypatch.setattr(Repository, "prepare_write", prepare)
    tables = ("strategy_question_admissions", "research_questions", "research_question_versions")
    before = [count(e, table) for table in tables]
    with e["engine"].connect() as blocker, ThreadPoolExecutor(max_workers=1) as pool:
        tx = blocker.begin()
        blocker.execute(text("LOCK TABLE projects IN ROW EXCLUSIVE MODE"))
        pid = blocker.execute(text("SELECT pg_backend_pid()")).scalar_one()
        # Retain only the worker thread SQL, excluding blocker/observer connections.
        event.listen(Engine, "before_cursor_execute", observe)
        try:
            future = pool.submit(
                e["service"].promote_strategy_question, e["principal"], qcommand(e, saved)
            )
            waiter = _witness(e["engine"], pid, before=expiry)
            with e["engine"].connect() as observer:
                started, observed = observer.execute(
                    text(
                        "SELECT xact_start,clock_timestamp() FROM pg_stat_activity WHERE pid=:pid"
                    ),
                    {"pid": waiter},
                ).one()
            deadline = monotonic() + 10
            while blocker.execute(text("SELECT clock_timestamp()")).scalar_one() < expiry:
                assert monotonic() < deadline
                Event().wait(0.01)
            tx.commit()
            with pytest.raises(ResearchBaseError) as caught:
                future.result(timeout=15)
        finally:
            if tx.is_active:
                tx.rollback()
            event.remove(Engine, "before_cursor_execute", observe)
    assert statements[0] == "LOCK TABLE " + ",".join(S) + " IN SHARE MODE"
    assert caught.value.code is ErrorCode.FORBIDDEN
    assert [count(e, table) for table in tables] == before
    assert started < expiry and observed < expiry <= acquired[0] <= samples[0]
    assert samples[0] > expiry
    print(
        "R1_SCHEDULED_EXPIRY",
        {
            "tx_started_at": str(started),
            "expiry_at": str(expiry),
            "lock_wait_started_at": str(observed),
            "lock_acquired_at": str(acquired[0]),
            "authorization_checked_at": str(samples[0]),
            "outcome": caught.value.code.value,
            "persisted_effect_counts": [0, 0, 0],
        },
    )


def test_scheduled_expiry_reads_use_lock_free_read_only_snapshots(b02_env, monkeypatch):
    e = b02_env
    saved = capture(e)
    expiry = _schedule_capture_owner_expiry(e)
    original_at = Repository.at
    statements = []

    def observe(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    def at(repo):
        value = original_at(repo)
        assert repo._session.execute(text("SHOW transaction_isolation")).scalar_one() == (
            "repeatable read"
        )
        assert repo._session.execute(text("SHOW transaction_read_only")).scalar_one() == "on"
        pid = repo._session.execute(text("SELECT pg_backend_pid()")).scalar_one()
        with e["engine"].connect() as observer:
            assert (
                observer.execute(
                    text("""
                SELECT count(*) FROM pg_locks WHERE pid=:pid AND
                    (locktype IN ('advisory','tuple') OR
                     (locktype='relation' AND mode NOT IN ('AccessShareLock','SIReadLock')))
            """),
                    {"pid": pid},
                ).scalar_one()
                == 0
            )
        return value

    monkeypatch.setattr(Repository, "at", at)
    event.listen(Engine, "before_cursor_execute", observe)
    try:
        assert (
            e["service"].get_strategy_capture(
                e["principal"], ExactStrategyQuery(saved.id, e["project"])
            )
            == saved
        )
        deadline = monotonic() + 10
        with e["engine"].connect() as observer:
            while observer.execute(text("SELECT clock_timestamp()")).scalar_one() < expiry:
                assert monotonic() < deadline
                Event().wait(0.01)
        with pytest.raises(ResearchBaseError) as caught:
            e["service"].get_strategy_capture(
                e["principal"], ExactStrategyQuery(saved.id, e["project"])
            )
        assert caught.value.code is ErrorCode.FORBIDDEN
    finally:
        event.remove(Engine, "before_cursor_execute", observe)
    assert not any(
        token in statement.upper()
        for statement in statements
        for token in ("LOCK TABLE", "PG_ADVISORY", "FOR UPDATE", "FOR SHARE")
    )
