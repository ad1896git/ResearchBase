"""Barrier-controlled PostgreSQL snapshot consistency and absence of explicit locks."""

# ruff: noqa: E501

from concurrent.futures import ThreadPoolExecutor
from threading import Event, current_thread
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from researchbase.application.internal_review import ReviewIssueRequest
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.manuscript_freeze_repository import (
    SqlAlchemyManuscriptFreezeRepository,
)
from tests.integration.phase2.b25_support import impact, place, queries
from tests.integration.phase2.test_b05_manuscript_review import (  # noqa: F401
    b04_env as _b04_env,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    b05_env as _b05_env,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    conclusion_env as _conclusion_env,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    create,
    seal,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    phase2_database_url as _phase2_database_url,
)

b04_env = _b04_env
b05_env = _b05_env
conclusion_env = _conclusion_env
phase2_database_url = _phase2_database_url

pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "change",
    [
        "review",
        "issue",
        "invalidation",
        "unrelated",
        "expiry",
        "freeze",
        "verification",
        "retraction",
    ],
)
def test_one_complete_nonblocking_snapshot(b05_env, monkeypatch, change):
    env = b05_env
    literature_evidence = None
    if change in {"verification", "retraction"}:
        from tests.integration.phase2.b25_support import literature_conclusion

        literature_evidence, _, _ = literature_conclusion(env)
    else:
        place(env)
    if change != "freeze":
        seal(env)
    existing = create(env) if change == "issue" else None
    service, q, aq = queries(env)
    entered, release = Event(), Event()
    statements = []
    original = SqlAlchemyManuscriptFreezeRepository.authority
    reader_authorizations = 0

    def capture(conn, cursor, sql, params, context, many):
        if current_thread().name.startswith("b25-reader"):
            statements.append(sql)

    def authority(self, *args):
        nonlocal reader_authorizations
        rows = original(self, *args)
        if current_thread().name.startswith("b25-reader"):
            reader_authorizations += 1
        pause_at = 2 if change == "expiry" else 1
        if current_thread().name.startswith("b25-reader") and reader_authorizations == pause_at:
            assert (
                self._session.execute(text("SHOW transaction_isolation")).scalar_one()
                == "repeatable read"
            )
            assert self._session.execute(text("SHOW transaction_read_only")).scalar_one() == "on"
            assert (
                self._session.execute(
                    text("""SELECT mode FROM pg_locks WHERE pid=pg_backend_pid()
                AND (locktype='advisory' OR mode IN ('ShareLock','RowShareLock','RowExclusiveLock'))""")
                ).all()
                == []
            )
            entered.set()
            assert release.wait(15)
        return rows

    monkeypatch.setattr(SqlAlchemyManuscriptFreezeRepository, "authority", authority)
    event.listen(env[5], "before_cursor_execute", capture)
    try:
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="b25-reader") as pool:
            future = pool.submit(service.get_manuscript_audit, env[3], aq)
            try:
                assert entered.wait(15)
                if change == "review":
                    create(
                        env,
                        issues=(
                            ReviewIssueRequest(
                                "BLOCKING", "UNSUPPORTED_CLAIM", "Concurrent review"
                            ),
                        ),
                    )
                elif change == "issue":
                    assert existing is not None
                    with env[4]() as uow:
                        uow.internal_review.insert_issue(
                            dict(
                                id=uuid4(),
                                review_record_id=existing.id,
                                severity="BLOCKING",
                                issue_type="UNSUPPORTED_CLAIM",
                                description="Concurrent issue",
                                ordinal=0,
                                created_at=uow.manuscript_freeze.at(),
                            )
                        )
                        uow.commit()
                elif change == "verification":
                    env[10][2].review(
                        env[3],
                        q.project_id,
                        literature_evidence,
                        "DISPUTED",
                        "Concurrent verification",
                        uuid4(),
                    )
                elif change == "retraction":
                    from tests.integration.phase2.b25_support import source_transition

                    source_transition(env, "RETRACTED")
                elif change == "invalidation":
                    impact(env, "claim_version", env[8], "invalid")
                elif change == "unrelated":
                    with env[5].begin() as conn:
                        conn.execute(
                            text(
                                "INSERT INTO actors(id,actor_type,display_name,created_at,row_version) VALUES (:id,'HUMAN','B25 unrelated',clock_timestamp(),1)"
                            ),
                            {"id": uuid4()},
                        )
                elif change == "expiry":
                    assert any("MANUSCRIPT_VERSIONS" in sql.upper() for sql in statements)
                    monkeypatch.setattr(env[9], "is_valid", lambda *args: False)
                elif change == "freeze":
                    seal(env)
            finally:
                release.set()
            if change in {"expiry", "freeze"}:
                with pytest.raises(ResearchBaseError) as error:
                    future.result(15)
                assert error.value.code == (
                    ErrorCode.FORBIDDEN if change == "expiry" else ErrorCode.VERSION_NOT_FROZEN
                )
            else:
                old = future.result(15)
                assert old.validity.current_validity == "VALID"
                assert old.unsupported_concerns == old.blocking_issue_ids == ()
                fresh = service.get_manuscript_audit(env[3], aq)
                if change in {"review", "issue"}:
                    assert len(fresh.unsupported_concerns) == len(fresh.blocking_issue_ids) == 1
                elif change in {"invalidation", "retraction"}:
                    assert fresh.validity.current_validity == "INVALID"
                elif change == "verification":
                    assert fresh.validity.current_validity == "STALE"
                else:
                    assert fresh.validity.current_validity == "VALID"
                assert old.validity.content_hash == fresh.validity.content_hash
        assert statements[0] == "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
        assert not any(
            any(
                token in sql.upper()
                for token in ("LOCK TABLE", "FOR UPDATE", "FOR SHARE", "ADVISORY_XACT")
            )
            for sql in statements
        )
        if change == "freeze":
            assert service.get_manuscript_validity(env[3], q).status == "FROZEN"
    finally:
        release.set()
        event.remove(env[5], "before_cursor_execute", capture)
