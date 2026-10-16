"""B07 forward-only admission, normal-role guards and RESTRICT catalog."""

from contextlib import contextmanager
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from tests.integration.phase2.test_b07_revision_decisions import decision_command
from tests.integration.phase2.test_pr2_15_decision_schema import _config, _tables
from tests.integration.phase2.test_revision_action import (
    conclusion_env,
    decision_env,
    phase2_database_url,
    revision_env,
)

pytestmark = pytest.mark.integration
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
_FIXTURES = (conclusion_env, decision_env, phase2_database_url, revision_env)
TABLES = {"decision_basis_claims", "decision_revision_concerns", "revision_action_re_reviews"}


@contextmanager
def normal_role(engine):
    role = "b07_normal_" + uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f"CREATE ROLE {role} NOLOGIN NOSUPERUSER"))
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        conn.execute(
            text(f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {role}")
        )
        conn.execute(text(f"SET LOCAL ROLE {role}"))
        yield conn
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        conn.execute(text("RESET ROLE"))
        conn.execute(text(f"DROP OWNED BY {role}"))
        conn.execute(text(f"DROP ROLE {role}"))


def test_empty_forward_upgrade_and_downgrade(phase2_database_url):
    config = _config(phase2_database_url)
    command.upgrade(config, "0051_b06_revision_action")
    engine = create_engine(phase2_database_url)
    try:
        with engine.connect() as conn:
            before = _tables(conn)
        command.upgrade(config, "head")
        with engine.connect() as conn:
            assert _tables(conn) - before == TABLES
            fks = (
                conn.execute(
                    text(
                        "SELECT confdeltype FROM pg_constraint WHERE contype='f' AND conrelid IN "
                        "(SELECT oid FROM pg_class WHERE relname=ANY(:tables))"
                    ),
                    {"tables": list(TABLES)},
                )
                .scalars()
                .all()
            )
            assert len(fks) == 7 and set(fks) == {"r"}
            triggers = conn.execute(
                text(
                    "SELECT tgname,tgdeferrable,tginitdeferred FROM pg_trigger WHERE "
                    "tgname=ANY(:names)"
                ),
                {
                    "names": [
                        "b07_complete_decision",
                        "b07_complete_claim",
                        "b07_complete_concern",
                        "b07_complete_re_review",
                    ]
                },
            ).all()
            assert len(triggers) == 4 and all(x[1] and x[2] for x in triggers)
        command.downgrade(config, "0051_b06_revision_action")
        with engine.connect() as conn:
            assert _tables(conn) == before
        command.upgrade(config, "head")
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "table",
    [
        "decision_records",
        "decision_revision_concerns",
        "decision_basis_conclusions",
        "decision_basis_reviews",
    ],
)
@pytest.mark.parametrize("verb", ["UPDATE", "DELETE"])
def test_new_revision_history_is_immutable(revision_env, table, verb):
    _, action, env, _, _ = revision_env
    d = env[0].record_revision_decision(env[2], decision_command(env, action.review_issue_id))
    engine = env[-1][8]
    column = "id" if table == "decision_records" else "decision_id"
    sql = (
        f"UPDATE {table} SET {column}={column} WHERE {column}=:id"
        if verb == "UPDATE"
        else f"DELETE FROM {table} WHERE {column}=:id"
    )
    with pytest.raises(DBAPIError) as caught, normal_role(engine) as conn:
        conn.execute(text(sql), {"id": d.id})
    assert getattr(caught.value.orig, "sqlstate", None) == "P17F1"


def test_revision_history_refuses_downgrade_and_late_append(revision_env, phase2_database_url):
    _, action, env, _, _ = revision_env
    d = env[0].record_revision_decision(env[2], decision_command(env, action.review_issue_id))
    with pytest.raises(DBAPIError) as caught:
        command.downgrade(_config(phase2_database_url), "0051_b06_revision_action")
    assert getattr(caught.value.orig, "sqlstate", None) == "P17F2"
    with pytest.raises(DBAPIError) as caught, normal_role(env[-1][8]) as conn:
        conn.execute(
            text("INSERT INTO decision_revision_concerns VALUES (:id,:issue)"),
            {"id": d.id, "issue": action.review_issue_id},
        )
    assert getattr(caught.value.orig, "sqlstate", None) == "P17F1"


@pytest.mark.parametrize("missing", ["all", "concern", "review", "target"])
def test_direct_sql_incomplete_parent_or_children_rolls_back(revision_env, missing):
    _, action, env, _, _ = revision_env
    base = env[-1]
    from researchbase.application.internal_review import ReviewIssueRequest
    from tests.integration.phase2.test_pr2_15_decision import _review

    extra = _review(env, "REJECT", (ReviewIssueRequest("MAJOR", "OTHER", "Separate concern"),))
    saved = env[0].record_revision_decision(env[2], decision_command(env, action.review_issue_id))
    with pytest.raises(DBAPIError) as caught, normal_role(base[8]) as conn:
        # New exact concern to avoid masking completeness with scope uniqueness.
        issue = extra.issues[0].id
        identity = uuid4()
        conn.execute(
            text(
                "INSERT INTO decision_records SELECT "
                ":id,project_id,decision_type,question,decision,rationale,decided_by,decided_at,"
                "supersedes_decision_id,basis_set_hash,content_hash,hash_scheme "
                "FROM decision_records WHERE id=:old"
            ),
            {"id": identity, "old": saved.id},
        )
        if missing not in {"all", "concern"}:
            conn.execute(
                text("INSERT INTO decision_revision_concerns VALUES (:id,:issue)"),
                {"id": identity, "issue": issue},
            )
        if missing not in {"all", "target"}:
            conn.execute(
                text(
                    "INSERT INTO decision_basis_conclusions SELECT "
                    ":id,scientific_conclusion_version_id,ordinal FROM "
                    "decision_basis_conclusions WHERE decision_id=:old"
                ),
                {"id": identity, "old": saved.id},
            )
        if missing not in {"all", "review"}:
            conn.execute(
                text(
                    "INSERT INTO decision_basis_reviews SELECT "
                    ":id,internal_review_record_id,ordinal FROM decision_basis_reviews WHERE "
                    "decision_id=:old"
                ),
                {"id": identity, "old": saved.id},
            )
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert getattr(caught.value.orig, "sqlstate", None) == "P17F2"


def test_typed_traversal_never_infers_target_type_from_uuid_existence(revision_env):
    base = revision_env[2][-1]
    with normal_role(base[8]) as conn:
        conn.execute(
            text("SELECT b07_target(:id,:project,'claim_versions')"),
            {"id": base[6], "project": base[5]},
        )
    with pytest.raises(DBAPIError) as caught, normal_role(base[8]) as conn:
        conn.execute(
            text("SELECT b07_target(:id,:project,'scientific_conclusion_versions')"),
            {"id": base[6], "project": base[5]},
        )
    assert getattr(caught.value.orig, "sqlstate", None) == "P17F2"


def test_deferred_link_still_rejects_later_same_transaction_invalidation(revision_env):
    service, action, env, _, revised = revision_env
    base = env[-1]
    saved = service.record_revision_action(base[3], action)
    review = env[1].create(
        env[2],
        base[5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        revised.version_id,
        "SCIENTIFIC",
        "ACCEPT",
        "TEST ONLY independent",
        (),
        uuid4(),
    )
    with pytest.raises(DBAPIError) as caught, normal_role(base[8]) as conn:
        conn.execute(
            text(
                "INSERT INTO revision_action_re_reviews "
                "VALUES (:action,:review,:actor,clock_timestamp())"
            ),
            {"action": saved.id, "review": review.id, "actor": env[2].actor_id},
        )
        assessment = uuid4()
        # An ordinary SQL caller can mutate its own SHARE-protected inventory.
        # Deferred validation must still deny the resulting invalid target.
        conn.execute(
            text(
                "INSERT INTO impact_assessments(id,project_id,audit_finding_id,assessment_payload,"
                "conclusion,created_by,created_at,content_hash) VALUES "
                "(:id,:project,NULL,'{}','INVALID',:actor,clock_timestamp(),:hash)"
            ),
            {"id": assessment, "project": base[5], "actor": base[3].actor_id, "hash": "a" * 64},
        )
        conn.execute(
            text(
                "INSERT INTO impact_targets"
                "(impact_assessment_id,target_type,target_id,impact_kind) "
                "VALUES (:id,'CLAIM_VERSION',:target,'INVALID')"
            ),
            {"id": assessment, "target": base[6]},
        )
        conn.execute(text("SET CONSTRAINTS b07_complete_re_review IMMEDIATE"))
    assert getattr(caught.value.orig, "sqlstate", None) == "P17F2"
    with base[8].connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM revision_action_re_reviews")).scalar_one() == 0
        )


def test_upgrade_preflights_retained_release_without_reapplying_late_blockers(
    decision_env, phase2_database_url
):
    from researchbase.application.internal_review import ReviewIssueRequest
    from tests.integration.phase2.test_pr2_15_decision import _command, _review

    env = decision_env
    base = env[-1]
    _review(env)
    saved = env[0].record_decision(env[2], _command(env))
    _review(env, "REJECT", (ReviewIssueRequest("BLOCKING", "OTHER", "Later exact concern"),))
    config = _config(phase2_database_url)
    command.downgrade(config, "0051_b06_revision_action")
    with base[8].connect() as conn:
        before = conn.execute(
            text("SELECT id,basis_set_hash,content_hash FROM decision_records")
        ).all()
    command.upgrade(config, "head")
    with base[8].connect() as conn:
        assert (
            conn.execute(text("SELECT id,basis_set_hash,content_hash FROM decision_records")).all()
            == before
        )
    with base[1]() as uow:
        assert env[0]._readback(uow, uow.decision.decision(saved.id, base[5])) == saved


@pytest.mark.parametrize("input_kind", ["snapshot", "direct"])
def test_current_validity_never_inherits_unrelated_conclusion_with_same_uuid(
    revision_env, input_kind
):
    from tests.integration.phase2.test_b06_revision_action import _source_response

    _, _, env, _, _ = revision_env
    base = env[-1]
    _source_response(env, "claim", "CORRECTED")
    with normal_role(base[8]) as conn:
        conn.execute(
            text(
                "INSERT INTO scientific_conclusion_versions "
                "(id,scientific_conclusion_id,version_number,status,statement,scope,confidence,"
                "limitation_summary,support_set_hash,content_hash,hash_scheme,created_by,"
                "created_at,frozen_at,row_version) SELECT :claim,scientific_conclusion_id,"
                "version_number+100,'DRAFT',statement,scope,confidence,limitation_summary,"
                "NULL,NULL,hash_scheme,created_by,clock_timestamp(),NULL,1 "
                "FROM scientific_conclusion_versions WHERE id=:conclusion"
            ),
            {"claim": base[6], "conclusion": env[3].version_id},
        )
        if input_kind == "snapshot":
            conn.execute(
                text(
                    "INSERT INTO scientific_conclusion_claim_inputs "
                    "SELECT :claim,:claim,id,'SUPPORTS',0 FROM literature_support_snapshots "
                    "WHERE claim_version_id=:claim ORDER BY snapshot_number LIMIT 1"
                ),
                {"claim": base[6]},
            )
        else:
            conn.execute(
                text(
                    "INSERT INTO scientific_conclusion_literature_inputs "
                    "SELECT :claim,id,'SUPPORTS',0 FROM literature_evidence "
                    "WHERE source_version_id=:source LIMIT 1"
                ),
                {"claim": base[6], "source": base[7]},
            )
        conn.execute(
            text("SELECT b07_current_target(:id,:project,'claim_versions')"),
            {"id": base[6], "project": base[5]},
        )
    with pytest.raises(DBAPIError) as caught, normal_role(base[8]) as conn:
        conn.execute(
            text("SELECT b07_current_target(:id,:project,'scientific_conclusion_versions')"),
            {"id": base[6], "project": base[5]},
        )
    assert getattr(caught.value.orig, "sqlstate", None) == "P17F2"
