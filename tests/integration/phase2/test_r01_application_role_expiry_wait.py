"""R01's missing F9 owning path: Application expiry, then an observed PG wait."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.phase2_identity import CloseProjectRole
from researchbase.application.scientific_conclusion import ScientificConclusionService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b30_observations import poll_db_clock
from tests.integration.phase2.pr2_19_support import counts
from tests.integration.phase2.test_pr2_00_challenges import _service
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker
from tests.integration.phase2.test_pr2_19_grant_consumption_release import (
    approval_env,
    conclusion_env,
    decision_env,
    fresh,
    issued,
    phase2_database_url,
)

_FIXTURES = (approval_env, conclusion_env, decision_env, phase2_database_url)
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("expiry_kind", ["caller_role", "issuer_role"])
def test_application_scheduled_expiry_denies_after_observed_consumption_wait(
    approval_env, expiry_kind
):
    base = approval_env[-1][-1]
    engine = base[8]
    with engine.connect() as conn:
        assert int(conn.execute(text("SHOW server_version_num")).scalar_one()) // 10000 == 18
        expiry = conn.execute(text("SELECT clock_timestamp()")).scalar_one() + timedelta(seconds=8)
    _, actor, command, _ = issued(approval_env)
    target = actor if expiry_kind == "caller_role" else approval_env[2]
    role_kind = "OWNER" if expiry_kind == "caller_role" else "APPROVER"
    with engine.connect() as conn:
        role_id = conn.execute(
            text("""SELECT id FROM project_role_assignments
            WHERE project_id=:project AND actor_id=:actor AND role=:role
            AND effective_until IS NULL"""),
            dict(project=command.project_id, actor=target.actor_id, role=role_kind),
        ).scalar_one()
    request = uuid4()
    identity, _, _ = _service(engine.url.render_as_string(hide_password=False))
    identity.close_project_role(
        CloseProjectRole(
            approval_env[-1][2],
            command.project_id,
            role_id,
            "R01 F9 Application-scheduled expiry",
            request,
            effective_until=expiry,
        )
    )
    with engine.connect() as conn:
        scheduled = conn.execute(
            text("SELECT effective_until,row_version FROM project_role_assignments WHERE id=:id"),
            dict(id=role_id),
        ).one()
        assert scheduled == (expiry, 2)
        event = conn.execute(
            text("""SELECT actor_id,occurred_at,event_kind FROM project_role_events
            WHERE role_assignment_id=:id AND request_id=:request"""),
            dict(id=role_id, request=request),
        ).one()
        assert event == (target.actor_id, expiry, "CLOSED")
    # Distinguish loss caused by crossing time from an already unusable grant.
    _, reader = fresh(approval_env)
    assert reader.get_grant(actor, command.project_id, command.grant_id).usable
    registry, checked = base[9], []

    class ObservedCredentials:
        def is_valid(self, principal, at):
            checked.append(at)
            return registry.is_valid(principal, at)

    consumer = ScientificConclusionService(base[1], ObservedCredentials(), base[2])
    before = counts(engine)
    with engine.connect() as holder:
        holder.execute(text("LOCK TABLE internal_review_records IN ROW EXCLUSIVE MODE"))
        blocker_pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(consumer.record_internal_scientific_release, actor, command)
            try:
                witness = _wait_for_pg_blocker(engine, blocker_pid, "relation")
                with engine.connect() as observer:
                    started = observer.execute(
                        text("SELECT xact_start FROM pg_stat_activity WHERE pid=:pid"),
                        dict(pid=witness["pid"]),
                    ).scalar_one()
                    assert started < witness["observed_at"] < expiry
                    expiry_observed = poll_db_clock(observer, expiry)
            finally:
                holder.rollback()
            with pytest.raises(ResearchBaseError) as denied:
                future.result(timeout=15)
            assert denied.value.code is (
                ErrorCode.FORBIDDEN if expiry_kind == "caller_role" else ErrorCode.GRANT_STALE
            )
    assert checked[-1] >= expiry_observed > expiry
    assert counts(engine) == before
    _, reader = fresh(approval_env)
    entitled = approval_env[-1][2] if expiry_kind == "caller_role" else actor
    assert reader.get_grant(entitled, command.project_id, command.grant_id).status == "ACTIVE"
    with engine.connect() as conn:
        assert (
            conn.execute(
                text(
                    "SELECT effective_until,row_version FROM project_role_assignments WHERE id=:id"
                ),
                dict(id=role_id),
            ).one()
            == scheduled
        )
        assert (
            conn.execute(
                text("""SELECT actor_id,occurred_at,event_kind FROM project_role_events
            WHERE role_assignment_id=:id AND request_id=:request"""),
                dict(id=role_id, request=request),
            ).one()
            == event
        )
    assert counts(engine) == before
    print(
        "R01_APPLICATION_ROLE_EXPIRY_WAIT",
        dict(
            kind=expiry_kind,
            scheduling="Phase2IdentityService.close_project_role",
            request_id=str(request),
            role_id=str(role_id),
            role_event="CLOSED",
            tx_started_at=str(started),
            wait_observed_at=str(witness["observed_at"]),
            expiry_at=str(expiry),
            expiry_observed_before_unlock_at=str(expiry_observed),
            authorization_checked_at=str(checked[-1]),
            outcome=denied.value.code.value,
            protected_effect_counts_unchanged=True,
        ),
    )
