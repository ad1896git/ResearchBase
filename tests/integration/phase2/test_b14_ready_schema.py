"""Forward-only READY extension and normal-role concrete deferred graph guards."""

# SQL assertions retain the reviewed literal lock/guard protocol.
# ruff: noqa: E501

import json
from uuid import uuid4

import pytest
from alembic import command as alembic
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from researchbase.domain.approval import consumption_request_material
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.persistence.approval_repository import B13_APPROVAL_SQL, B13_SHARE_SQL
from tests.disposable_postgres import disposable_database
from tests.integration.phase2.test_b04_manuscript_migration import normal_sql_role
from tests.integration.phase2.test_b14_publication_ready import (
    b04_env,
    b05_env,
    conclusion_env,
    counts,
    decision_env,
    issued,
    phase2_database_url,
    revision_env,
)
from tests.integration.phase2.test_b14a_entry_schema import catalog_inventory, config

_FIXTURES = (
    b04_env,
    b05_env,
    conclusion_env,
    phase2_database_url,
    decision_env,
    revision_env,
    normal_sql_role,
)
pytestmark = pytest.mark.integration


def test_forward_empty_catalog_and_exact_downgrade(monkeypatch):
    with disposable_database("researchbase_pr212_test_", "RB_PR210_TEST_ADMIN_URL") as url:
        monkeypatch.setenv("DATABASE_URL", url)
        cfg = config(url)
        alembic.upgrade(cfg, "0063_b14r_ready_approval")
        engine = create_engine(url)
        with engine.connect() as conn:
            before = catalog_inventory(conn)
        alembic.upgrade(cfg, "0075_m1_reconsideration")
        with engine.connect() as conn:
            assert conn.execute(text("SHOW server_version_num")).scalar_one().startswith("18")
            constraints = set(conn.execute(text("SELECT conname FROM pg_constraint")).scalars())
            assert {
                "fk_b14_ready_decision",
                "fk_b14_ready_consumption",
                "ck_b14a_event_tuple",
                "ck_b14a_publication_status",
            } <= constraints
            assert conn.execute(
                text(
                    "SELECT condeferrable AND condeferred FROM pg_constraint WHERE conname='fk_b14_ready_consumption'"
                )
            ).scalar_one()
            triggers = set(
                conn.execute(
                    text("SELECT tgname FROM pg_trigger WHERE tgdeferrable AND tginitdeferred")
                ).scalars()
            )
            assert {
                "b14_complete_publication",
                "b14_complete_ready_event",
                "b14_complete_ready_consumption",
            } <= triggers
            indexes = set(conn.execute(text("SELECT indexname FROM pg_indexes")).scalars())
            assert {
                "uq_b14_ready_event",
                "uq_b14_ready_consumption",
                "ix_b14_event_decision",
            } <= indexes
        alembic.downgrade(cfg, "0063_b14r_ready_approval")
        with engine.connect() as conn:
            assert catalog_inventory(conn) == before
        engine.dispose()


@pytest.mark.parametrize("complete", [False, True])
def test_entry_and_ready_history_refuse_downgrade(b05_env, complete):
    env = b05_env
    app, cmd, _, _ = issued(env)
    if complete:
        app.transition_publication_ready(env[2], cmd)
    before = counts(env)
    with pytest.raises(DBAPIError) as error:
        alembic.downgrade(
            config(env[5].url.render_as_string(hide_password=False)), "0063_b14r_ready_approval"
        )
    assert getattr(error.value.orig, "sqlstate", None) == "P14I1"
    assert counts(env) == before


def direct(env, cmd, role, attack=None):
    """Real normal-role transaction, literal locks and preallocated deferred cycle."""
    identity, event = uuid4(), uuid4()
    with env[5].connect().execution_options(isolation_level="SERIALIZABLE") as conn, conn.begin():
        conn.execute(text(B13_SHARE_SQL))
        conn.execute(text("LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE"))
        conn.execute(text(B13_APPROVAL_SQL))
        conn.execute(text(f'SET LOCAL ROLE "{role}"'))
        chain = (
            conn.execute(
                text(
                    "SELECT r.*,d.decided_by FROM approval_grants g JOIN approval_decisions d ON d.id=g.approval_decision_id JOIN approval_requests r ON r.id=d.approval_request_id WHERE g.id=:id"
                ),
                {"id": cmd.grant_id},
            )
            .mappings()
            .one()
        )
        at = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        actor = env[2].actor_id
        params = dict(
            id=identity,
            event=event,
            pub=cmd.result_id,
            grant=cmd.grant_id,
            key=cmd.command_key,
            actor=actor,
            project=cmd.project_id,
            at=at,
            decision=chain["basis_decision_id"],
        )
        if attack != "event_only" and attack != "receipt_only":
            conn.execute(
                text(
                    "UPDATE publications SET lifecycle_status='READY',row_version=row_version+1 WHERE id=:pub"
                ),
                params,
            )
        if attack == "state_only":
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            return
        event_params = dict(params)
        if attack == "actor":
            event_params["actor"] = chain["decided_by"]
        if attack == "decision":
            event_params["decision"] = uuid4()
        if attack != "receipt_only":
            conn.execute(
                text(
                    "INSERT INTO publication_lifecycle_events(id,publication_id,prior_status,new_status,actor_id,occurred_at,basis_decision_id,basis_grant_consumption_id) VALUES (:event,:pub,'INTERNAL_REVIEW','READY',:actor,:at,:decision,:id)"
                ),
                event_params,
            )
        if attack == "event_only":
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            return
        request_hash = str(
            sha256_canonical_json(
                consumption_request_material(
                    cmd.project_id,
                    actor,
                    cmd.grant_id,
                    "TRANSITION_PUBLICATION_READY",
                    "ManuscriptVersion",
                    chain["manuscript_version_id"],
                    chain["target_content_hash"],
                    cmd.result_id,
                    None,
                    cmd.checked_review_ids,
                )
            )
        )
        dto = json.dumps(
            dict(
                command="TRANSITION_PUBLICATION_READY",
                publication_id=str(cmd.result_id),
                consumption_id=str(identity),
            )
        )
        if attack == "time":
            params["at"] = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        conn.execute(
            text(
                "INSERT INTO approval_grant_consumptions(id,grant_id,command_key,project_id,actor_id,consumed_at,command,request_hash,hash_scheme,result_dto_version,result_dto,result_publication_id) VALUES (:id,:grant,:key,:project,:actor,:at,'TRANSITION_PUBLICATION_READY',:hash,'sha256-cjson-v1',1,CAST(:dto AS jsonb),:pub)"
            ),
            params | dict(hash=request_hash, dto=dto),
        )
        conn.execute(
            text(
                "INSERT INTO approval_grant_events(id,grant_id,prior_status,new_status,actor_id,occurred_at,reason) VALUES (:event,:grant,'ACTIVE','CONSUMED',:actor,:at,'grant consumed')"
            ),
            params | dict(event=uuid4()),
        )
        if attack != "grant_update":
            conn.execute(
                text("UPDATE approval_grants SET status='CONSUMED' WHERE id=:grant"), params
            )
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_normal_role_complete_deferred_cycle_succeeds(b05_env, normal_sql_role):
    env = b05_env
    _, cmd, _, _ = issued(env)
    direct(env, cmd, normal_sql_role)
    assert counts(env) == (1, 3, 2)


@pytest.mark.parametrize(
    "attack",
    ["state_only", "event_only", "receipt_only", "actor", "time", "decision", "grant_update"],
)
def test_normal_role_incomplete_cycle_cannot_commit(b05_env, normal_sql_role, attack):
    env = b05_env
    _, cmd, _, _ = issued(env)
    with pytest.raises(DBAPIError):
        direct(env, cmd, normal_sql_role, attack)
    assert counts(env) == (0, 2, 1)


@pytest.mark.parametrize(
    "table,operation",
    [
        ("publication_lifecycle_events", "UPDATE"),
        ("publication_lifecycle_events", "DELETE"),
        ("approval_grant_consumptions", "UPDATE"),
        ("approval_grant_consumptions", "DELETE"),
    ],
)
def test_normal_role_history_is_immutable(b05_env, normal_sql_role, table, operation):
    env = b05_env
    app, cmd, _, _ = issued(env)
    app.transition_publication_ready(env[2], cmd)
    with pytest.raises(DBAPIError):
        with env[5].begin() as conn:
            conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
            conn.execute(
                text(
                    f"UPDATE {table} SET actor_id=actor_id"
                    if operation == "UPDATE"
                    else f"DELETE FROM {table}"
                )
            )
    assert counts(env) == (1, 3, 2)


@pytest.mark.parametrize("gate", ["b14_consumption_gate", "b13_release_gate"])
@pytest.mark.parametrize("damage", ["extra_conclusion", "missing_manuscript"])
def test_ready_dispatch_rejects_malformed_composite_tuple(b05_env, gate, damage):
    env = b05_env
    _, cmd, _, _ = issued(env)
    # Invoke the gate with a transient malformed typed row. Persisted requests
    # remain protected by the canonical tuple CHECK and immutable guards.
    value = (
        "jsonb_build_object('scientific_conclusion_version_id',:id)"
        if damage == "extra_conclusion"
        else "jsonb_build_object('manuscript_version_id',NULL)"
    )
    with pytest.raises(DBAPIError) as error:
        with env[5].begin() as conn:
            conn.execute(
                text(
                    f"SELECT {gate}(jsonb_populate_record(NULL::approval_requests,to_jsonb(r)||{value}),NULL) "
                    "FROM approval_grants g JOIN approval_decisions d ON d.id=g.approval_decision_id "
                    "JOIN approval_requests r ON r.id=d.approval_request_id WHERE g.id=:grant"
                ),
                {"id": uuid4(), "grant": cmd.grant_id},
            )
    assert getattr(error.value.orig, "sqlstate", None) == "P16P1"
    assert counts(env) == (0, 2, 1)
