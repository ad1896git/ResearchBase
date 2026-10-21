"""B10 forward DDL and normal-role immutable/deferred evidence enforcement."""

from uuid import uuid4

import pytest
from alembic import command as migration
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from researchbase.persistence.approval_repository import B09_SHARE_SQL
from tests.integration.phase2 import test_b10_reconsideration as fixtures

approval_env = fixtures.approval_env
conclusion_env = fixtures.conclusion_env
decision_env = fixtures.decision_env
phase2_database_url = fixtures.phase2_database_url
reconsideration_env = fixtures.reconsideration_env
pytestmark = pytest.mark.integration


def config(env):
    c = Config("alembic.ini")
    c.set_main_option("sqlalchemy.url", env[-1][8].url.render_as_string(hide_password=False))
    return c


def normal_role(conn):
    role = "b10_test_" + uuid4().hex
    conn.execute(text(f"CREATE ROLE {role} NOSUPERUSER NOLOGIN"))
    conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
    conn.execute(
        text(f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {role}")
    )
    conn.execute(text(f"SET LOCAL ROLE {role}"))
    assert not conn.execute(
        text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")
    ).scalar_one()


def clone(conn, source, new, mode):
    conn.execute(
        text("""INSERT INTO decision_records
    (id,project_id,decision_type,question,decision,rationale,decided_by,decided_at,
     supersedes_decision_id,basis_set_hash,content_hash,hash_scheme)
    SELECT :new,project_id,decision_type,question,decision,rationale,decided_by,clock_timestamp(),
     supersedes_decision_id,basis_set_hash,
     CASE WHEN :forge THEN repeat('0',64) ELSE content_hash END,hash_scheme
    FROM decision_records WHERE id=:source"""),
        {"new": new, "source": source, "forge": mode == "hash"},
    )
    for table, key in (
        ("decision_basis_approval_decisions", "approval_decision_id"),
        ("decision_basis_conclusions", "scientific_conclusion_version_id"),
        ("decision_basis_reviews", "internal_review_record_id"),
        ("decision_basis_revision_actions", "revision_action_id"),
    ):
        if mode == "partial" and table == "decision_basis_reviews":
            continue
        conn.execute(
            text(f"""INSERT INTO {table}(decision_id,{key},ordinal)
         SELECT :new,{key},ordinal+CASE WHEN :shift THEN 10 ELSE 0 END
         FROM {table} WHERE decision_id=:source"""),
            {
                "new": new,
                "source": source,
                "shift": mode == "ordinal" and table == "decision_basis_reviews",
            },
        )


@pytest.mark.parametrize(
    "mode,code", [("hash", "P17F2"), ("partial", "P10B1"), ("ordinal", "P10B1")]
)
@pytest.mark.parametrize("force", [False, True])
def test_normal_sql_rejects_forged_or_incomplete_final_graph(
    reconsideration_env, mode, code, force
):
    service, command, actor, approval = reconsideration_env
    saved = service.record_rejection_reconsideration(command, actor)
    engine = approval[-1][-1][8]
    with engine.connect() as conn:
        tx = conn.begin()
        conn.execute(text(B09_SHARE_SQL))
        normal_role(conn)
        with pytest.raises(DBAPIError) as denied:
            clone(conn, saved.id, uuid4(), mode)
            if force:
                conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            else:
                tx.commit()
        assert getattr(denied.value.orig, "sqlstate", None) == code
        if tx.is_active:
            tx.rollback()
    assert (
        service.get_rejection_reconsideration(command.project_id, saved.id, actor).content_hash
        == saved.content_hash
    )


@pytest.mark.parametrize("operation", ["UPDATE", "DELETE", "APPEND"])
@pytest.mark.parametrize(
    "table,key",
    [
        ("decision_basis_approval_decisions", "approval_decision_id"),
        ("decision_basis_reviews", "internal_review_record_id"),
        ("decision_basis_conclusions", "scientific_conclusion_version_id"),
    ],
)
def test_committed_children_cannot_mutate_or_grow(reconsideration_env, operation, table, key):
    service, command, actor, approval = reconsideration_env
    saved = service.record_rejection_reconsideration(command, actor)
    with approval[-1][-1][8].connect() as conn:
        tx = conn.begin()
        conn.execute(text(B09_SHARE_SQL))
        normal_role(conn)
        query = (
            f"UPDATE {table} SET ordinal=ordinal WHERE decision_id=:id"
            if operation == "UPDATE"
            else f"DELETE FROM {table} WHERE decision_id=:id"
            if operation == "DELETE"
            else f"INSERT INTO {table} SELECT * FROM {table} WHERE decision_id=:id"
        )
        with pytest.raises(DBAPIError) as denied:
            conn.execute(text(query), {"id": saved.id})
        assert getattr(denied.value.orig, "sqlstate", None) == "P17F1"
        tx.rollback()


def test_direct_sql_must_prehold_inventory(reconsideration_env):
    service, command, actor, approval = reconsideration_env
    saved = service.record_rejection_reconsideration(command, actor)
    with approval[-1][-1][8].connect() as conn:
        tx = conn.begin()
        normal_role(conn)
        with pytest.raises(DBAPIError) as denied:
            clone(conn, saved.id, uuid4(), "hash")
        assert getattr(denied.value.orig, "sqlstate", None) == "P16G1"
        tx.rollback()


def test_empty_roundtrip_and_populated_downgrade_refusal(reconsideration_env):
    service, command, actor, approval = reconsideration_env
    env = approval[-1]
    migration.downgrade(config(env), "0055_b09_approval_tuples")
    migration.upgrade(config(env), "0075_m1_reconsideration")
    saved = service.record_rejection_reconsideration(command, actor)
    with pytest.raises(DBAPIError):
        migration.downgrade(config(env), "0055_b09_approval_tuples")
    assert service.get_rejection_reconsideration(command.project_id, saved.id, actor) == saved
    with env[-1][8].connect() as conn:
        assert conn.execute(text("SHOW server_version_num")).scalar_one().startswith("18")
        constraints = conn.execute(
            text("""SELECT conname,confdeltype FROM pg_constraint
          WHERE contype='f' AND conrelid IN ('decision_basis_approval_decisions'::regclass,
          'decision_basis_revision_actions'::regclass)""")
        ).all()
        assert len(constraints) == 4 and {row[1] for row in constraints} == {"r"}
        triggers = conn.execute(
            text("""SELECT tgname,tgdeferrable,tginitdeferred FROM pg_trigger
           WHERE tgname IN ('b10_complete_decision','b10_complete_rejections',
           'b10_complete_revisions','b10_no_basis_cycle')""")
        ).all()
        assert len(triggers) == 11 and all(row[1] and row[2] for row in triggers)


@pytest.mark.parametrize("graph", ["self", "transitive", "10001", "10000"])
def test_deferred_graph_cycles_and_distinct_node_bound(reconsideration_env, graph):
    """Fault-inject only traversal edges in a rolled-back disposable transaction.

    Decision/evidence rows are real service-created history. The synthetic graph
    isolates cycle/bound enforcement, including future Decision-bearing edges;
    it is never retained as scientific acceptance history.
    """
    service, command, actor, approval = reconsideration_env
    saved = service.record_rejection_reconsideration(command, actor)
    candidate = uuid4()
    engine = approval[-1][-1][8]
    with engine.connect() as conn:
        tx = conn.begin()
        conn.execute(text(B09_SHARE_SQL))
        conn.execute(
            text("""CREATE TABLE b10_test_edges(kind text,id uuid,child_kind text,child_id uuid);
          CREATE INDEX b10_test_edges_parent ON b10_test_edges(kind,id)""")
        )
        if graph in {"self", "transitive"}:
            conn.execute(
                text("""INSERT INTO b10_test_edges VALUES
              ('DecisionRecord',:root,'DecisionRecord',:child)"""),
                {"root": candidate, "child": candidate if graph == "self" else saved.id},
            )
            if graph == "transitive":
                conn.execute(
                    text("""INSERT INTO b10_test_edges VALUES
                  ('DecisionRecord',:child,'DecisionRecord',:root)"""),
                    {"root": candidate, "child": saved.id},
                )
        else:
            conn.execute(
                text("""INSERT INTO b10_test_edges
             SELECT 'DecisionRecord',CASE WHEN i=0 THEN :root ELSE md5(i::text)::uuid END,
              'DecisionRecord',md5((i+1)::text)::uuid
              FROM generate_series(0,:last) AS series(i)"""),
                {"root": candidate, "last": int(graph) - 2},
            )
        conn.execute(
            text("""CREATE OR REPLACE VIEW b10_edges AS
          SELECT kind,id,child_kind,child_id FROM b10_test_edges""")
        )
        normal_role(conn)
        if graph == "10000":
            clone(conn, saved.id, candidate, "valid")
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        else:
            with pytest.raises(DBAPIError) as denied:
                clone(conn, saved.id, candidate, "valid")
                conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            assert getattr(denied.value.orig, "sqlstate", None) == "P10B1"
        tx.rollback()


revised_env = fixtures.revised_env


def test_normal_sql_cannot_launder_a_forged_revision_predecessor(revised_env):
    from dataclasses import replace

    from researchbase.domain.decision import (
        DecisionBasisReference,
        decision_basis_material,
        decision_content_material,
    )
    from researchbase.domain.revision_action import RevisionReference, revision_action_material
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from researchbase.foundation.hashing import sha256_canonical_json

    service, command, actor, approval = revised_env
    saved = service.record_rejection_reconsideration(command, actor)
    engine = approval[-1][-1][8]
    with engine.connect() as conn:
        source = dict(
            conn.execute(
                text("SELECT * FROM revision_actions WHERE id=:id"),
                {"id": command.revision_action_ids[0]},
            )
            .mappings()
            .one()
        )
    predecessor = {**source, "id": uuid4(), "content_hash": "0" * 64}
    results = (
        None,
        None,
        None,
        None,
        RevisionReference(
            "ScientificConclusionVersion",
            saved.scientific_conclusion_version_id,
            saved.target_content_hash,
        ),
        None,
        None,
    )
    child = {**source, "id": uuid4(), "supersedes_revision_action_id": predecessor["id"]}
    child["content_hash"] = str(
        sha256_canonical_json(
            revision_action_material(
                RevisionReference("ReviewIssue", source["review_issue_id"]),
                None,
                "CONCLUSION_CHANGE",
                results,
                RevisionReference("RevisionAction", predecessor["id"], predecessor["content_hash"]),
                RevisionReference("ActorIdentity", source["created_by"]),
            )
        )
    )

    def insert(conn, table, row):
        keys = tuple(row)
        conn.execute(
            text(
                f"INSERT INTO {table} ({','.join(keys)}) VALUES ("
                + ",".join(f":{key}" for key in keys)
                + ")"
            ),
            row,
        )

    # B07 now rejects this forgery at admission, before B10 traverses it.
    with pytest.raises(DBAPIError) as admission_denied, engine.begin() as conn:
        normal_role(conn)
        insert(conn, "revision_actions", predecessor)
    assert getattr(admission_denied.value.orig, "sqlstate", None) == "P17F2"
    # Retain B10's historical-corruption regression using a privileged negative
    # fixture in this disposable database. Ordinary writers cannot create it.
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE revision_actions DISABLE TRIGGER USER"))
        insert(conn, "revision_actions", predecessor)
        insert(conn, "revision_actions", child)
        conn.execute(text("ALTER TABLE revision_actions ENABLE TRIGGER USER"))
    with pytest.raises(ResearchBaseError) as application_denied:
        service.record_rejection_reconsideration(
            replace(command, id=uuid4(), revision_action_ids=(child["id"],)), actor
        )
    assert application_denied.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    with engine.connect() as conn:
        parent = dict(
            conn.execute(text("SELECT * FROM decision_records WHERE id=:id"), {"id": saved.id})
            .mappings()
            .one()
        )
    material = [
        (
            r.type,
            child["id"] if r.type == "RevisionAction" else r.id,
            child["content_hash"] if r.type == "RevisionAction" else r.content_hash,
        )
        for r in saved.basis
    ]
    basis = tuple(
        DecisionBasisReference(kind, identity, digest, ordinal)
        for ordinal, (kind, identity, digest) in enumerate(
            sorted(material, key=lambda r: (r[0], str(r[1]), r[2]))
        )
    )
    parent["id"] = uuid4()
    parent["basis_set_hash"] = str(sha256_canonical_json(decision_basis_material(basis)))
    parent["content_hash"] = str(
        sha256_canonical_json(
            decision_content_material(
                parent["project_id"],
                parent["decision_type"],
                parent["question"],
                parent["decision"],
                parent["rationale"],
                parent["decided_by"],
                parent["basis_set_hash"],
            )
        )
    )
    with engine.connect() as conn:
        tx = conn.begin()
        conn.execute(text(B09_SHARE_SQL))
        normal_role(conn)
        with pytest.raises(DBAPIError) as sql_denied:
            insert(conn, "decision_records", parent)
            for ref in basis:
                table, key = {
                    "ApprovalDecision": (
                        "decision_basis_approval_decisions",
                        "approval_decision_id",
                    ),
                    "InternalReviewRecord": ("decision_basis_reviews", "internal_review_record_id"),
                    "RevisionAction": ("decision_basis_revision_actions", "revision_action_id"),
                    "ScientificConclusionVersion": (
                        "decision_basis_conclusions",
                        "scientific_conclusion_version_id",
                    ),
                }[ref.type]
                insert(
                    conn, table, {"decision_id": parent["id"], key: ref.id, "ordinal": ref.ordinal}
                )
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        assert getattr(sql_denied.value.orig, "sqlstate", None) == "P17F2"
        tx.rollback()
