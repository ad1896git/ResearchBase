from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.r1_support import (
    _expiry_role,
    _schedule_expiry,
)


def _migrate(database_url: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    with patch.dict("os.environ", {"DATABASE_URL": database_url}):
        command.upgrade(config, "0019_phase2_bootstrap_membership")


def _add_owner(
    connection,
    *,
    actor_id,
    project_id,
    now,
    event_kind,
    request_id,
    create_actor=True,
):
    membership_id = uuid4()
    role_id = uuid4()
    binding_id = uuid4()
    if create_actor:
        connection.execute(
            text(
                "INSERT INTO actors (id, actor_type, display_name, created_at) "
                "VALUES (:id, 'HUMAN', 'Owner', :now)"
            ),
            {"id": actor_id, "now": now},
        )
    connection.execute(
        text(
            "INSERT INTO actor_subject_bindings "
            "(id, actor_id, deployment_id, subject_kind, subject_value, status, bound_at, "
            "operator_credential_id, subject_credential_id, proof_sha256, proof_record_ref, "
            "proof_kind, created_at, row_version) "
            "VALUES (:id, :actor, 'test-deployment', 'OS_UID', :uid, 'ACTIVE', :now, "
            "'operator', :subject_credential, :digest, 'audit://owner-proof', 'OS_PEER', :now, 1)"
        ),
        {
            "id": binding_id,
            "actor": actor_id,
            "uid": str(actor_id.int),
            "subject_credential": f"uid:{actor_id.int}",
            "digest": "b" * 64,
            "now": now,
        },
    )
    connection.execute(
        text(
            "INSERT INTO actor_subject_binding_events "
            "(id, binding_id, actor_id, event_kind, operator_credential_id, subject_credential_id, "
            "proof_sha256, proof_record_ref, proof_kind, request_id, reason, occurred_at) "
            "VALUES (:id, :binding, :actor, 'PROVISIONED', 'operator', :subject_credential, "
            ":digest, 'audit://owner-proof', 'OS_PEER', :request, 'owner proof', :now)"
        ),
        {
            "id": uuid4(),
            "binding": binding_id,
            "actor": actor_id,
            "subject_credential": f"uid:{actor_id.int}",
            "digest": "b" * 64,
            "request": request_id,
            "now": now,
        },
    )
    connection.execute(
        text(
            "INSERT INTO project_memberships "
            "(id, project_id, actor_id, status, started_at, created_by, created_at, row_version) "
            "VALUES (:id, :project, :actor, 'ACTIVE', :now, :actor, :now, 1)"
        ),
        {"id": membership_id, "project": project_id, "actor": actor_id, "now": now},
    )
    connection.execute(
        text(
            "INSERT INTO project_membership_events "
            "(id, membership_id, event_kind, prior_status, new_status, actor_id, "
            "occurred_at, reason, request_id) "
            "VALUES (:id, :membership, :kind, NULL, 'ACTIVE', :actor, :now, "
            "'owner coverage start', :request)"
        ),
        {
            "id": uuid4(),
            "membership": membership_id,
            "kind": event_kind,
            "actor": actor_id,
            "now": now,
            "request": request_id,
        },
    )
    connection.execute(
        text(
            "INSERT INTO project_role_assignments "
            "(id, membership_id, project_id, actor_id, role, effective_from, assigned_by, "
            "created_at, row_version) "
            "VALUES (:id, :membership, :project, :actor, 'OWNER', :now, :actor, :now, 1)"
        ),
        {
            "id": role_id,
            "membership": membership_id,
            "project": project_id,
            "actor": actor_id,
            "now": now,
        },
    )
    connection.execute(
        text(
            "INSERT INTO project_role_events "
            "(id, role_assignment_id, actor_id, event_kind, occurred_at, reason, request_id) "
            "VALUES (:id, :role, :actor, 'ASSIGNED', :now, 'owner assignment', :request)"
        ),
        {"id": uuid4(), "role": role_id, "actor": actor_id, "now": now, "request": request_id},
    )
    return membership_id, role_id


def test_project_requires_contiguous_owner_coverage_and_accepts_touching_successor(
    phase2_database_url: str,
) -> None:
    _migrate(phase2_database_url)
    engine = create_engine(phase2_database_url)
    actor_a, actor_b, project_id = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO actors (id, actor_type, display_name, created_at) "
                    "VALUES (:id, 'HUMAN', 'Owner A', :now)"
                ),
                {"id": actor_a, "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO projects (id, name, created_by, created_at) "
                    "VALUES (:id, 'Coverage project', :actor, :now)"
                ),
                {"id": project_id, "actor": actor_a, "now": now},
            )
            # The initial owner records provide the immutable enrollment marker.
            membership_a, role_a = _add_owner(
                connection,
                actor_id=actor_a,
                project_id=project_id,
                now=now,
                event_kind="PROJECT_ENROLLMENT",
                request_id=uuid4(),
                create_actor=False,
            )

        end_at = now + timedelta(seconds=10)
        with engine.connect() as connection:
            transaction = connection.begin()
            connection.execute(
                text(
                    "UPDATE project_role_assignments SET effective_until = :end, row_version = 2 "
                    "WHERE id = :id"
                ),
                {"end": end_at, "id": role_a},
            )
            connection.execute(
                text(
                    "INSERT INTO project_role_events "
                    "(id, role_assignment_id, actor_id, event_kind, occurred_at, "
                    "reason, request_id) "
                    "VALUES (:id, :role, :actor, 'CLOSED', :end, 'owner transition', :request)"
                ),
                {
                    "id": uuid4(),
                    "role": role_a,
                    "actor": actor_a,
                    "end": end_at,
                    "request": uuid4(),
                },
            )
            try:
                transaction.commit()
            except DBAPIError:
                pass
            else:
                raise AssertionError("closing the only OWNER must fail the deferred coverage guard")

        with engine.begin() as connection:
            membership_b, role_b = _add_owner(
                connection,
                actor_id=actor_b,
                project_id=project_id,
                now=end_at,
                event_kind="ACTIVATED",
                request_id=uuid4(),
            )
            connection.execute(
                text(
                    "UPDATE project_role_assignments SET effective_until = :end, row_version = 2 "
                    "WHERE id = :id"
                ),
                {"end": end_at, "id": role_a},
            )
            connection.execute(
                text(
                    "INSERT INTO project_role_events "
                    "(id, role_assignment_id, actor_id, event_kind, occurred_at, "
                    "reason, request_id) "
                    "VALUES (:id, :role, :actor, 'CLOSED', :end, 'owner transition', :request)"
                ),
                {
                    "id": uuid4(),
                    "role": role_a,
                    "actor": actor_a,
                    "end": end_at,
                    "request": uuid4(),
                },
            )
            assert (
                connection.execute(
                    text("SELECT id FROM project_role_assignments WHERE id = :id"), {"id": role_b}
                ).scalar_one()
                == role_b
            )
            assert (
                connection.execute(
                    text("SELECT id FROM project_memberships WHERE id = :id"), {"id": membership_b}
                ).scalar_one()
                == membership_b
            )
    finally:
        engine.dispose()


def test_actor_retirement_cannot_remove_the_last_owner(
    phase2_database_url: str,
) -> None:
    _migrate(phase2_database_url)
    engine = create_engine(phase2_database_url)
    actor_id, project_id = uuid4(), uuid4()
    now = datetime.now(UTC)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO actors (id, actor_type, display_name, created_at) "
                    "VALUES (:id, 'HUMAN', 'Only owner', :now)"
                ),
                {"id": actor_id, "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO projects (id, name, created_by, created_at) "
                    "VALUES (:id, 'Retirement project', :actor, :now)"
                ),
                {"id": project_id, "actor": actor_id, "now": now},
            )
            _add_owner(
                connection,
                actor_id=actor_id,
                project_id=project_id,
                now=now,
                event_kind="PROJECT_ENROLLMENT",
                request_id=uuid4(),
                create_actor=False,
            )

        with engine.connect() as connection:
            transaction = connection.begin()
            connection.execute(
                text(
                    "UPDATE actors SET retired_at = :now, row_version = row_version + 1 "
                    "WHERE id = :id"
                ),
                {"id": actor_id, "now": now + timedelta(seconds=1)},
            )
            try:
                transaction.commit()
            except DBAPIError:
                pass
            else:
                raise AssertionError("retiring the last OWNER must fail")

        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT retired_at FROM actors WHERE id = :id"), {"id": actor_id}
                ).scalar_one()
                is None
            )
    finally:
        engine.dispose()


@pytest.mark.parametrize("role_name", ["REVIEWER", "RESEARCHER", "APPROVER", "VIEWER"])
def test_application_schedules_non_owner_role_expiry(role_expiry_env, role_name):
    e = role_expiry_env
    role = _expiry_role(e, role_name)
    expiry = _schedule_expiry(e, role)
    with e["engine"].connect() as connection:
        assert connection.execute(
            text("SELECT effective_until, row_version FROM project_role_assignments WHERE id=:id"),
            {"id": role},
        ).one() == (expiry, 2)
        assert (
            connection.execute(
                text(
                    "SELECT occurred_at FROM project_role_events "
                    "WHERE role_assignment_id=:id AND event_kind='CLOSED'"
                ),
                {"id": role},
            ).scalar_one()
            == expiry
        )


def test_application_cannot_schedule_sole_owner_expiry(role_expiry_env):
    e = role_expiry_env
    role = e["first"].role_assignment_id
    with pytest.raises(ResearchBaseError) as caught:
        _schedule_expiry(e, role)
    assert caught.value.code is ErrorCode.OWNER_COVERAGE_GAP
    with e["engine"].connect() as connection:
        assert connection.execute(
            text("SELECT effective_until, row_version FROM project_role_assignments WHERE id=:id"),
            {"id": role},
        ).one() == (None, 1)
        assert (
            connection.execute(
                text("SELECT count(*) FROM project_role_events WHERE role_assignment_id=:id"),
                {"id": role},
            ).scalar_one()
            == 1
        )


def test_application_schedules_owner_expiry_with_open_successor(role_expiry_env):
    e = role_expiry_env
    successor = _expiry_role(e, "OWNER")
    role = e["first"].role_assignment_id
    expiry = _schedule_expiry(e, role)
    with e["engine"].connect() as connection:
        assert connection.execute(
            text("SELECT effective_until, row_version FROM project_role_assignments WHERE id=:id"),
            {"id": role},
        ).one() == (expiry, 2)
        assert (
            connection.execute(
                text("SELECT effective_until FROM project_role_assignments WHERE id=:id"),
                {"id": successor},
            ).scalar_one()
            is None
        )
        assert connection.execute(
            text("SELECT rb_phase2_owner_coverage(:project)"),
            {"project": e["first"].project_id},
        ).scalar_one()
