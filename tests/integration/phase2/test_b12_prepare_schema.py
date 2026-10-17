"""B12 conservative admission with real frozen manuscripts; no READY bypass."""

from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.decision import (
    RecordPrepareSubmissionDecisionCommand,
)
from tests.integration.phase2.test_b11_readiness_decision import (
    b04_env,
    b05_env,
    conclusion_env,
    phase2_database_url,
)
from tests.integration.phase2.test_revision_action import decision_env, revision_env

_FIXTURES = (b04_env, b05_env, conclusion_env, phase2_database_url, decision_env, revision_env)
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


def prepare_command(env):
    return RecordPrepareSubmissionDecisionCommand(
        uuid4(), env[1].project_id, env[1].manuscript_version_id, "Prepare?", "Independent judgment"
    )


def test_catalog_no_new_schema_and_empty_roundtrip(b05_env):
    from alembic import command as alembic

    from tests.integration.phase2.test_b11_readiness_schema import config

    env = b05_env

    def catalog():
        with env[5].connect() as conn:
            return conn.execute(
                text(
                    "SELECT table_name,column_name,data_type FROM information_schema.columns "
                    "WHERE table_schema='public' ORDER BY 1,2"
                )
            ).all()

    before = catalog()
    with env[5].connect() as conn:
        names = set(
            conn.execute(
                text(
                    "SELECT conname FROM pg_constraint WHERE conrelid='decision_records'::regclass"
                )
            ).scalars()
        )
    assert {"ck_b12_decision_policy", "ck_b12_text_bounds"} <= names
    alembic.downgrade(config(env), "0057_xid_wraparound_guards")
    assert catalog() == before
    alembic.upgrade(config(env), "head")
    assert catalog() == before


@pytest.mark.parametrize("protected", [False, True])
@pytest.mark.parametrize("force", [False, True])
def test_sql_parent_only_denied_without_partial_history(b05_env, protected, force):
    from sqlalchemy.exc import DBAPIError

    from researchbase.persistence.decision_repository import B11_SHARE_SQL

    env = b05_env
    with pytest.raises(DBAPIError):
        with env[5].begin() as conn:
            if protected:
                conn.execute(text(B11_SHARE_SQL))
            conn.execute(
                text("""INSERT INTO decision_records
                (id,project_id,decision_type,decision,question,rationale,decided_by,decided_at,
                basis_set_hash,content_hash,hash_scheme)
                VALUES (:id,:project,'PREPARE_SUBMISSION','PROCEED','Q','R',:actor,
                clock_timestamp(),:hash,:hash,'sha256-cjson-v1')"""),
                {
                    "id": uuid4(),
                    "project": env[1].project_id,
                    "actor": env[3].actor_id,
                    "hash": "a" * 64,
                },
            )
            if force:
                conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    with env[5].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM decision_records")).scalar_one() == 0


def test_upgrade_and_downgrade_preserve_exact_predecessor_function_catalog(b05_env):
    from alembic import command as alembic

    from tests.integration.phase2.test_b11_readiness_schema import config

    env = b05_env

    def functions():
        with env[5].connect() as conn:
            return {
                (row[0], row[1]): (row[2], row[3])
                for row in conn.execute(
                    text("""SELECT proname,pg_get_function_identity_arguments(oid),
                    pg_get_functiondef(oid),proconfig FROM pg_proc
                    WHERE pronamespace='public'::regnamespace AND prokind='f'""")
                )
            }

    cfg = config(env)
    alembic.downgrade(cfg, "0057_xid_wraparound_guards")
    predecessor = functions()
    alembic.upgrade(cfg, "0058_b12_prepare_submission")
    prepare = functions()
    assert {key[0] for key in prepare.keys() - predecessor.keys()} == {
        "b12_saved_decision",
        "b12_approval_gate",
    }
    assert predecessor.keys() <= prepare.keys()
    assert {key[0] for key in predecessor if predecessor[key] != prepare[key]} == {
        "b11_decision_guard",
        "b11_check_basis",
        "b11_complete",
        "pr215_basis_guard",
        "pr215_complete_basis",
        "pr216_gate",
    }
    alembic.downgrade(cfg, "0057_xid_wraparound_guards")
    assert functions() == predecessor
    alembic.upgrade(cfg, "0058_b12_prepare_submission")
    assert functions() == prepare


@pytest.mark.parametrize(
    "omitted", [None, "internal_review_records", "review_issues", "review_issue_events"]
)
def test_approval_sql_guard_requires_full_b_inventory(b05_env, omitted):
    from sqlalchemy.exc import DBAPIError

    from researchbase.persistence.approval_repository import B09_SNAPSHOT_TABLES

    tables = [name for name in B09_SNAPSHOT_TABLES if name != omitted]
    with b05_env[5].begin() as conn:
        conn.execute(text("LOCK TABLE " + ",".join(tables) + " IN SHARE MODE"))
        if omitted is None:
            conn.execute(text("SELECT b09_preheld()"))
        else:
            with pytest.raises(DBAPIError) as denied:
                conn.execute(text("SELECT b09_preheld()"))
            assert getattr(denied.value.orig, "sqlstate", None) == "P16G1"
