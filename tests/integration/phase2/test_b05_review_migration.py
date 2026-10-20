"""B05 forward migration, preflight and deferred OPEN history constraints."""

# ruff: noqa: E501
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from tests.disposable_postgres import disposable_database
from tests.integration.phase2.test_b04_manuscript_migration import (
    normal_sql_role as _normal_sql_role,
)
from tests.integration.phase2.test_b05_manuscript_review import (
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
normal_sql_role = _normal_sql_role

pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("start", ["base", "0048_b04_manuscript_freeze"])
def test_upgrade_actual_head_catalog_and_empty_downgrade(start, monkeypatch):
    with disposable_database("researchbase_pr212_test_", "RB_PR210_TEST_ADMIN_URL") as url:
        monkeypatch.setenv("DATABASE_URL", url)
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
        if start != "base":
            command.upgrade(config, start)
        command.upgrade(config, "head")
        engine = create_engine(url)
        with engine.connect() as conn:
            assert (
                conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == "0075_m1_reconsideration"
            )
            triggers = conn.execute(
                text(
                    "SELECT tgname,tgdeferrable,tginitdeferred FROM pg_trigger WHERE tgname LIKE 'b05_complete_%' ORDER BY tgname"
                )
            ).all()
            assert triggers == [
                ("b05_complete_issue", True, True),
                ("b05_complete_issue_event", True, True),
                ("b05_complete_review", True, True),
            ]
            definitions = (
                conn.execute(
                    text(
                        "SELECT pg_get_triggerdef(oid) FROM pg_trigger WHERE tgname LIKE 'b05_complete_%'"
                    )
                )
                .scalars()
                .all()
            )
            assert len(definitions) == 3 and all("WHEN" in definition for definition in definitions)
            assert (
                conn.execute(
                    text(
                        "SELECT count(*) FROM pg_indexes WHERE indexname='ix_pr214_review_manuscript'"
                    )
                ).scalar_one()
                == 1
            )
        engine.dispose()
        command.downgrade(config, "0048_b04_manuscript_freeze")
        command.upgrade(config, "head")


@pytest.mark.parametrize("mutation", ["gap", "missing", "forged", "duplicate"])
@pytest.mark.parametrize("force", [False, True])
def test_structural_constraint_at_commit_or_force(b05_env, mutation, force):
    env = b05_env
    seal(env)
    review = create(env)
    with pytest.raises(DBAPIError) as exc:
        with env[5].begin() as conn:
            issue = uuid4()
            if mutation in {"missing", "forged"}:
                conn.execute(
                    text(
                        "ALTER TABLE review_issue_events DISABLE TRIGGER pr214_issue_events_immutable"
                    )
                )
            conn.execute(
                text("""INSERT INTO review_issues(id,review_record_id,severity,issue_type,description,status,created_at,ordinal)
                VALUES (:id,:review,'MINOR','OTHER','Test issue','OPEN',clock_timestamp(),:ordinal)"""),
                {"id": issue, "review": review.id, "ordinal": 2 if mutation == "gap" else 0},
            )
            if mutation in {"missing", "forged"}:
                if mutation == "missing":
                    conn.execute(
                        text("DELETE FROM review_issue_events WHERE issue_id=:id"), {"id": issue}
                    )
                else:
                    conn.execute(
                        text("UPDATE review_issue_events SET actor_id=:actor WHERE issue_id=:id"),
                        {"id": issue, "actor": env[2].actor_id},
                    )
            if mutation == "duplicate":
                conn.execute(
                    text(
                        "INSERT INTO review_issue_events SELECT :id,issue_id,actor_id,prior_status,new_status,occurred_at FROM review_issue_events WHERE issue_id=:issue"
                    ),
                    {"id": uuid4(), "issue": issue},
                )
            if force:
                conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert getattr(exc.value.orig, "sqlstate", None) == (
        "23505" if mutation == "duplicate" else "P05R1"
    )
    with env[5].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM review_issues")).scalar_one() == 0


def test_preflight_rejects_incompatible_history_and_populated_downgrade(
    b05_env, phase2_database_url
):
    env = b05_env
    seal(env)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.downgrade(config, "0048_b04_manuscript_freeze")
    review = create(env)
    # Before B05 this gapped issue is permitted; B05 must reject without rewriting.
    with env[5].begin() as conn:
        conn.execute(
            text("""INSERT INTO review_issues(id,review_record_id,severity,issue_type,description,status,created_at,ordinal)
            VALUES (:id,:review,'MINOR','OTHER','Legacy gap','OPEN',clock_timestamp(),3)"""),
            {"id": uuid4(), "review": review.id},
        )
    with pytest.raises(DBAPIError) as exc:
        command.upgrade(config, "head")
    assert getattr(exc.value.orig, "sqlstate", None) == "P05R1" and str(review.id) in str(
        exc.value.orig
    )
    with env[5].connect() as conn:
        assert (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0048_b04_manuscript_freeze"
        )


def test_populated_history_prevents_downgrade(b05_env, phase2_database_url):
    seal(b05_env)
    create(b05_env)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    with pytest.raises(DBAPIError) as exc:
        command.downgrade(config, "0048_b04_manuscript_freeze")
    assert getattr(exc.value.orig, "sqlstate", None) == "P05R1"


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE internal_review_records SET summary='rewrite' WHERE id=:id",
        "DELETE FROM internal_review_records WHERE id=:id",
        "UPDATE review_issues SET description='rewrite' WHERE review_record_id=:id",
        "DELETE FROM review_issues WHERE review_record_id=:id",
        "UPDATE review_issue_events SET occurred_at=clock_timestamp()",
        "DELETE FROM review_issue_events",
    ],
)
def test_normal_role_history_immutable(b05_env, normal_sql_role, sql):
    from researchbase.application.internal_review import ReviewIssueRequest

    env = b05_env
    seal(env)
    review = create(env, issues=(ReviewIssueRequest("MAJOR", "OTHER", "Historical issue"),))
    with pytest.raises(DBAPIError) as exc:
        with env[5].begin() as conn:
            conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
            conn.execute(text(sql), {"id": review.id})
    assert getattr(exc.value.orig, "sqlstate", None) == (
        "P17D1" if "review_issue_events" in sql else "P17F1" if "review_issues" in sql else "P17E1"
    )


@pytest.mark.parametrize("case", ["draft", "project", "hash", "multiple"])
def test_sql_rejects_invalid_target(b05_env, normal_sql_role, case):
    env = b05_env
    sealed = seal(env) if case != "draft" else None
    values = {
        "id": uuid4(),
        "project_id": uuid4() if case == "project" else env[1].project_id,
        "manuscript_version_id": env[1].manuscript_version_id,
        "claim_version_id": env[8] if case == "multiple" else None,
        "scientific_conclusion_version_id": None,
        "target_content_hash": "0" * 64
        if case in {"draft", "hash"}
        else (sealed.content_hash if sealed is not None else None),
        "reviewer_actor_id": env[3].actor_id,
        "review_type": "SCIENTIFIC",
        "recommendation": "ACCEPT",
        "summary": "SQL test",
        "content_hash": "b" * 64,
        "hash_scheme": "sha256-cjson-v1",
    }
    with pytest.raises(DBAPIError):
        with env[4]() as uow:
            uow._session.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
            values["created_at"] = uow.manuscript_freeze.at()
            uow.internal_review.insert_review(values)
            uow.commit()
    with env[5].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM internal_review_records")).scalar_one() == 0


@pytest.mark.parametrize("with_issue", [False, True])
def test_legacy_target_has_no_b05_deferred_work_after_sql_role_revocation(b05_env, with_issue):
    env = b05_env
    review = env[0].create(
        env[3],
        env[1].project_id,
        "CLAIM_VERSION",
        env[8],
        "SCIENTIFIC",
        "ACCEPT",
        "Legacy review",
        (),
        uuid4(),
    )
    role = "b05_legacy_" + uuid4().hex
    with env[5].begin() as conn:
        conn.execute(text(f"CREATE ROLE {role} NOLOGIN NOSUPERUSER"))
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        conn.execute(text(f"GRANT SELECT,INSERT,UPDATE ON ALL TABLES IN SCHEMA public TO {role}"))
        conn.execute(text(f"SET LOCAL ROLE {role}"))
        identity = uuid4()
        conn.execute(
            text("""INSERT INTO internal_review_records
            SELECT :id,project_id,manuscript_version_id,claim_version_id,scientific_conclusion_version_id,artifact_version_id,
                target_content_hash,reviewer_actor_id,review_type,recommendation,summary,clock_timestamp(),content_hash,hash_scheme
            FROM internal_review_records WHERE id=:review"""),
            {"id": identity, "review": review.id},
        )
        if with_issue:
            conn.execute(
                text("""INSERT INTO review_issues(id,review_record_id,severity,issue_type,description,status,created_at,ordinal)
                VALUES (:id,:review,'MINOR','OTHER','Legacy issue','OPEN',clock_timestamp(),0)"""),
                {"id": uuid4(), "review": identity},
            )
        if with_issue:
            # B08 now checks all Issue roots, while this still proves no B05
            # manuscript work survives after the temporary SQL role is dropped.
            conn.execute(text("SET CONSTRAINTS b08_complete_issue,b08_complete_event IMMEDIATE"))
        conn.execute(text("RESET ROLE"))
        conn.execute(text(f"DROP OWNED BY {role}"))
        conn.execute(text(f"DROP ROLE {role}"))
    with env[5].connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM internal_review_records WHERE id=:id"), {"id": identity}
            ).scalar_one()
            == 1
        )
