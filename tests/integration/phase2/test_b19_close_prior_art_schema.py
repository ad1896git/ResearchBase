"""Normal-role B19 seals, typed criteria, populated upgrade and downgrade refusal."""

from dataclasses import replace
from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from researchbase.domain.novelty import NoveltyOutcome, PriorArtKind
from researchbase.persistence.novelty_repository import N
from tests.integration.phase2.b19_basis_support import legacy_coverage, record, setup
from tests.integration.phase2.test_b22_prior_art_schema import config

PARENT = "0065_b22_prior_art_correction"


def test_empty_downgrade_restores_exact_parent_catalog(phase2_database_url):
    cfg = config(phase2_database_url)
    command.upgrade(cfg, PARENT)
    engine = create_engine(phase2_database_url)

    def catalog():
        queries = (
            "SELECT c.relname,c.relkind FROM pg_class c JOIN pg_namespace n "
            "ON n.oid=c.relnamespace WHERE n.nspname='public' ORDER BY 1,2",
            "SELECT c.relname,a.attname,format_type(a.atttypid,a.atttypmod),"
            "a.attnotnull,pg_get_expr(d.adbin,d.adrelid) FROM pg_attribute a "
            "JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace "
            "LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum "
            "WHERE n.nspname='public' AND a.attnum>0 AND NOT a.attisdropped ORDER BY 1,2",
            "SELECT c.relname,k.conname,pg_get_constraintdef(k.oid) FROM pg_constraint k "
            "JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' ORDER BY 1,2",
            "SELECT c.relname,t.tgname,pg_get_triggerdef(t.oid) FROM pg_trigger t "
            "JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND NOT t.tgisinternal ORDER BY 1,2",
            "SELECT p.oid::regprocedure::text,pg_get_functiondef(p.oid) FROM pg_proc p "
            "JOIN pg_namespace n ON n.oid=p.pronamespace "
            "WHERE n.nspname='public' ORDER BY 1",
            "SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY 1",
        )
        with engine.connect() as conn:
            return tuple(tuple(conn.execute(text(query)).all()) for query in queries)

    before = catalog()
    command.upgrade(cfg, "0075_m1_reconsideration")
    command.downgrade(cfg, PARENT)
    try:
        assert catalog() == before
        with engine.connect() as conn:
            assert (
                conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == PARENT
            )
            assert (
                conn.execute(
                    text(
                        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                        "WHERE conrelid='novelty_assessments'::regclass "
                        "AND conname='ck_pr218_novelty_initial_slice'"
                    )
                ).scalar_one()
                == "CHECK (((assessment)::text = 'INCONCLUSIVE'::text))"
            )
    finally:
        engine.dispose()


def prelock(conn, role):
    conn.execute(text('SET LOCAL ROLE "' + role + '"'))
    conn.execute(text("LOCK TABLE " + ",".join(N) + " IN SHARE MODE"))


def insert_parent(conn, e, c, identity=None):
    identity = identity or uuid4()
    conn.execute(
        text("""INSERT INTO novelty_assessments
      (id,created_at,created_by,claim_version_id,search_coverage_id,assessment,limitations,
       assessed_by,content_hash,hash_scheme,material_version,scope_statement,closeness_criteria)
      VALUES (:id,clock_timestamp(),:actor,:claim,:cov,'CLOSE_PRIOR_ART_FOUND','SQL basis',
        :actor,:hash,'sha256-cjson-v1',2,'Selected scope',ARRAY['Same method'])"""),
        dict(
            id=identity,
            actor=e["author"].actor_id,
            claim=c.claim_version_id,
            cov=c.search_coverage_id,
            hash="a" * 64,
        ),
    )
    return identity


def insert_basis(conn, e, parent, pair):
    conn.execute(
        text("""INSERT INTO novelty_assessment_prior_art_inputs
      (id,created_at,created_by,novelty_assessment_id,prior_art_relation_id,search_result_resolution_id)
      VALUES (:id,clock_timestamp(),:actor,:parent,:relation,:witness)"""),
        dict(
            id=uuid4(),
            actor=e["author"].actor_id,
            parent=parent,
            relation=pair.prior_art_relation_id,
            witness=pair.search_result_resolution_id,
        ),
    )


@pytest.mark.parametrize(
    "criteria",
    [
        "ARRAY[]::text[]",
        "ARRAY[NULL]::text[]",
        "ARRAY[' '::text]",
        "ARRAY[E'\\t\\n']",
        "ARRAY[U&'\\2003']",
        "ARRAY[U&'e\\0301']",
        "ARRAY[['x','y']]",
        "'[0:0]={x}'::text[]",
        "array_fill('x'::text,ARRAY[101])",
        "ARRAY[repeat('x',8193),repeat('y',8192)]",
    ],
)
def test_sql_criteria_shapes(novelty_env, criteria):
    with novelty_env["engine"].connect() as conn:
        assert (
            conn.execute(text("SELECT b19_valid_criteria(" + criteria + ")")).scalar_one() is False
        )


def test_populated_v1_upgrade_preserves_hash_and_v2_refuses_downgrade(
    novelty_env, phase2_database_url
):
    e = novelty_env
    cfg = config(phase2_database_url)
    command.downgrade(cfg, "0067_b17_prepared_package_freeze")
    coverage = legacy_coverage(e)
    command.upgrade(cfg, "0075_m1_reconsideration")
    c, _, _, _ = setup(e, coverage=coverage)
    v1 = record(
        e,
        replace(
            c,
            assessment=NoveltyOutcome.INCONCLUSIVE,
            prior_art_basis=(),
            scope_statement=None,
            closeness_criteria=None,
        ),
    )
    cfg = config(phase2_database_url)
    command.downgrade(cfg, PARENT)
    command.upgrade(cfg, "0075_m1_reconsideration")
    assert (
        record(
            e,
            replace(
                c,
                assessment=NoveltyOutcome.INCONCLUSIVE,
                prior_art_basis=(),
                scope_statement=None,
                closeness_criteria=None,
            ),
        ).content_hash
        == v1.content_hash
    )
    v2 = record(e, replace(c, id=uuid4()))
    with pytest.raises(DBAPIError, match="B19 basis history prevents downgrade"):
        command.downgrade(cfg, PARENT)
    assert record(e, replace(c, id=v2.id)).content_hash == v2.content_hash
    with e["engine"].connect() as conn:
        assert conn.execute(text("SHOW server_version_num")).scalar_one().startswith("18")
        assert (
            conn.execute(
                text(
                    "SELECT data_type FROM information_schema.columns "
                    "WHERE table_name='novelty_assessments' AND column_name='closeness_criteria'"
                )
            ).scalar_one()
            == "ARRAY"
        )
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM pg_constraint "
                    "WHERE conrelid='novelty_assessment_prior_art_inputs'::regclass "
                    "AND contype='f' AND confdeltype='r'"
                )
            ).scalar_one()
            == 4
        )


@pytest.mark.parametrize(
    "case,state",
    [
        ("no_prelock", "P17D3"),
        ("missing", "P17D2"),
        ("nonclose", "P17D2"),
        ("ambiguous", "P17D3"),
        ("wrong_coverage", "P17D3"),
        ("superseded", "P17D2"),
        ("unverified", "P17D3"),
    ],
)
@pytest.mark.parametrize("force", [False, True])
def test_normal_role_structural_admission(novelty_env, novelty_sql_role, case, state, force):
    from researchbase.application.novelty import RecordSearchCoverageCommand
    from tests.integration.phase2.pr2_18_fixtures import add_resolution

    e = novelty_env
    c, rc, relation, _ = setup(
        e, kind=PriorArtKind.RELATED if case == "nonclose" else PriorArtKind.IDENTICAL
    )
    if case == "superseded":
        e["service"].record_prior_art_relation(
            e["author"], replace(rc, id=uuid4(), supersedes_prior_art_relation_id=relation.id)
        )
    if case == "ambiguous":
        add_resolution(e, e["results"][0], version=False)
    if case == "wrong_coverage":
        cov = e["service"].record_search_coverage(
            e["author"],
            RecordSearchCoverageCommand(
                uuid4(), e["project"], e["plan"], (e["executions"][1],), "Other"
            ),
        )
        c = replace(c, search_coverage_id=cov.id)
    if case == "unverified":
        e["literature"].review(
            e["reviewer"], e["project"], e["evidence"], "DISPUTED", "New dispute", uuid4()
        )
    with pytest.raises(DBAPIError) as error:
        with e["engine"].begin() as conn:
            if case == "no_prelock":
                conn.execute(text('SET LOCAL ROLE "' + novelty_sql_role + '"'))
            else:
                prelock(conn, novelty_sql_role)
            parent = insert_parent(conn, e, c)
            if case != "missing":
                insert_basis(conn, e, parent, c.prior_art_basis[0])
            if force:
                conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert getattr(error.value.orig, "sqlstate", None) == state
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM novelty_assessments")).scalar_one() == 0
        assert (
            conn.execute(
                text("SELECT count(*) FROM novelty_assessment_prior_art_inputs")
            ).scalar_one()
            == 0
        )


def test_normal_role_seal_mutation_and_fabricated_hash(novelty_env, novelty_sql_role):
    from researchbase.application.novelty import ExactReadQuery
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    e = novelty_env
    c, _, _, _ = setup(e)
    with e["engine"].begin() as conn:
        prelock(conn, novelty_sql_role)
        parent = insert_parent(conn, e, c)
        insert_basis(conn, e, parent, c.prior_art_basis[0])
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    with pytest.raises(ResearchBaseError) as error:
        e["service"].read_novelty_assessment(e["author"], ExactReadQuery(e["project"], parent))
    assert error.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    for table, where in [
        ("novelty_assessments", "id"),
        ("novelty_assessment_prior_art_inputs", "novelty_assessment_id"),
    ]:
        for operation in (
            "UPDATE " + table + " SET created_at=clock_timestamp()",
            "DELETE FROM " + table,
        ):
            with pytest.raises(DBAPIError) as error:
                with e["engine"].begin() as conn:
                    prelock(conn, novelty_sql_role)
                    conn.execute(text(operation + " WHERE " + where + "=:id"), dict(id=parent))
            assert getattr(error.value.orig, "sqlstate", None) == "P17D1"
    with pytest.raises(DBAPIError) as error:
        with e["engine"].begin() as conn:
            prelock(conn, novelty_sql_role)
            insert_basis(conn, e, parent, c.prior_art_basis[0])
    assert getattr(error.value.orig, "sqlstate", None) == "P17D1"


def test_oversized_basis_rolls_back_at_deferred_completion(novelty_env, novelty_sql_role):
    from researchbase.domain.novelty import PriorArtBasisInput
    from tests.integration.phase2.test_b22_prior_art_schema import insert as insert_relation

    e = novelty_env
    c, _, _, witness = setup(e)
    with pytest.raises(DBAPIError) as error:
        with e["engine"].begin() as conn:
            prelock(conn, novelty_sql_role)
            parent = insert_parent(conn, e, c)
            insert_basis(conn, e, parent, c.prior_art_basis[0])
            for _ in range(100):
                identity = insert_relation(conn, e)
                insert_basis(conn, e, parent, PriorArtBasisInput(identity, witness["id"]))
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert getattr(error.value.orig, "sqlstate", None) == "P17D2"
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM novelty_assessments")).scalar_one() == 0


@pytest.mark.parametrize("epoch", [0, 1, 7])
def test_b19_seal_is_epoch_safe(novelty_env, epoch):
    e = novelty_env
    c, _, _, _ = setup(e)
    # The executed guard uses xid; these synthetic high epochs exercise that exact comparison.
    with e["engine"].begin() as conn:
        conn.execute(text("LOCK TABLE " + ",".join(N) + " IN SHARE MODE"))
        parent = insert_parent(conn, e, c)
        low = conn.execute(text("SELECT pg_current_xact_id()::xid::text::bigint")).scalar_one()
        full = str((epoch << 32) + low)
        assert conn.execute(
            text(
                "SELECT xmin=CAST(:full AS text)::xid8::xid FROM novelty_assessments WHERE id=:id"
            ),
            dict(full=full, id=parent),
        ).scalar_one()
        insert_basis(conn, e, parent, c.prior_art_basis[0])
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        definition = conn.execute(
            text("SELECT pg_get_functiondef('b19_basis_insert_guard()'::regprocedure)")
        ).scalar_one()
        assert "parent_xid xid" in definition and "pg_current_xact_id()::xid" in definition


@pytest.mark.parametrize("case", ["source_only", "wrong_source", "wrong_claim", "wrong_project"])
def test_normal_role_exact_join_mismatches(novelty_env, novelty_sql_role, case):
    from researchbase.application.commands import FreezeClaimVersionCommand, LinkEvidenceCommand
    from researchbase.domain.novelty import PriorArtBasisInput
    from researchbase.domain.organization import ProjectId
    from tests.integration.phase2.pr2_18_fixtures import add_resolution
    from tests.integration.phase2.test_b22_prior_art_schema import second_source
    from tests.integration.test_pr12_application import seed_claim, seed_measurement

    e = novelty_env
    c, _, _, _ = setup(e)
    pair = c.prior_art_basis[0]
    if case == "source_only":
        witness = add_resolution(e, e["results"][0], version=False)
        pair = PriorArtBasisInput(pair.prior_art_relation_id, witness["id"])
    elif case == "wrong_source":
        witness = add_resolution(e | {"source": second_source(e)}, e["results"][0])
        pair = PriorArtBasisInput(pair.prior_art_relation_id, witness["id"])
    else:
        project = e["other_project"] if case == "wrong_project" else e["project"]
        app, context = e["application"], e["context"]
        measurement = seed_measurement(app, ProjectId(project), context, "b19-other")
        claim, draft = seed_claim(app, ProjectId(project), context)
        app.link_evidence(
            LinkEvidenceCommand(
                claim.id, draft.id, measurement, None, "supports", None, draft.row_version, context
            )
        )
        linked = app.get_current_claim_version(claim.id)
        frozen = app.freeze_claim_version(
            FreezeClaimVersionCommand(claim.id, linked.id, context, linked.row_version)
        )
        c = replace(c, claim_version_id=UUID(str(frozen.id)))
    with pytest.raises(DBAPIError) as error:
        with e["engine"].begin() as conn:
            prelock(conn, novelty_sql_role)
            parent = insert_parent(conn, e, c)
            insert_basis(conn, e, parent, pair)
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert getattr(error.value.orig, "sqlstate", None) == "P17D3"


def test_preflight_refuses_broken_v1_capture_closure(novelty_env, phase2_database_url):
    e = novelty_env
    cfg = config(phase2_database_url)
    command.downgrade(cfg, "0067_b17_prepared_package_freeze")
    coverage = legacy_coverage(e)
    command.upgrade(cfg, "0075_m1_reconsideration")
    c, _, _, _ = setup(e, coverage=coverage)
    record(
        e,
        replace(
            c,
            assessment=NoveltyOutcome.INCONCLUSIVE,
            prior_art_basis=(),
            scope_statement=None,
            closeness_criteria=None,
        ),
    )
    cfg = config(phase2_database_url)
    command.downgrade(cfg, PARENT)
    # Controlled administrator corruption only; normal-role immutable guards stay covered above.
    with e["engine"].begin() as conn:
        conn.execute(text("ALTER TABLE search_coverage_executions DISABLE TRIGGER USER"))
        conn.execute(
            text("DELETE FROM search_coverage_executions WHERE search_coverage_id=:id"),
            {"id": c.search_coverage_id},
        )
        conn.execute(text("ALTER TABLE search_coverage_executions ENABLE TRIGGER USER"))
    with pytest.raises(DBAPIError, match="unresolved existing immutable assessment closure"):
        command.upgrade(cfg, "0075_m1_reconsideration")
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == PARENT
