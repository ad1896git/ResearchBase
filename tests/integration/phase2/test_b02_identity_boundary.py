"""Reproduce B02's missing Agent binding prerequisite without admission fixtures.

These tests document the current identity boundary, not B02 acceptance. All writes
are rolled back. HUMAN is a positive control for each supported subject kind.
"""

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError


@pytest.mark.parametrize("actor_type", ["HUMAN", "AGENT"])
@pytest.mark.parametrize("subject_kind", ["OS_UID", "MTLS_URI"])
def test_existing_subject_binding_guard(phase2_database_url, actor_type, subject_kind):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url.replace("%", "%%"))
    command.upgrade(config, "head")
    engine = create_engine(phase2_database_url)
    try:
        with engine.connect() as connection:
            assert (
                180000
                <= int(connection.execute(text("SHOW server_version_num")).scalar_one())
                < 190000
            )
            trigger = connection.execute(
                text("""SELECT pg_get_triggerdef(t.oid), pg_get_functiondef(t.tgfoid)
                    FROM pg_trigger t
                    WHERE t.tgrelid='actor_subject_bindings'::regclass
                    AND t.tgname='trg_actor_binding_human' AND t.tgenabled='O'""")
            ).one()
            assert "BEFORE INSERT" in trigger[0]
            assert "actor_type = 'HUMAN'" in trigger[1]
            assert "ck_actor_subject_binding_human" in trigger[1]
            actor, binding = uuid4(), uuid4()
            connection.execute(
                text("""INSERT INTO actors(id, actor_type, display_name, created_at)
                    VALUES (:id, :kind, 'B02 identity reproduction', clock_timestamp())"""),
                {"id": actor, "kind": actor_type},
            )
            statement = text("""INSERT INTO actor_subject_bindings
                (id, actor_id, deployment_id, subject_kind, subject_value, status,
                 bound_at, operator_credential_id, subject_credential_id, proof_sha256,
                 proof_record_ref, proof_kind, created_at, row_version)
                VALUES (:id,:actor,'b02-reproduction',:subject_kind,:subject_value,'ACTIVE',
                 clock_timestamp(),'test-operator','test-credential',:digest,
                 'test-only:identity-proof',:proof_kind,clock_timestamp(),1)""")
            params = {
                "id": binding,
                "actor": actor,
                "subject_kind": subject_kind,
                "subject_value": "501" if subject_kind == "OS_UID" else "spiffe://test/agent",
                "proof_kind": "OS_PEER" if subject_kind == "OS_UID" else "MTLS_CHALLENGE",
                "digest": "a" * 64,
            }
            if actor_type == "AGENT":
                with pytest.raises(IntegrityError) as caught:
                    connection.execute(statement, params)
                assert getattr(caught.value.orig, "sqlstate", None) == "23514"
                diag = getattr(caught.value.orig, "diag", None)
                assert diag is not None
                assert diag.constraint_name == "ck_actor_subject_binding_human"
                assert diag.message_primary == "subject binding requires a HUMAN actor"
                print(f"{actor_type}/{subject_kind}: 23514 ck_actor_subject_binding_human")
            else:
                connection.execute(statement, params)
                assert (
                    connection.execute(
                        text("SELECT actor_id FROM actor_subject_bindings WHERE id=:id"),
                        {"id": binding},
                    ).scalar_one()
                    == actor
                )
                print(f"{actor_type}/{subject_kind}: INSERT accepted (positive control)")
            # This isolates the immediate binding guard; deferred ceremony/event
            # completeness is deliberately never claimed or committed.
            connection.rollback()
    finally:
        engine.dispose()
