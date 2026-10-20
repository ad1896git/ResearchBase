"""Concrete B23 constraints, SQL sealing and reversible empty migration."""

# SQL preserves literal installed constraint checks.
# ruff: noqa: E501
from itertools import product
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from researchbase.domain.revision_action import ACTION_SHAPES
from researchbase.persistence.novelty_repository import N
from tests.integration.phase2.test_b23_novelty_review import _review, _root

pytest_plugins = ("tests.integration.phase2.pr2_18_fixtures",)


def test_catalog_and_empty_roundtrip(novelty_env):
    e = novelty_env
    with e["engine"].connect() as conn:
        constraints = dict(
            conn.execute(
                text(
                    "SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE (conname LIKE '%b23%' OR conname='ck_m1_revision_action_shape') AND contype IN ('c','f')"
                )
            ).all()
        )
        assert set(constraints) == {
            "fk_b23_review_novelty",
            "ck_b23_review_target",
            "ck_b23_review_version",
            "fk_b23_result_novelty",
            "ck_m1_revision_action_shape",
        }
        assert all(
            "ON DELETE RESTRICT" in constraints[n]
            for n in ("fk_b23_review_novelty", "fk_b23_result_novelty")
        )
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM pg_indexes WHERE indexname IN ('ix_b23_review_novelty','ix_b23_result_novelty')"
                )
            ).scalar_one()
            == 2
        )
    config = Config("alembic.ini")
    command.downgrade(config, "0068_b21_unresolved_capture")
    command.upgrade(config, "head")
    with e["engine"].connect() as conn:
        assert (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0075_m1_reconsideration"
        )


def test_v1_shape_cross_product_equivalent(novelty_env):
    with novelty_env["engine"].connect() as conn:
        expression = conn.execute(
            text(
                "SELECT pg_get_expr(conbin,conrelid) FROM pg_constraint WHERE conname='ck_m1_revision_action_shape'"
            )
        ).scalar_one()
        names = (
            "result_experiment_spec_version_id",
            "result_run_id",
            "result_statistical_result_id",
            "result_claim_version_id",
            "result_scientific_conclusion_version_id",
            "result_manuscript_version_id",
            "result_source_version_id",
        )
        rows = []
        for action in (*ACTION_SHAPES, "UNKNOWN"):
            for bits in product((False, True), repeat=7):
                rows.append(
                    (
                        action,
                        bits,
                        tuple(i for i, b in enumerate(bits) if b)
                        == ACTION_SHAPES.get(action, (-1,)),
                    )
                )
        # One PostgreSQL VALUES relation exercises the exact installed CHECK predicate.
        values = []
        for index, (action, bits, _expected) in enumerate(rows):
            values.append(
                "("
                + ",".join(
                    [
                        str(index),
                        "'" + action + "'",
                        "1",
                        "NULL::uuid",
                        "NULL::uuid",
                        "NULL::uuid",
                        *[
                            "'00000000-0000-0000-0000-000000000001'::uuid" if b else "NULL::uuid"
                            for b in bits
                        ],
                    ]
                )
                + ")"
            )
        sql = (
            "SELECT n,("
            + expression
            + ") FROM (VALUES "
            + ",".join(values)
            + ") AS a(n,action_type,material_version,result_novelty_assessment_id,review_issue_id,decision_record_id,"
            + ",".join(names)
            + ")"
        )
        actual = conn.execute(text(sql)).all()
        assert all(
            value is expected for (_, value), (_, _, expected) in zip(actual, rows, strict=True)
        )


def test_normal_role_late_issue_and_disposition_denied(novelty_env, novelty_sql_role):
    e = novelty_env
    _, root = _root(e)
    _, review = _review(e, root)
    for operation in ("late_issue", "disposition", "update", "delete"):
        with pytest.raises(DBAPIError) as error:
            with e["engine"].begin() as conn:
                conn.execute(text(f'SET LOCAL ROLE "{novelty_sql_role}"'))
                conn.execute(text("LOCK TABLE " + ",".join(N) + " IN SHARE MODE"))
                if operation == "late_issue":
                    conn.execute(
                        text(
                            "INSERT INTO review_issues(id,review_record_id,severity,issue_type,description,status,created_at,ordinal) VALUES (:id,:review,'MINOR','NOVELTY','Late','OPEN',clock_timestamp(),1)"
                        ),
                        {"id": uuid4(), "review": review.id},
                    )
                elif operation == "disposition":
                    conn.execute(
                        text(
                            "INSERT INTO review_issue_events(id,issue_id,prior_status,new_status,actor_id,occurred_at) VALUES (:id,:issue,'OPEN','ADDRESSED',:actor,clock_timestamp())"
                        ),
                        {
                            "id": uuid4(),
                            "issue": review.issues[0].id,
                            "actor": e["reviewer"].actor_id,
                        },
                    )
                elif operation == "update":
                    conn.execute(
                        text("UPDATE internal_review_records SET summary='Changed' WHERE id=:id"),
                        {"id": review.id},
                    )
                else:
                    conn.execute(
                        text("DELETE FROM internal_review_records WHERE id=:id"), {"id": review.id}
                    )
        assert getattr(error.value.orig, "sqlstate", None) in {"P17D1", "P17D2", "P17E1"}
    config = Config("alembic.ini")
    with pytest.raises(DBAPIError):
        command.downgrade(config, "0068_b21_unresolved_capture")
    with e["engine"].connect() as conn:
        assert (
            conn.execute(
                text("SELECT content_hash FROM internal_review_records WHERE id=:id"),
                {"id": review.id},
            ).scalar_one()
            == review.content_hash
        )


def _insert_row(conn, table, row):
    # Identifiers come solely from fixed table names and database column names.
    conn.execute(
        text(
            "INSERT INTO "
            + table
            + " ("
            + ",".join(row)
            + ") VALUES ("
            + ",".join(":" + key for key in row)
            + ")"
        ),
        row,
    )


@pytest.mark.parametrize(
    "mutation", ["hash", "version", "double_target", "ordinal", "foreign_edge"]
)
def test_normal_sql_review_bypass_and_deferred_sealing(novelty_env, novelty_sql_role, mutation):
    e = novelty_env
    _, root = _root(e)
    _, saved = _review(e, root)
    with e["engine"].connect() as conn:
        row = dict(
            conn.execute(
                text("SELECT * FROM internal_review_records WHERE id=:id"), {"id": saved.id}
            )
            .mappings()
            .one()
        )
    row["id"] = uuid4()
    if mutation == "hash":
        row["content_hash"] = "f" * 64
    elif mutation == "version":
        row["material_version"] = 1
    elif mutation == "double_target":
        row["claim_version_id"] = e["claim"]
    with pytest.raises(DBAPIError) as error:
        with e["engine"].begin() as conn:
            conn.execute(text(f'SET LOCAL ROLE "{novelty_sql_role}"'))
            conn.execute(text("LOCK TABLE " + ",".join(N) + " IN SHARE MODE"))
            _insert_row(conn, "internal_review_records", row)
            if mutation in {"ordinal", "foreign_edge"}:
                conn.execute(
                    text(
                        "INSERT INTO review_issues(id,review_record_id,severity,issue_type,description,status,created_at,ordinal,related_claim_version_id) VALUES (:id,:review,'MINOR','NOVELTY','Sealed child','OPEN',:at,:ordinal,:related)"
                    ),
                    {
                        "id": uuid4(),
                        "review": row["id"],
                        "at": row["created_at"],
                        "ordinal": 1 if mutation == "ordinal" else 0,
                        "related": e["claim"] if mutation == "foreign_edge" else None,
                    },
                )
            # The gap in ordinals is rejected here by deferred completeness.
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert (
        getattr(error.value.orig, "sqlstate", None)
        == {
            "hash": "P17D3",
            "version": "P17E2",
            "double_target": "23514",
            "ordinal": "P17D3",
            "foreign_edge": "P17D3",
        }[mutation]
    )
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM internal_review_records")).scalar_one() == 1
        assert conn.execute(text("SELECT count(*) FROM review_issue_events")).scalar_one() == 1


def test_same_transaction_result_denied_by_normal_sql(novelty_env, novelty_sql_role, monkeypatch):
    from dataclasses import replace

    from researchbase.domain.revision_action import RevisionReference, novelty_revision_material
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from researchbase.foundation.hashing import sha256_canonical_json
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    e = novelty_env
    c, root = _root(e)
    _, review = _review(e, root)
    successor_id = uuid4()
    intercepted = []

    def attempt_action(uow):
        session = uow._require_session()
        result = (
            session.execute(
                text(
                    "SELECT content_hash,created_at,xmin=pg_current_xact_id()::xid AS uncommitted FROM novelty_assessments WHERE id=:id"
                ),
                {"id": successor_id},
            )
            .mappings()
            .one()
        )
        assert result["uncommitted"] is True
        intercepted.append(True)
        material = novelty_revision_material(
            RevisionReference("ReviewIssue", review.issues[0].id),
            RevisionReference("NoveltyAssessment", successor_id, result["content_hash"]),
            None,
            RevisionReference("ActorIdentity", e["author"].actor_id),
        )
        session.execute(text(f'SET LOCAL ROLE "{novelty_sql_role}"'))
        session.execute(
            text(
                "INSERT INTO revision_actions(id,review_issue_id,action_type,result_novelty_assessment_id,material_version,content_hash,hash_scheme,created_by,created_at) VALUES (:id,:issue,'NOVELTY_REASSESSMENT',:result,2,:hash,'sha256-cjson-v1',:actor,clock_timestamp())"
            ),
            {
                "id": uuid4(),
                "issue": review.issues[0].id,
                "result": successor_id,
                "hash": str(sha256_canonical_json(material)),
                "actor": e["author"].actor_id,
            },
        )
        pytest.fail("uncommitted result was admitted")

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", attempt_action)
    with pytest.raises(ResearchBaseError) as error:
        e["service"].record_novelty_assessment(
            e["author"], replace(c, id=successor_id, supersedes_assessment_id=root.id)
        )
    assert intercepted == [True]
    assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM novelty_assessments")).scalar_one() == 1
        assert conn.execute(text("SELECT count(*) FROM revision_actions")).scalar_one() == 0


@pytest.mark.parametrize("mutation", ["bad_result", "hash", "version", "extra_result"])
def test_normal_sql_revision_bypass_denied(novelty_env, novelty_sql_role, mutation):
    from dataclasses import replace

    from researchbase.application.revision_action import (
        RecordNoveltyRevisionCommand,
        RevisionActionService,
    )

    e = novelty_env
    c, root = _root(e)
    _, review = _review(e, root)
    result = e["service"].record_novelty_assessment(
        e["author"], replace(c, id=uuid4(), supersedes_assessment_id=root.id)
    )
    actions = RevisionActionService(e["factory"], e["credentials"], e["literature"])
    saved = actions.record_novelty_revision(
        e["author"],
        RecordNoveltyRevisionCommand(uuid4(), e["project"], review.issues[0].id, result.id),
    )
    with e["engine"].connect() as conn:
        row = dict(
            conn.execute(text("SELECT * FROM revision_actions WHERE id=:id"), {"id": saved.id})
            .mappings()
            .one()
        )
    row["id"] = uuid4()
    if mutation == "bad_result":
        row["result_novelty_assessment_id"] = root.id
    elif mutation == "hash":
        row["content_hash"] = "f" * 64
    elif mutation == "version":
        row["material_version"] = 1
    else:
        row["result_claim_version_id"] = e["claim"]
    with pytest.raises(DBAPIError) as error:
        with e["engine"].begin() as conn:
            conn.execute(text(f'SET LOCAL ROLE "{novelty_sql_role}"'))
            conn.execute(text("LOCK TABLE " + ",".join(N) + " IN SHARE MODE"))
            _insert_row(conn, "revision_actions", row)
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert (
        getattr(error.value.orig, "sqlstate", None)
        == {"bad_result": "P17D2", "hash": "P17D3", "version": "P17F2", "extra_result": "23514"}[
            mutation
        ]
    )
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM revision_actions")).scalar_one() == 1


@pytest.mark.parametrize(
    "mutation", ["wrong_review", "wrong_actor", "late_time", "update", "delete"]
)
def test_normal_sql_link_guards_and_immutable_correspondence(
    novelty_env, novelty_sql_role, mutation
):
    from dataclasses import replace

    from researchbase.application.revision_action import (
        RecordConcernReReviewCommand,
        RecordNoveltyRevisionCommand,
        RevisionActionService,
    )

    e = novelty_env
    c, root = _root(e)
    _, original = _review(e, root)
    result = e["service"].record_novelty_assessment(
        e["author"], replace(c, id=uuid4(), supersedes_assessment_id=root.id)
    )
    actions = RevisionActionService(e["factory"], e["credentials"], e["literature"])
    action = actions.record_novelty_revision(
        e["researcher"],
        RecordNoveltyRevisionCommand(uuid4(), e["project"], original.issues[0].id, result.id),
    )
    _, review = _review(e, result, issues=())
    if mutation in {"update", "delete"}:
        actions.record_concern_re_review(
            e["reviewer"],
            RecordConcernReReviewCommand(e["project"], action.id, review.id),
            novelty=True,
        )
    with pytest.raises(DBAPIError) as error:
        with e["engine"].begin() as conn:
            conn.execute(text(f'SET LOCAL ROLE "{novelty_sql_role}"'))
            conn.execute(text("LOCK TABLE " + ",".join(N) + " IN SHARE MODE"))
            if mutation == "update":
                conn.execute(
                    text(
                        "UPDATE revision_action_re_reviews SET recorded_at=clock_timestamp() WHERE revision_action_id=:id"
                    ),
                    {"id": action.id},
                )
            elif mutation == "delete":
                conn.execute(
                    text("DELETE FROM revision_action_re_reviews WHERE revision_action_id=:id"),
                    {"id": action.id},
                )
            else:
                conn.execute(
                    text(
                        "INSERT INTO revision_action_re_reviews(revision_action_id,internal_review_record_id,recorded_by,recorded_at) VALUES (:action,:review,:actor,CASE WHEN :late THEN clock_timestamp()+interval '1 hour' ELSE clock_timestamp() END)"
                    ),
                    {
                        "action": action.id,
                        "review": original.id if mutation == "wrong_review" else review.id,
                        "actor": e["owner"].actor_id
                        if mutation == "wrong_actor"
                        else e["reviewer"].actor_id,
                        "late": mutation == "late_time",
                    },
                )
                conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert getattr(error.value.orig, "sqlstate", None) == (
        "P17F1" if mutation in {"update", "delete"} else "P17D3"
    )
    with e["engine"].connect() as conn:
        assert conn.execute(
            text("SELECT count(*) FROM revision_action_re_reviews")
        ).scalar_one() == (1 if mutation in {"update", "delete"} else 0)


def test_populated_v1_upgrade_preserves_hashes_and_children(novelty_env):
    from researchbase.application.internal_review import InternalReviewService, ReviewIssueRequest

    e = novelty_env
    config = Config("alembic.ini")
    command.downgrade(config, "0068_b21_unresolved_capture")
    reviews = InternalReviewService(e["factory"], e["credentials"], e["literature"])
    review = reviews.create(
        e["reviewer"],
        e["project"],
        "CLAIM_VERSION",
        e["claim"],
        "SCIENTIFIC",
        "UNCERTAIN",
        "Retained v1 material",
        (ReviewIssueRequest("MINOR", "OTHER", "Retained Issue"),),
        uuid4(),
    )
    with e["engine"].connect() as conn:
        before = dict(
            conn.execute(
                text("SELECT * FROM internal_review_records WHERE id=:id"), {"id": review.id}
            )
            .mappings()
            .one()
        )
        issues = conn.execute(
            text("SELECT * FROM review_issues WHERE review_record_id=:id"), {"id": review.id}
        ).all()
        events = conn.execute(
            text("SELECT * FROM review_issue_events WHERE issue_id=:id"),
            {"id": review.issues[0].id},
        ).all()
    command.upgrade(config, "head")
    with e["engine"].connect() as conn:
        after = dict(
            conn.execute(
                text("SELECT * FROM internal_review_records WHERE id=:id"), {"id": review.id}
            )
            .mappings()
            .one()
        )
        assert after.pop("material_version") == 1
        assert after.pop("novelty_assessment_id") is None
        assert after == before
        assert (
            conn.execute(
                text("SELECT * FROM review_issues WHERE review_record_id=:id"), {"id": review.id}
            ).all()
            == issues
        )
        assert (
            conn.execute(
                text("SELECT * FROM review_issue_events WHERE issue_id=:id"),
                {"id": review.issues[0].id},
            ).all()
            == events
        )
    assert reviews.read(e["reviewer"], e["project"], review.id).content_hash == review.content_hash


def test_pinned_guard_definitions_restore_byte_for_byte(novelty_env):
    import runpy

    migration = runpy.run_path("migrations/versions/0071_b23_novelty_review.py")
    legacy: dict[str, str] = migration["LEGACY"]
    dispatch: dict[str, str] = migration["DISPATCH"]
    # Append the active forward-migration values; the accepted B23 inventory stays pinned.
    import re

    m1 = runpy.run_path("migrations/versions/0074_m1_manuscript_revision.py")
    for definition in re.findall(
        r"CREATE OR REPLACE FUNCTION public\.[\s\S]*?\$function\$;", m1["_UPGRADE"]
    ):
        name = definition.split("public.", 1)[1].split("(", 1)[0]
        if name in dispatch:
            dispatch[name] = definition.removesuffix(";") + "\n"
    expected_triggers: dict[str, str] = migration["TRIGGERS"]
    engine = novelty_env["engine"]
    config = Config("alembic.ini")

    def functions():
        with engine.connect() as conn:
            return {
                name: definition.encode("utf-8")
                for name, definition in conn.execute(
                    text(
                        "SELECT proname,pg_get_functiondef(oid) FROM pg_proc "
                        "WHERE pronamespace='public'::regnamespace AND proname=ANY(:names)"
                    ),
                    {"names": list(legacy)},
                )
            }

    def triggers_and_checks():
        with engine.connect() as conn:
            triggers = dict(
                conn.execute(
                    text(
                        "SELECT tgname,pg_get_triggerdef(oid) FROM pg_trigger "
                        "WHERE NOT tgisinternal AND tgname=ANY(:names) "
                        "AND tgrelid IN ('internal_review_records'::regclass,"
                        "'review_issues'::regclass,'review_issue_events'::regclass,"
                        "'revision_actions'::regclass,'revision_action_re_reviews'::regclass)"
                    ),
                    {"names": list(expected_triggers)},
                ).all()
            )
            checks = dict(
                conn.execute(
                    text(
                        "SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint "
                        "WHERE conname IN ('ck_pr214_one_target','revision_action_shape')"
                    )
                ).all()
            )
            return triggers, checks

    # Compare the actual installed head against the entire pinned dispatch text.
    assert functions() == {
        name: definition.encode("utf-8") for name, definition in dispatch.items()
    }
    command.downgrade(config, "0068_b21_unresolved_capture")
    expected_legacy = {name: definition.encode("utf-8") for name, definition in legacy.items()}
    assert functions() == expected_legacy
    before_triggers, before_checks = triggers_and_checks()
    assert before_triggers == expected_triggers
    assert set(before_checks) == {"ck_pr214_one_target", "revision_action_shape"}

    command.upgrade(config, "head")
    assert functions() == {
        name: definition.encode("utf-8") for name, definition in dispatch.items()
    }
    command.downgrade(config, "0068_b21_unresolved_capture")
    assert functions() == expected_legacy
    assert triggers_and_checks() == (before_triggers, before_checks)
    command.upgrade(config, "head")
