"""Observed barriers prove complete, nonlocking snapshot reads and final authorization."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event, current_thread
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from researchbase.application.governance import (
    CreateCorrectionRecordCommand,
    GovernanceService,
    TransitionAuditFindingCommand,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.time import SystemClock
from researchbase.persistence.manuscript_freeze_repository import (
    SqlAlchemyManuscriptFreezeRepository,
)
from tests.integration.phase2.b25_support import literature_conclusion, place, source_transition
from tests.integration.phase2.test_b05_manuscript_review import seal
from tests.integration.phase2.test_b26_finding_impact import (
    assessment,
    b04_env,
    b05_env,
    conclusion_env,
    context,
    phase2_database_url,
    query,
    selected,
)

__all__ = ["b04_env", "b05_env", "conclusion_env", "phase2_database_url"]
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "change", ["dismissal", "assessment", "correction", "retraction", "dispute", "expiry"]
)
def test_complete_old_then_new_snapshot(b05_env, monkeypatch, change):
    env = b05_env
    evidence = None
    if change in {"retraction", "dispute"}:
        evidence, _, _ = literature_conclusion(env, snapshot=True)
    else:
        place(env)
    seal(env)
    f = selected(env)
    if change == "dismissal":
        assessment(env, f)
    reader, q = query(env, f)
    baseline = reader.get_finding_manuscript_impact(env[3], q)
    entered, release = Event(), Event()
    statements = []
    original = SqlAlchemyManuscriptFreezeRepository.authority
    checks = 0
    authorization_times = []
    expiry = None
    if change == "expiry":
        with env[5].connect() as conn:
            expiry = conn.execute(
                text("SELECT clock_timestamp() + interval '3 seconds'")
            ).scalar_one()
        original_valid = env[9].is_valid

        def credential_live(principal, at):
            if current_thread().name.startswith("b26-reader"):
                authorization_times.append(at)
            return original_valid(principal, at) and at < expiry

        monkeypatch.setattr(env[9], "is_valid", credential_live)

    def capture(conn, cursor, sql, params, execution, many):
        if current_thread().name.startswith("b26-reader"):
            statements.append(sql)

    def authority(self, *args):
        nonlocal checks
        rows = original(self, *args)
        if current_thread().name.startswith("b26-reader"):
            checks += 1
            if checks == (2 if change == "expiry" else 1):
                assert (
                    self._session.execute(text("SHOW transaction_isolation")).scalar_one()
                    == "repeatable read"
                )
                assert (
                    self._session.execute(text("SHOW transaction_read_only")).scalar_one() == "on"
                )
                assert not self._session.execute(
                    text("""SELECT mode FROM pg_locks
                    WHERE pid=pg_backend_pid() AND (locktype='advisory'
                    OR mode IN ('ShareLock','RowShareLock','RowExclusiveLock'))""")
                ).all()
                entered.set()
                assert release.wait(20)
        return rows

    monkeypatch.setattr(SqlAlchemyManuscriptFreezeRepository, "authority", authority)
    event.listen(env[5], "before_cursor_execute", capture)
    try:
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="b26-reader") as pool:
            future = pool.submit(reader.get_finding_manuscript_impact, env[3], q)
            try:
                assert entered.wait(20)
                governance = GovernanceService(env[4], SystemClock())
                if change == "dismissal":
                    governance.transition_audit_finding(
                        TransitionAuditFindingCommand(
                            f.id, "dismissed", f.row_version, context(env)
                        )
                    )
                elif change == "assessment":
                    assessment(env, f)
                elif change == "correction":
                    governance.create_correction_record(
                        CreateCorrectionRecordCommand(
                            q.project_id,
                            f.target_type,
                            f.target_id,
                            "factual",
                            {"note": "new"},
                            "Concurrent correction",
                            context(env),
                        )
                    )
                elif change == "retraction":
                    source_transition(env, "RETRACTED")
                elif change == "dispute":
                    env[10][2].review(
                        env[3],
                        q.project_id,
                        evidence,
                        "DISPUTED",
                        "Concurrent dispute",
                        uuid4(),
                    )
                else:
                    with env[5].connect() as conn:
                        while not conn.execute(
                            text("SELECT clock_timestamp() >= :expiry"), {"expiry": expiry}
                        ).scalar_one():
                            release.wait(0.02)

                # Writer completed while the reader remained open.
                assert not future.done()
            finally:
                release.set()
            if change == "expiry":
                with pytest.raises(ResearchBaseError) as error:
                    future.result(20)
                assert error.value.code == ErrorCode.FORBIDDEN
                assert authorization_times[0] < expiry <= authorization_times[-1]

            else:
                old = future.result(20)
                assert old.finding == baseline.finding
                assert old.assessments == baseline.assessments
                assert old.matches == baseline.matches
                assert old.validity.witnesses == baseline.validity.witnesses
                fresh = reader.get_finding_manuscript_impact(env[3], q)
                assert (
                    fresh.validity.current_validity
                    == {
                        "dismissal": "VALID",
                        "assessment": "INVALID",
                        "correction": "STALE",
                        "retraction": "INVALID",
                        "dispute": "STALE",
                    }[change]
                )
                assert fresh.validity.content_hash == old.validity.content_hash
                assert fresh.validity.placement_set_hash == old.validity.placement_set_hash
                if change == "dismissal":
                    assert (
                        fresh.finding.status.value == "dismissed" and fresh.matches == old.matches
                    )
                if change == "assessment":
                    assert len(fresh.assessments) == 1 and old.assessments == ()
        assert statements[0] == "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
        assert not any(
            any(
                token in sql.upper()
                for token in (
                    "LOCK TABLE",
                    "FOR UPDATE",
                    "FOR SHARE",
                    "PG_ADVISORY",
                    "INSERT INTO",
                    "UPDATE ",
                    "DELETE FROM",
                )
            )
            for sql in statements
        )
    finally:
        release.set()
        event.remove(env[5], "before_cursor_execute", capture)
