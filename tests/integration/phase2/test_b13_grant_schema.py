"""Forward-only B13 DDL and direct SQL fail-closed final graphs."""

# SQL spells out the exact concrete graph attacks.
# ruff: noqa: E501

from uuid import uuid4

import pytest
from alembic import command as alembic
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.integration.phase2.test_b13_grant_consumption import (
    approval_env as approval_env,
)
from tests.integration.phase2.test_b13_grant_consumption import (
    conclusion_env as conclusion_env,
)
from tests.integration.phase2.test_b13_grant_consumption import (
    counts,
    issued,
)
from tests.integration.phase2.test_b13_grant_consumption import (
    decision_env as decision_env,
)
from tests.integration.phase2.test_b13_grant_consumption import (
    phase2_database_url as phase2_database_url,
)

_FIXTURES = (approval_env, conclusion_env, decision_env, phase2_database_url)
pytestmark = pytest.mark.integration
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)


def config(env):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", env[-1][-1][8].url.render_as_string(hide_password=False))
    return cfg


def test_exact_catalog_and_no_duplicate_review_owner(approval_env):
    engine = approval_env[-1][-1][8]
    with engine.connect() as conn:
        assert conn.execute(text("SHOW server_version_num")).scalar_one().startswith("18")
        constraints = set(
            conn.execute(
                text(
                    "SELECT conname FROM pg_constraint WHERE conrelid='approval_grant_consumptions'::regclass"
                )
            ).scalars()
        )
        assert {
            "pk_b13_consumptions",
            "uq_b13_consumption_grant",
            "uq_b13_command_key",
            "fk_b13_consumption_grant",
            "fk_b13_consumption_project",
            "fk_b13_consumption_actor",
            "fk_b13_result_publication",
            "fk_b13_result_conclusion",
            "ck_b13_hash",
            "ck_b13_time",
            "ck_b13_dto",
            "ck_b13_result_tuple",
        } <= constraints
        assert (
            conn.execute(
                text("SELECT to_regclass('approval_grant_consumption_reviews')")
            ).scalar_one()
            is None
        )
        guards = conn.execute(
            text(
                "SELECT tgname,tgdeferrable,tginitdeferred FROM pg_trigger WHERE tgname LIKE 'b13_complete%' ORDER BY tgname"
            )
        ).all()
        assert len(guards) == 3 and all(row[1] and row[2] for row in guards)
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM pg_constraint WHERE conrelid='approval_grant_consumptions'::regclass AND contype='f' AND confdeltype<>'r'"
                )
            ).scalar_one()
            == 0
        )


def test_empty_slice_roundtrip_preserves_populated_predecessor(approval_env):
    _, _, _, _ = issued(approval_env)
    cfg = config(approval_env)
    before = counts(approval_env)
    alembic.downgrade(cfg, "0058_b12_prepare_submission")
    alembic.upgrade(cfg, "head")
    assert counts(approval_env) == before


def test_populated_downgrade_refuses_history_loss(approval_env):
    owner, actor, cmd, _ = issued(approval_env)
    owner.record_internal_scientific_release(actor, cmd)
    with pytest.raises(DBAPIError):
        alembic.downgrade(config(approval_env), "0058_b12_prepare_submission")
    assert counts(approval_env) == (1, 2, 1)


@pytest.mark.parametrize("force", [False, True])
@pytest.mark.parametrize(
    "attack", ["status", "event", "late_review", "review_update", "review_delete"]
)
def test_direct_sql_cannot_forge_or_rewrite_history(approval_env, force, attack):
    _, actor, cmd, _ = issued(approval_env)
    request = approval_env[3]
    engine = approval_env[-1][-1][8]
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            if attack == "status":
                conn.execute(
                    text("UPDATE approval_grants SET status='CONSUMED' WHERE id=:id"),
                    {"id": cmd.grant_id},
                )
            elif attack == "event":
                conn.execute(
                    text(
                        "INSERT INTO approval_grant_events(grant_id,prior_status,new_status,actor_id,occurred_at,reason) VALUES(:id,'ACTIVE','REVOKED',:actor,clock_timestamp(),'forged')"
                    ),
                    {"id": cmd.grant_id, "actor": actor.actor_id},
                )
            elif attack == "late_review":
                conn.execute(
                    text("INSERT INTO approval_request_reviews VALUES(:request,:review)"),
                    {"request": request.id, "review": uuid4()},
                )
            elif attack == "review_update":
                conn.execute(
                    text(
                        "UPDATE approval_request_reviews SET internal_review_record_id=:review WHERE request_id=:id"
                    ),
                    {"review": uuid4(), "id": request.id},
                )
            else:
                conn.execute(
                    text("DELETE FROM approval_request_reviews WHERE request_id=:id"),
                    {"id": request.id},
                )
            if force:
                conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert counts(approval_env) == (0, 1, 1)


@pytest.mark.parametrize(
    "table", ["approval_grant_consumptions", "approval_grant_events", "approval_grants"]
)
@pytest.mark.parametrize("verb", ["UPDATE", "DELETE"])
def test_terminal_and_receipt_edits_denied(approval_env, table, verb):
    owner, actor, cmd, _ = issued(approval_env)
    owner.record_internal_scientific_release(actor, cmd)
    sql = (
        (
            "UPDATE "
            + table
            + " SET "
            + ("status='ACTIVE'" if table == "approval_grants" else "id=id")
        )
        if verb == "UPDATE"
        else "DELETE FROM " + table
    )
    with pytest.raises(DBAPIError):
        with approval_env[-1][-1][8].begin() as conn:
            conn.execute(text(sql))
    assert counts(approval_env) == (1, 2, 1)


@pytest.mark.parametrize("missing", ["event", "grant_update"])
@pytest.mark.parametrize("force", [False, True])
def test_normal_role_preheld_receipt_cannot_commit_incomplete_graph(approval_env, missing, force):
    import json

    from researchbase.domain.approval import consumption_request_material
    from researchbase.foundation.hashing import sha256_canonical_json
    from researchbase.persistence.approval_repository import B13_APPROVAL_SQL, B13_SHARE_SQL

    _, actor, cmd, _ = issued(approval_env)
    engine = approval_env[-1][-1][8]
    request = approval_env[0].get_request(actor, cmd.project_id, approval_env[3].id)
    identity = uuid4()
    digest = str(
        sha256_canonical_json(
            consumption_request_material(
                cmd.project_id,
                actor.actor_id,
                cmd.grant_id,
                "RECORD_INTERNAL_SCIENTIFIC_RELEASE",
                "ScientificConclusionVersion",
                cmd.result_id,
                request.target_content_hash,
                cmd.result_id,
                None,
                cmd.checked_review_ids,
            )
        )
    )
    dto = json.dumps(
        {
            "command": "RECORD_INTERNAL_SCIENTIFIC_RELEASE",
            "scientific_conclusion_version_id": str(cmd.result_id),
            "consumption_id": str(identity),
        }
    )
    with pytest.raises(DBAPIError) as error:
        with engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn:
            with conn.begin():
                conn.execute(text(B13_SHARE_SQL))
                conn.execute(text("LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE"))
                conn.execute(text(B13_APPROVAL_SQL))
                role = "test_b13_" + uuid4().hex
                conn.execute(text("CREATE ROLE " + role + " NOSUPERUSER"))
                conn.execute(text("GRANT USAGE ON SCHEMA public TO " + role))
                conn.execute(
                    text(
                        "GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO "
                        + role
                    )
                )
                conn.execute(text("SET LOCAL ROLE " + role))
                at = conn.execute(
                    text("""INSERT INTO approval_grant_consumptions
                  (id,grant_id,command_key,project_id,actor_id,consumed_at,command,request_hash,
                   hash_scheme,result_dto_version,result_dto,result_scientific_conclusion_version_id)
                  VALUES(:id,:grant,:key,:project,:actor,clock_timestamp()-interval '1 day',
                   'RECORD_INTERNAL_SCIENTIFIC_RELEASE',:hash,'sha256-cjson-v1',1,CAST(:dto AS jsonb),:target)
                   RETURNING consumed_at"""),
                    {
                        "id": identity,
                        "grant": cmd.grant_id,
                        "key": cmd.command_key,
                        "project": cmd.project_id,
                        "actor": actor.actor_id,
                        "hash": digest,
                        "dto": dto,
                        "target": cmd.result_id,
                    },
                ).scalar_one()
                if missing != "event":
                    conn.execute(
                        text("""INSERT INTO approval_grant_events(grant_id,prior_status,new_status,actor_id,occurred_at,reason)
                      VALUES(:grant,'ACTIVE','CONSUMED',:actor,:at,'grant consumed')"""),
                        {"grant": cmd.grant_id, "actor": actor.actor_id, "at": at},
                    )
                if force:
                    conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert getattr(error.value.orig, "sqlstate", None) == "P17F2"
    assert counts(approval_env) == (0, 1, 1)
