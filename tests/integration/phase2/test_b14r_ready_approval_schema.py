"""Forward-only function amendment and ordinary-role final-graph guards."""

# SQL assertions preserve the literal lock and guard protocol.
# ruff: noqa: E501

from dataclasses import replace
from uuid import uuid4

import pytest
from alembic import command as alembic
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from researchbase.persistence.approval_repository import B09_SHARE_SQL
from tests.disposable_postgres import disposable_database
from tests.integration.phase2.test_b04_manuscript_migration import normal_sql_role
from tests.integration.phase2.test_b14a_entry_schema import catalog_inventory, config
from tests.integration.phase2.test_b14r_ready_approval import (
    b04_env,
    b05_env,
    conclusion_env,
    counts,
    decide,
    phase2_database_url,
    setup,
)
from tests.integration.phase2.test_revision_action import decision_env, revision_env

_FIXTURES = (
    b04_env,
    b05_env,
    conclusion_env,
    phase2_database_url,
    normal_sql_role,
    decision_env,
    revision_env,
)
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("start", ["base", "0062_b14a_publication_entry"])
def test_clean_upgrade_changes_only_four_functions_and_exact_empty_downgrade(start, monkeypatch):
    with disposable_database("researchbase_pr212_test_", "RB_PR210_TEST_ADMIN_URL") as url:
        monkeypatch.setenv("DATABASE_URL", url)
        cfg = config(url)
        alembic.upgrade(cfg, start)
        alembic.upgrade(cfg, "0062_b14a_publication_entry")
        engine = create_engine(url)
        try:
            with engine.connect() as conn:
                before = catalog_inventory(conn)
            alembic.upgrade(cfg, "0063_b14r_ready_approval")
            with engine.connect() as conn:
                after = catalog_inventory(conn)
                assert conn.execute(text("SHOW server_version_num")).scalar_one().startswith("18")
            for key in before.keys() - {"functions"}:
                assert before[key] == after[key]
            old = {row[:2]: row[2] for row in before["functions"]}
            new = {row[:2]: row[2] for row in after["functions"]}
            changed = {key[0] for key in new if new[key] != old.get(key)}
            assert changed == {
                "pr216_gate",
                "pr216_complete",
                "b14r_saved_decision",
                "b14r_approval_gate",
            }
            assert not old.keys() - new.keys()
            alembic.downgrade(cfg, "0062_b14a_publication_entry")
            with engine.connect() as conn:
                assert catalog_inventory(conn) == before
            alembic.upgrade(cfg, "0063_b14r_ready_approval")
            with engine.connect() as conn:
                assert catalog_inventory(conn) == after
        finally:
            engine.dispose()


def test_populated_predecessor_preserved_and_ready_history_refuses_downgrade(b05_env):
    env = b05_env
    cfg = config(env[5].url.render_as_string(hide_password=False))
    # Pin this predecessor migration test before creating retained entry history;
    # B14's extension correctly refuses downgrade once that history exists.
    alembic.downgrade(cfg, "0063_b14r_ready_approval")
    app, cmd, actor = setup(env)
    alembic.downgrade(cfg, "0062_b14a_publication_entry")
    alembic.upgrade(cfg, "0063_b14r_ready_approval")
    app.request_approval(env[2], cmd)
    app.decide_approval(actor, decide(cmd))
    before = counts(env)
    with env[5].connect() as conn:
        catalog = catalog_inventory(conn)
    with pytest.raises(DBAPIError) as error:
        alembic.downgrade(cfg, "0062_b14a_publication_entry")
    assert getattr(error.value.orig, "sqlstate", None) == "P17F1"
    assert counts(env) == before
    with env[5].connect() as conn:
        assert catalog_inventory(conn) == catalog
        assert (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0063_b14r_ready_approval"
        )


def insert_request(conn, cmd, actor, *, reviews=True):
    conn.execute(
        text("""INSERT INTO approval_requests(id,project_id,manuscript_version_id,
      target_content_hash,target_hash_scheme,approval_purpose,requested_by,requested_at,
      basis_decision_id,status) SELECT :id,:project,m.id,m.content_hash,m.hash_scheme,
      :purpose,:actor,clock_timestamp(),:basis,'PENDING' FROM manuscript_versions m WHERE m.id=:target"""),
        dict(
            id=cmd.id,
            project=cmd.project_id,
            target=cmd.manuscript_version_id,
            purpose=cmd.approval_purpose,
            actor=actor,
            basis=cmd.basis_decision_id,
        ),
    )
    if reviews:
        for review in cmd.review_ids:
            conn.execute(
                text(
                    "INSERT INTO approval_request_reviews(request_id,internal_review_record_id) VALUES (:id,:review)"
                ),
                dict(id=cmd.id, review=review),
            )


@pytest.mark.parametrize(
    "attack",
    [
        "no_prefix",
        "wrong_isolation",
        "missing_reviews",
        "extra_review",
        "wrong_basis",
        "wrong_purpose",
        "late_child",
        "event_forgery",
        "edit",
        "delete",
    ],
)
def test_normal_role_denies_invalid_graph_atomically(b05_env, normal_sql_role, attack):
    env = b05_env
    app, cmd, _ = setup(env)
    if attack in {"late_child", "edit", "delete", "event_forgery"}:
        app.request_approval(env[2], cmd)
    before = counts(env)
    with pytest.raises(DBAPIError):
        with (
            env[5]
            .connect()
            .execution_options(
                isolation_level="REPEATABLE READ"
                if attack == "wrong_isolation"
                else "READ COMMITTED"
            ) as conn
        ):
            with conn.begin():
                if attack != "no_prefix":
                    conn.execute(text(B09_SHARE_SQL))
                conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
                if attack in {"edit", "delete"}:
                    conn.execute(
                        text(
                            "DELETE FROM approval_requests WHERE id=:id"
                            if attack == "delete"
                            else "UPDATE approval_requests SET requested_at=clock_timestamp() WHERE id=:id"
                        ),
                        {"id": cmd.id},
                    )
                elif attack == "late_child":
                    conn.execute(
                        text(
                            "INSERT INTO approval_request_reviews(request_id,internal_review_record_id) VALUES (:id,:review)"
                        ),
                        dict(id=cmd.id, review=cmd.review_ids[0]),
                    )
                elif attack == "event_forgery":
                    conn.execute(
                        text(
                            "INSERT INTO approval_request_events(id,request_id,new_status,actor_id,occurred_at,reason) VALUES (:id,:request,'PENDING',:actor,clock_timestamp(),'request created')"
                        ),
                        dict(id=uuid4(), request=cmd.id, actor=env[2].actor_id),
                    )
                else:
                    bad = replace(
                        cmd,
                        **(
                            {"basis_decision_id": uuid4()}
                            if attack == "wrong_basis"
                            else {"approval_purpose": "PREPARE_SUBMISSION"}
                            if attack == "wrong_purpose"
                            else {"review_ids": cmd.review_ids + (uuid4(),)}
                            if attack == "extra_review"
                            else {}
                        ),
                    )
                    insert_request(conn, bad, env[2].actor_id, reviews=attack != "missing_reviews")
                conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert counts(env) == before


def test_complete_request_succeeds_through_normal_role_sql(b05_env, normal_sql_role):
    env = b05_env
    _, cmd, _ = setup(env)
    with env[5].begin() as conn:
        conn.execute(text(B09_SHARE_SQL))
        conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
        insert_request(conn, cmd, env[2].actor_id)
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert counts(env) == (1, 1, 1, 0, 0, 0)


def insert_blocker(conn, env, cmd, *, upstream=False):
    from researchbase.foundation.hashing import sha256_canonical_json

    target = env[8] if upstream else cmd.manuscript_version_id
    table = "claim_versions" if upstream else "manuscript_versions"
    column = "claim_version_id" if upstream else "manuscript_version_id"
    kind = "ClaimVersion" if upstream else "ManuscriptVersion"
    digest = conn.execute(
        text(f"SELECT content_hash FROM {table} WHERE id=:id"), dict(id=target)
    ).scalar_one()
    review = uuid4()
    material = dict(
        type="InternalReviewRecord",
        material_version=1,
        project_id=str(cmd.project_id),
        target=dict(type=kind, id=str(target), content_hash=digest),
        reviewer_actor_id=str(env[3].actor_id),
        review_type="SCIENTIFIC",
        recommendation="REJECT",
        summary="New blocker",
    )
    hashed = str(sha256_canonical_json(material))
    conn.execute(
        text(
            f"INSERT INTO internal_review_records(id,project_id,{column},target_content_hash,reviewer_actor_id,review_type,recommendation,summary,created_at,content_hash,hash_scheme) VALUES (:id,:project,:target,:digest,:actor,'SCIENTIFIC','REJECT','New blocker',clock_timestamp(),:hash,'sha256-cjson-v1')"
        ),
        dict(
            id=review,
            project=cmd.project_id,
            target=target,
            digest=digest,
            actor=env[3].actor_id,
            hash=hashed,
        ),
    )
    conn.execute(
        text(
            "INSERT INTO review_issues(id,review_record_id,severity,issue_type,description,status,created_at,ordinal) VALUES (:id,:review,'BLOCKING','OTHER','New blocker','OPEN',clock_timestamp(),0)"
        ),
        dict(id=uuid4(), review=review),
    )


def test_final_graph_rechecks_later_blocker_in_same_transaction(b05_env, normal_sql_role):
    env = b05_env
    _, cmd, _ = setup(env)
    with pytest.raises(DBAPIError) as error:
        with env[5].begin() as conn:
            conn.execute(text(B09_SHARE_SQL))
            conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
            insert_request(conn, cmd, env[2].actor_id)
            insert_blocker(conn, env, cmd)
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert getattr(error.value.orig, "sqlstate", None) == "P16G1"
    assert counts(env) == (0,) * 6


@pytest.mark.parametrize(
    "attack", ["no_grant", "reject_with_grant", "wrong_scope", "wrong_hash", "consent"]
)
def test_normal_role_decision_and_grant_are_one_exact_atomic_graph(
    b05_env, normal_sql_role, attack
):
    from researchbase.domain.approval import approval_decision_material
    from researchbase.foundation.hashing import sha256_canonical_json

    env = b05_env
    app, cmd, actor = setup(env)
    request = app.request_approval(env[2], cmd)
    assert cmd.manuscript_version_id is not None
    before = counts(env)
    with pytest.raises(DBAPIError):
        with env[5].begin() as conn:
            conn.execute(text(B09_SHARE_SQL))
            conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
            identity = uuid4()
            outcome = "REJECT" if attack == "reject_with_grant" else "APPROVE"
            digest = str(
                sha256_canonical_json(
                    approval_decision_material(
                        cmd.id,
                        cmd.manuscript_version_id,
                        request.target_content_hash,
                        outcome,
                        None,
                        False,
                        "Permission",
                        actor.actor_id,
                        target_type="ManuscriptVersion",
                    )
                )
            )
            at = conn.execute(
                text(
                    "INSERT INTO approval_decisions(id,approval_request_id,decision,valid_until,requires_current_author_consent,rationale,decided_by,decided_at,content_hash,hash_scheme) VALUES (:id,:request,:outcome,NULL,:consent,'Permission',:actor,clock_timestamp(),:hash,'sha256-cjson-v1') RETURNING decided_at"
                ),
                dict(
                    id=identity,
                    request=cmd.id,
                    outcome=outcome,
                    consent=attack == "consent",
                    actor=actor.actor_id,
                    hash="0" * 64 if attack == "wrong_hash" else digest,
                ),
            ).scalar_one()
            if attack != "no_grant":
                conn.execute(
                    text(
                        "INSERT INTO approval_grants(id,approval_decision_id,project_id,purpose,allowed_command,status,valid_until) VALUES (:id,:decision,:project,'READY_FOR_SUBMISSION',:command,'ACTIVE',:at+interval '720 hours')"
                    ),
                    dict(
                        id=uuid4(),
                        decision=identity,
                        project=cmd.project_id,
                        command="prepare_submission"
                        if attack == "wrong_scope"
                        else "transition_publication_ready",
                        at=at,
                    ),
                )
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert counts(env) == before
