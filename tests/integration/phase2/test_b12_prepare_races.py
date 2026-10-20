"""B12 actual PostgreSQL waits and bounded fresh transaction retries."""

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.decision_repository import B11_SHARE_SQL, SqlAlchemyDecisionRepository
from tests.integration.phase2.test_b04_manuscript_migration import normal_sql_role
from tests.integration.phase2.test_b12_prepare_decision import (
    b04_env,
    b05_env,
    conclusion_env,
    decision_env,
    phase2_database_url,
    prepare_command,
    revision_env,
    seal,
    service,
)
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

_FIXTURES = (
    normal_sql_role,
    b04_env,
    b05_env,
    conclusion_env,
    phase2_database_url,
    decision_env,
    revision_env,
)
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("wait_at", ["inventory", "request", "target", "project", "publication"])
def test_expiry_after_observed_wait_denies_without_writes(b05_env, wait_at):
    env = b05_env
    seal(env)
    cmd = prepare_command(env)

    class Expiring:
        until = None

        def is_valid(self, principal, at):
            return env[9].is_valid(principal, at) and (self.until is None or at < self.until)

    credentials = Expiring()
    policy = service(env)
    policy._credentials = credentials
    other = create_engine(env[5].url)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            with other.begin() as holder:
                pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
                if wait_at == "inventory":
                    holder.execute(text("LOCK TABLE actors IN ROW EXCLUSIVE MODE"))
                    kind = "relation"
                elif wait_at == "request":
                    holder.execute(
                        text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                        {"key": f"b12:decision:{cmd.id}"},
                    )
                    kind = "advisory"
                else:
                    table, identity = {
                        "target": ("manuscript_versions", cmd.manuscript_version_id),
                        "project": ("projects", cmd.project_id),
                        "publication": ("publications", env[1].publication_id),
                    }[wait_at]
                    holder.execute(
                        text(f"SELECT id FROM {table} WHERE id=:id FOR UPDATE"), {"id": identity}
                    )
                    kind = "transactionid"
                future = pool.submit(policy.record_prepare_submission_decision, env[3], cmd)
                witness = _wait_for_pg_blocker(env[5], pid, kind)
                assert witness["pid"] != pid if "pid" in witness else True
                if wait_at == "inventory":
                    assert witness["query"] == B11_SHARE_SQL
                credentials.until = witness["observed_at"]
            with pytest.raises(ResearchBaseError) as exc:
                future.result(timeout=15)
            assert exc.value.code == ErrorCode.FORBIDDEN
        with env[5].connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM decision_records")).scalar_one() == 0
    finally:
        other.dispose()


@pytest.mark.parametrize(
    "state,attempts",
    [("40001", 3), ("40P01", 3), ("55P03", 1), ("57014", 1), ("P17F3", 1), ("XX000", 1)],
)
def test_exact_retryable_states_and_fresh_uows(b05_env, monkeypatch, state, attempts):
    env = b05_env
    sessions = []
    original = SqlAlchemyDecisionRepository.prepare_readiness_write

    def fail(self):
        original(self)
        sessions.append(self._session)
        raise DBAPIError(None, None, cast(Any, SimpleNamespace(sqlstate=state, diag=None)))

    monkeypatch.setattr(SqlAlchemyDecisionRepository, "prepare_readiness_write", fail)
    with pytest.raises(ResearchBaseError) as exc:
        service(env).record_prepare_submission_decision(env[3], prepare_command(env))
    assert len(sessions) == attempts and len({id(x) for x in sessions}) == attempts
    assert exc.value.code == (
        ErrorCode.IDEMPOTENCY_CONFLICT
        if state == "P17F3"
        else ErrorCode.INVALID_STATE_TRANSITION
        if state == "XX000"
        else ErrorCode.CONCURRENT_MODIFICATION
    )


@pytest.mark.parametrize("first", ["approval", "issue"])
def test_upstream_issue_serialized_by_full_approval_inventory(b05_env, normal_sql_role, first):
    """The former N race now excludes a blocker commit during the approval gate."""
    from uuid import uuid4

    from researchbase.persistence.approval_repository import B09_SHARE_SQL
    from tests.integration.phase2.test_b05_review_races import insert_sql
    from tests.integration.phase2.test_b11_readiness_decision import place_claim

    env = b05_env
    place_claim(env)
    seal(env)
    review = env[0].create(
        env[3],
        env[1].project_id,
        "CLAIM_VERSION",
        env[8],
        "SCIENTIFIC",
        "REJECT",
        "Upstream zero-Issue review",
        (),
        uuid4(),
    )

    def blockers(conn):
        return (
            conn.execute(
                text("""SELECT i.id FROM review_issues i
                JOIN b11_applicable_reviews(:target,:project) r ON r.id=i.review_record_id
                WHERE i.status='OPEN' AND i.severity='BLOCKING'"""),
                {"target": env[1].manuscript_version_id, "project": env[1].project_id},
            )
            .scalars()
            .all()
        )

    other = create_engine(env[5].url)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            if first == "approval":
                with env[5].begin() as holder:
                    holder.execute(text(B09_SHARE_SQL))
                    # The accepted SQL guard recognizes the same full inventory.
                    holder.execute(text("SELECT b09_preheld()"))
                    holder.execute(
                        text("SELECT id FROM manuscript_versions WHERE id=:id FOR UPDATE"),
                        {"id": env[1].manuscript_version_id},
                    )
                    pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
                    assert blockers(holder) == []

                    def write():
                        with other.begin() as writer:
                            writer.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
                            writer_pid = writer.execute(
                                text("SELECT pg_backend_pid()")
                            ).scalar_one()
                            insert_sql(writer, "issue", review)
                            return writer_pid

                    future = pool.submit(write)
                    witness = _wait_for_pg_blocker(env[5], pid, "relation")
                    assert "INSERT INTO review_issues" in witness["query"]
                    assert not future.done()
                    assert blockers(holder) == []
                assert future.result(timeout=15) != pid
                with env[5].connect() as conn:
                    assert len(blockers(conn)) == 1
            else:
                with other.begin() as writer:
                    writer.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
                    insert_sql(writer, "issue", review)
                    pid = writer.execute(text("SELECT pg_backend_pid()")).scalar_one()

                    def gate():
                        with env[5].begin() as holder:
                            holder.execute(text(B09_SHARE_SQL))
                            holder.execute(text("SELECT b09_preheld()"))
                            return blockers(holder)

                    future = pool.submit(gate)
                    witness = _wait_for_pg_blocker(env[5], pid, "relation")
                    assert witness["query"] == B09_SHARE_SQL
                    assert not future.done()
                assert len(future.result(timeout=15)) == 1
    finally:
        other.dispose()
