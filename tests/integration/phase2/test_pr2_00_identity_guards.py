from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError


def test_enrollment_challenge_issuance_fields_are_immutable(phase2_database_url: str) -> None:
    database_url = phase2_database_url
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "0018_current_pointer_same_parent_integrity")
    command.upgrade(config, "0019_phase2_bootstrap_membership")

    engine = create_engine(database_url)
    actor_id = uuid4()
    challenge_id = uuid4()
    issued_at = datetime.now(UTC)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            connection.execute(
                text(
                    "INSERT INTO actors (id, actor_type, display_name, created_at) "
                    "VALUES (:id, 'HUMAN', 'guard test actor', :created_at)"
                ),
                {"id": actor_id, "created_at": issued_at},
            )
            connection.execute(
                text(
                    "INSERT INTO actor_enrollment_challenges ("
                    "id, deployment_id, actor_id, subject_kind, subject_value, "
                    "subject_credential_id, operator_credential_id, nonce_digest, "
                    "proof_method, issued_at, expires_at, status, request_id, row_version"
                    ") VALUES ("
                    ":id, 'test-deployment', :actor_id, 'OS_UID', '1000', 'subject-credential', "
                    "'operator-credential', :nonce, 'OS_PEER', :issued, :expires, 'ISSUED', "
                    ":request, 1)"
                ),
                {
                    "id": challenge_id,
                    "actor_id": actor_id,
                    "nonce": "a" * 64,
                    "issued": issued_at,
                    "expires": issued_at + timedelta(minutes=5),
                    "request": uuid4(),
                },
            )
            try:
                connection.execute(
                    text(
                        "UPDATE actor_enrollment_challenges SET nonce_digest = :nonce, "
                        "row_version = row_version + 1 WHERE id = :id"
                    ),
                    {"nonce": "b" * 64, "id": challenge_id},
                )
            except DBAPIError:
                denied = True
            else:
                denied = False
            finally:
                transaction.rollback()

        assert denied, "issued challenge identity must not be mutable"
    finally:
        engine.dispose()


def test_membership_identity_is_immutable(phase2_database_url: str) -> None:
    database_url = phase2_database_url
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "0018_current_pointer_same_parent_integrity")
    command.upgrade(config, "0019_phase2_bootstrap_membership")

    engine = create_engine(database_url)
    actor_id = uuid4()
    replacement_actor_id = uuid4()
    project_id = uuid4()
    membership_id = uuid4()
    started_at = datetime.now(UTC)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            for identity, display_name in (
                (actor_id, "membership owner"),
                (replacement_actor_id, "replacement actor"),
            ):
                connection.execute(
                    text(
                        "INSERT INTO actors (id, actor_type, display_name, created_at) "
                        "VALUES (:id, 'HUMAN', :display_name, :created_at)"
                    ),
                    {"id": identity, "display_name": display_name, "created_at": started_at},
                )
            connection.execute(
                text(
                    "INSERT INTO projects (id, name, created_by, created_at) "
                    "VALUES (:id, 'membership test', :actor_id, :created_at)"
                ),
                {"id": project_id, "actor_id": actor_id, "created_at": started_at},
            )
            connection.execute(
                text(
                    "INSERT INTO project_memberships ("
                    "id, project_id, actor_id, status, started_at, created_by, created_at, "
                    "row_version"
                    ") VALUES (:id, :project_id, :actor_id, 'ACTIVE', :started_at, "
                    ":actor_id, :started_at, 1)"
                ),
                {
                    "id": membership_id,
                    "project_id": project_id,
                    "actor_id": actor_id,
                    "started_at": started_at,
                },
            )
            connection.execute(
                text(
                    "INSERT INTO project_membership_events ("
                    "id, membership_id, event_kind, prior_status, new_status, actor_id, "
                    "occurred_at, reason, request_id) VALUES ("
                    ":id, :membership_id, 'ACTIVATED', NULL, 'ACTIVE', :actor_id, :occurred_at, "
                    "'initial member row for guard test', :request_id)"
                ),
                {
                    "id": uuid4(),
                    "membership_id": membership_id,
                    "actor_id": actor_id,
                    "occurred_at": started_at,
                    "request_id": uuid4(),
                },
            )
            try:
                connection.execute(
                    text(
                        "UPDATE project_memberships SET actor_id = :replacement, "
                        "row_version = row_version + 1 WHERE id = :id"
                    ),
                    {"replacement": replacement_actor_id, "id": membership_id},
                )
            except DBAPIError:
                denied = True
            else:
                denied = False
            finally:
                transaction.rollback()

        assert denied, "membership identity must be immutable"
    finally:
        engine.dispose()
