"""Independent deferred DB guards, same-transaction seals and downgrade history."""

from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from researchbase.persistence.novelty_repository import N
from tests.integration.phase2.b20_screening_support import record, request
from tests.integration.phase2.test_b22_prior_art_schema import config

pytest_plugins = ("tests.integration.phase2.pr2_18_fixtures",)


@pytest.mark.parametrize(
    "value",
    [
        "ARRAY[]::int[]",
        "ARRAY[NULL]::int[]",
        "ARRAY[0,0]",
        "ARRAY[1,0]",
        "ARRAY[-1]",
        "ARRAY[100]",
        "ARRAY[[0,1]]",
        "'[0:0]={0}'::int[]",
    ],
)
def test_sql_ordinals(novelty_env, value):
    with novelty_env["engine"].connect() as conn:
        assert conn.execute(text("SELECT b20_valid_ordinals(" + value + ")")).scalar_one() is False


def test_empty_downgrade_restores_check_trigger_and_functions(phase2_database_url):
    cfg = config(phase2_database_url)
    command.upgrade(cfg, "0068_b21_unresolved_capture")
    engine = create_engine(phase2_database_url)

    def catalog():
        with engine.connect() as conn:
            return (
                conn.execute(
                    text(
                        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                        "WHERE conname='ck_b19_novelty_material'"
                    )
                ).scalar_one(),
                conn.execute(
                    text(
                        "SELECT pg_get_triggerdef(oid) FROM pg_trigger "
                        "WHERE tgname='trg_b19_novelty_complete'"
                    )
                ).scalar_one(),
                conn.execute(
                    text(
                        "SELECT proname,pg_get_functiondef(oid) FROM pg_proc "
                        "WHERE proname LIKE 'pr218_%' OR proname LIKE 'b19_%' "
                        "OR proname LIKE 'b21_%' OR proname LIKE 'b22_%' ORDER BY proname"
                    )
                ).all(),
            )

    before = catalog()
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0068_b21_unresolved_capture")
    assert catalog() == before
    engine.dispose()


def test_populated_downgrade_refuses(novelty_env):
    e = novelty_env
    c = request(e)
    saved = record(e, c)
    with pytest.raises(DBAPIError, match="history prevents downgrade"):
        command.downgrade(
            config(e["engine"].url.render_as_string(hide_password=False)),
            "0068_b21_unresolved_capture",
        )
    assert record(e, c).content_hash == saved.content_hash


@pytest.mark.parametrize("operation", ["UPDATE", "DELETE", "LATE"])
def test_normal_role_sealed_children(novelty_env, novelty_sql_role, operation):
    e = novelty_env
    c = request(e)
    record(e, c)
    with pytest.raises(DBAPIError) as error, e["engine"].begin() as conn:
        conn.execute(text('SET LOCAL ROLE "' + novelty_sql_role + '"'))
        if operation == "LATE":
            conn.execute(text("LOCK TABLE " + ",".join(N) + " IN SHARE MODE"))
            conn.execute(
                text(
                    """INSERT INTO novelty_assessment_probes
                        SELECT :id,novelty_assessment_id,search_execution_id,query_index,
                          disposition,rationale,created_by,created_at
                        FROM novelty_assessment_probes LIMIT 1"""
                ),
                {"id": uuid4()},
            )
        elif operation == "UPDATE":
            conn.execute(text("UPDATE novelty_assessment_probes SET rationale='Changed'"))
        else:
            conn.execute(text("DELETE FROM novelty_assessment_screening_results"))
    assert getattr(error.value.orig, "sqlstate", None) == "P17D1"


@pytest.mark.parametrize("prelocks", [False, True])
def test_parent_cannot_omit_children(novelty_env, novelty_sql_role, prelocks):
    e = novelty_env
    c = request(e)
    with pytest.raises(DBAPIError) as error, e["engine"].begin() as conn:
        conn.execute(text('SET LOCAL ROLE "' + novelty_sql_role + '"'))
        if prelocks:
            conn.execute(text("LOCK TABLE " + ",".join(N) + " IN SHARE MODE"))
        conn.execute(
            text("""INSERT INTO novelty_assessments
            (id,created_at,created_by,claim_version_id,search_coverage_id,assessment,limitations,assessed_by,content_hash,hash_scheme,material_version,scope_statement,closeness_criteria,screening_captured)
            VALUES (:id,clock_timestamp(),:actor,:claim,:coverage,
                'INCONCLUSIVE','SQL screening',:actor,:digest,'sha256-cjson-v1',2,
                'All visible',ARRAY['Method'],true)"""),
            dict(
                id=uuid4(),
                actor=e["author"].actor_id,
                claim=e["claim"],
                coverage=c.search_coverage_id,
                digest="a" * 64,
            ),
        )
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert getattr(error.value.orig, "sqlstate", None) == "P17D3"


def raw_screening(conn, e, c, *, change=None):
    """Bypass Application deliberately to exercise independent deferred guards."""
    from dataclasses import fields

    values = dict(
        id=c.id,
        created_by=e["author"].actor_id,
        claim_version_id=c.claim_version_id,
        search_coverage_id=c.search_coverage_id,
        assessment=c.assessment.value,
        limitations=c.limitations,
        assessed_by=e["author"].actor_id,
        content_hash="a" * 64,
        hash_scheme="sha256-cjson-v1",
        material_version=2,
        scope_statement=c.scope_statement,
        closeness_criteria=list(c.closeness_criteria.statements),
        screening_captured=True,
    )
    columns = list(values)
    conn.execute(
        text(
            "INSERT INTO novelty_assessments ("
            + ",".join(columns)
            + ",created_at) VALUES ("
            + ",".join(":" + x for x in columns)
            + ",clock_timestamp())"
        ),
        values,
    )
    at = conn.execute(
        text("SELECT created_at FROM novelty_assessments WHERE id=:id"), {"id": c.id}
    ).scalar_one()
    for table, rows in (
        ("novelty_assessment_probes", c.screening_basis.probes),
        ("novelty_assessment_screening_results", c.screening_basis.results),
    ):
        if change == "omit_screen" and table.endswith("results"):
            continue
        for item in rows:
            child = {f.name: getattr(item, f.name) for f in fields(item)}
            child.update(
                id=uuid4(),
                novelty_assessment_id=c.id,
                created_by=e["author"].actor_id,
                created_at=at,
            )
            child["disposition"] = item.disposition.value
            if "criteria_ordinals" in child:
                child["criteria_ordinals"] = (
                    [1] if change == "criterion" else list(item.criteria_ordinals)
                )
                if change == "foreign_result":
                    child["search_result_record_id"] = conn.execute(
                        text(
                            "SELECT r.id FROM search_result_records r JOIN search_query_records q "
                            "ON q.id=r.search_query_record_id JOIN literature_search_executions e "
                            "ON e.id=q.literature_search_execution_id "
                            "WHERE e.search_plan_version_id<>:plan LIMIT 1"
                        ),
                        {"plan": e["plan"]},
                    ).scalar_one()
                if change == "witness":
                    child["search_result_resolution_id"] = uuid4()
                if change == "disposition":
                    child["disposition"] = "EXCLUDED"
            elif change == "probe":
                child["query_index"] = 1
            elif change == "probe_disposition":
                child["disposition"] = "INCOMPLETE"
            if change == "execution" and table.endswith("probes"):
                child["search_execution_id"] = conn.execute(
                    text(
                        "SELECT id FROM literature_search_executions "
                        "WHERE search_plan_version_id<>:plan LIMIT 1"
                    ),
                    {"plan": e["plan"]},
                ).scalar_one()
            if change == "actor":
                child["created_by"] = e["reviewer"].actor_id
            if change == "time":
                child["created_at"] = at.replace(year=at.year - 1)
            keys = list(child)
            conn.execute(
                text(
                    "INSERT INTO "
                    + table
                    + " ("
                    + ",".join(keys)
                    + ") VALUES ("
                    + ",".join(":" + x for x in keys)
                    + ")"
                ),
                child,
            )
    conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


@pytest.mark.parametrize(
    "change",
    [
        "omit_screen",
        "criterion",
        "witness",
        "disposition",
        "probe",
        "actor",
        "time",
        "isolation",
        "execution",
        "foreign_result",
        "probe_disposition",
    ],
)
def test_normal_role_cannot_forge_complete_negative(novelty_env, novelty_sql_role, change):
    from tests.integration.phase2.b20_screening_support import compared

    e, c, _, _ = compared(novelty_env)
    with pytest.raises(DBAPIError) as error, e["engine"].begin() as conn:
        if change == "isolation":
            conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        conn.execute(text('SET LOCAL ROLE "' + novelty_sql_role + '"'))
        conn.execute(text("LOCK TABLE " + ",".join(N) + " IN SHARE MODE"))
        raw_screening(conn, e, c, change=change)
    expected_state = {
        "witness": "23503",
        "criterion": "P17D2",
        "disposition": "P17D2",
    }.get(change, "P17D3")
    assert getattr(error.value.orig, "sqlstate", None) == expected_state
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM novelty_assessments")).scalar_one() == 0


def test_normal_role_captured_ambiguity_cannot_claim_not_close(novelty_env, novelty_sql_role):
    from dataclasses import replace

    from researchbase.domain.novelty import NoveltyOutcome
    from tests.integration.phase2.b20_screening_support import compared

    e, c, _, _ = compared(novelty_env, ambiguous_capture=True)
    c = replace(c, assessment=NoveltyOutcome.INCONCLUSIVE)
    with pytest.raises(DBAPIError) as error, e["engine"].begin() as conn:
        conn.execute(text('SET LOCAL ROLE "' + novelty_sql_role + '"'))
        conn.execute(text("LOCK TABLE " + ",".join(N) + " IN SHARE MODE"))
        raw_screening(conn, e, c)
    assert getattr(error.value.orig, "sqlstate", None) == "P17D3"


def test_catalog_types_constraints_and_indexes(novelty_env):
    expected_columns = {
        "id": "uuid",
        "novelty_assessment_id": "uuid",
        "disposition": "character varying(16)",
        "rationale": "text",
        "created_by": "uuid",
        "created_at": "timestamp with time zone",
    }
    with novelty_env["engine"].connect() as conn:
        for table, prefix, additional, nullable, targets in (
            (
                "novelty_assessment_probes",
                "b20_probe",
                {"search_execution_id": "uuid", "query_index": "integer"},
                set(),
                {
                    "assessment": "novelty_assessments",
                    "execution": "literature_search_executions",
                    "actor": "actors",
                },
            ),
            (
                "novelty_assessment_screening_results",
                "b20_screen",
                {
                    "search_result_record_id": "uuid",
                    "criteria_ordinals": "integer[]",
                    "prior_art_relation_id": "uuid",
                    "search_result_resolution_id": "uuid",
                },
                {"prior_art_relation_id", "search_result_resolution_id"},
                {
                    "assessment": "novelty_assessments",
                    "result": "search_result_records",
                    "relation": "prior_art_relations",
                    "resolution": "search_result_resolutions",
                    "actor": "actors",
                },
            ),
        ):
            rows = conn.execute(
                text("""SELECT attname,format_type(atttypid,atttypmod),attnotnull
                FROM pg_attribute WHERE attrelid=to_regclass(:table)
                AND attnum>0 AND NOT attisdropped"""),
                {"table": table},
            ).all()
            assert {r[0]: r[1] for r in rows} == expected_columns | additional
            assert {r[0] for r in rows if not r[2]} == nullable
            constraints = conn.execute(
                text("""SELECT conname,contype,confrelid::regclass::text,confdeltype
                FROM pg_constraint WHERE conrelid=to_regclass(:table)"""),
                {"table": table},
            ).all()
            assert {r[0]: (r[2], r[3]) for r in constraints if r[1] == "f"} == {
                f"fk_{prefix}_{name}": (target, "r") for name, target in targets.items()
            }
            checks = {r[0] for r in constraints if r[1] == "c"}
            assert checks == {
                f"ck_{prefix}_{name}"
                for name in (
                    ("index", "disposition", "text")
                    if prefix == "b20_probe"
                    else ("disposition", "refs", "ordinals", "text")
                )
            }
            indexes = set(
                conn.execute(
                    text("SELECT indexname FROM pg_indexes WHERE tablename=:table"),
                    {"table": table},
                ).scalars()
            )
            assert indexes == {
                f"pk_{prefix}",
                "uq_b20_probe_key" if prefix == "b20_probe" else "uq_b20_screen_result",
                *(f"ix_{prefix}_{name}" for name in targets if name != "assessment"),
            }


def test_populated_old_shape_upgrade_preserves_hash(novelty_env):
    from researchbase.application.novelty import ExactReadQuery, RecordNoveltyAssessmentCommand
    from researchbase.domain.novelty import NoveltyOutcome

    e = novelty_env
    screening = request(e)
    saved = record(
        e,
        RecordNoveltyAssessmentCommand(
            uuid4(),
            e["project"],
            e["claim"],
            screening.search_coverage_id,
            NoveltyOutcome.INCONCLUSIVE,
            "Historical v1",
        ),
    )
    cfg = config(e["engine"].url.render_as_string(hide_password=False))
    command.downgrade(cfg, "0068_b21_unresolved_capture")
    with e["engine"].connect() as conn:
        before = conn.execute(
            text("SELECT content_hash FROM novelty_assessments WHERE id=:id"), {"id": saved.id}
        ).scalar_one()
    command.upgrade(cfg, "head")
    read = e["service"].read_novelty_assessment(e["author"], ExactReadQuery(e["project"], saved.id))
    assert read.content_hash == before == saved.content_hash
    assert read.material_version == 1 and read.screening_basis is None


def test_preflight_rejects_changed_sibling_definition(novelty_env):
    e = novelty_env
    cfg = config(e["engine"].url.render_as_string(hide_password=False))
    command.downgrade(cfg, "0068_b21_unresolved_capture")
    with e["engine"].begin() as conn:
        conn.execute(text("ALTER FUNCTION b19_complete_basis() SECURITY DEFINER"))
    with pytest.raises(RuntimeError, match="sibling function definitions"):
        command.upgrade(cfg, "head")
    with e["engine"].begin() as conn:
        assert (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0068_b21_unresolved_capture"
        )
        conn.execute(text("ALTER FUNCTION b19_complete_basis() SECURITY INVOKER"))
    command.upgrade(cfg, "head")


def test_normal_role_correctly_retained_incomplete_negative_is_invalid_state(
    novelty_env, novelty_sql_role
):
    from dataclasses import replace

    from researchbase.domain.novelty import NoveltyOutcome

    e = novelty_env
    c = replace(request(e), assessment=NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE)
    with pytest.raises(DBAPIError) as error, e["engine"].begin() as conn:
        conn.execute(text('SET LOCAL ROLE "' + novelty_sql_role + '"'))
        conn.execute(text("LOCK TABLE " + ",".join(N) + " IN SHARE MODE"))
        raw_screening(conn, e, c)
    assert getattr(error.value.orig, "sqlstate", None) == "P17D2"
