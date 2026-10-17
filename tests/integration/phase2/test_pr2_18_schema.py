"""PostgreSQL catalog, sealing, SQL guards and data-preserving migration."""

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from researchbase.application.novelty import RecordSearchCoverageCommand

pytest_plugins = ("tests.integration.phase2.pr2_18_fixtures",)


@pytest.mark.parametrize("value", [{}, ["x", "x"], ["z", "a"], [""], [1], ["e\u0301"]])
def test_provider_helper_rejects(novelty_env, value):
    import json

    with novelty_env["engine"].connect() as conn:
        assert (
            conn.execute(
                text("SELECT pr218_valid_providers(CAST(:v AS jsonb))"), {"v": json.dumps(value)}
            ).scalar_one()
            is False
        )


@pytest.mark.parametrize(
    "value",
    [
        {"from": None, "through": None},
        {"from": "2025-02-29", "through": None},
        {"from": "2024-02-29", "through": "2024-02-28"},
        {"from": "2024-02-29", "through": None, "extra": 1},
    ],
)
def test_date_helper_rejects(novelty_env, value):
    import json

    with novelty_env["engine"].connect() as conn:
        assert (
            conn.execute(
                text("SELECT pr218_valid_time_scope(CAST(:v AS jsonb))"), {"v": json.dumps(value)}
            ).scalar_one()
            is False
        )


def test_catalog_and_empty_downgrade(novelty_env, phase2_database_url):
    e = novelty_env
    with e["engine"].connect() as conn:
        assert conn.execute(text("SHOW server_version_num")).scalar_one().startswith("18")
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND "
                    "tablename IN ('search_coverage','search_coverage_executions',"
                    "'prior_art_relations',"
                    "'prior_art_evidence_inputs','novelty_assessments')"
                )
            ).scalar_one()
            == 5
        )
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM pg_constraint WHERE conname LIKE 'fk_pr218_%' "
                    "AND confdeltype<>'r'"
                )
            ).scalar_one()
            == 0
        )
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM pg_indexes WHERE "
                    "indexname='uq_pr218_novelty_predecessor' AND indexdef LIKE '%WHERE%'"
                )
            ).scalar_one()
            == 1
        )
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", phase2_database_url)
    command.downgrade(cfg, "0045_pr2_16_basic_approval")
    command.upgrade(cfg, "head")
    result = e["service"].record_search_coverage(
        e["author"],
        RecordSearchCoverageCommand(
            uuid4(), e["project"], e["plan"], e["executions"], "Selected observations."
        ),
    )
    with pytest.raises(DBAPIError):
        command.downgrade(cfg, "0045_pr2_16_basic_approval")
    with e["engine"].connect() as conn:
        assert (
            conn.execute(
                text("SELECT content_hash FROM search_coverage WHERE id=:id"), {"id": result.id}
            ).scalar_one()
            == result.content_hash
        )


@pytest.mark.parametrize(
    "operation",
    [
        "UPDATE search_coverage SET query_count=99",
        "DELETE FROM search_coverage",
        "INSERT INTO search_coverage_executions SELECT "
        "gen_random_uuid(),created_at,created_by,id,:execution FROM search_coverage",
    ],
)
def test_sealed_sets(novelty_env, operation):
    e = novelty_env
    e["service"].record_search_coverage(
        e["author"],
        RecordSearchCoverageCommand(
            uuid4(), e["project"], e["plan"], e["executions"], "Selected scope."
        ),
    )
    with pytest.raises(DBAPIError) as error:
        with e["engine"].begin() as conn:
            if operation.startswith("INSERT"):
                from researchbase.persistence.novelty_repository import N

                conn.execute(text("LOCK TABLE " + ",".join(N) + " IN SHARE MODE"))
            conn.execute(text(operation), {"execution": e["executions"][0]})
    assert getattr(error.value.orig, "sqlstate", None) == "P17D1"


def test_direct_sql_requires_preheld_locks(novelty_env):
    e = novelty_env
    with pytest.raises(DBAPIError) as error:
        with e["engine"].begin() as conn:
            conn.execute(
                text(
                    """INSERT INTO search_coverage
                            VALUES(:id,clock_timestamp(),:actor,:plan,'[]',0,0,0,NULL,
                                   'Bounded scope',:hash,'sha256-cjson-v1')"""
                ),
                {"id": uuid4(), "actor": e["author"].actor_id, "plan": e["plan"], "hash": "a" * 64},
            )
    assert getattr(error.value.orig, "sqlstate", None) == "P17D3"


@pytest.mark.parametrize("outcome", ["CLOSE_PRIOR_ART_FOUND", "NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE"])
def test_normal_role_stronger_outcomes_denied(novelty_env, novelty_sql_role, outcome):
    e = novelty_env
    cov = e["service"].record_search_coverage(
        e["author"],
        RecordSearchCoverageCommand(
            uuid4(), e["project"], e["plan"], e["executions"], "Selected scope."
        ),
    )
    with pytest.raises(DBAPIError) as error:
        with e["engine"].begin() as conn:
            conn.execute(text(f'SET LOCAL ROLE "{novelty_sql_role}"'))
            assert (
                conn.execute(
                    text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")
                ).scalar_one()
                is False
            )
            conn.execute(
                text("""INSERT INTO novelty_assessments VALUES(
                :id,clock_timestamp(),:actor,:claim,:coverage,:outcome,'No approved basis',
                :actor,NULL,:hash,'sha256-cjson-v1')"""),
                {
                    "id": uuid4(),
                    "actor": e["author"].actor_id,
                    "claim": e["claim"],
                    "coverage": cov.id,
                    "outcome": outcome,
                    "hash": "a" * 64,
                },
            )
    assert (
        getattr(getattr(error.value.orig, "diag", None), "constraint_name", None)
        == "ck_pr218_novelty_initial_slice"
    )


def test_deferred_prior_art_rechecks_verification(novelty_env, novelty_sql_role):
    from researchbase.application.novelty import RecordPriorArtRelationCommand
    from researchbase.domain.novelty import PriorArtKind

    e = novelty_env
    existing = e["service"].record_prior_art_relation(
        e["author"],
        RecordPriorArtRelationCommand(
            uuid4(),
            e["project"],
            e["claim"],
            e["source"],
            PriorArtKind.RELATED,
            "Comparison",
            (e["evidence"],),
        ),
    )
    new = uuid4()
    with pytest.raises(DBAPIError) as error:
        with e["engine"].begin() as conn:
            conn.execute(text(f'SET LOCAL ROLE "{novelty_sql_role}"'))
            conn.execute(
                text("""INSERT INTO prior_art_relations SELECT :id,created_at,created_by,
                claim_version_id,source_version_id,relation,rationale,assessed_by,content_hash,hash_scheme
                FROM prior_art_relations WHERE id=:old"""),
                {"id": new, "old": existing.id},
            )
            conn.execute(
                text("""INSERT INTO prior_art_evidence_inputs VALUES(
                :id,clock_timestamp(),:actor,:parent,:evidence)"""),
                {
                    "id": uuid4(),
                    "actor": e["author"].actor_id,
                    "parent": new,
                    "evidence": e["evidence"],
                },
            )
            conn.execute(
                text("""INSERT INTO literature_evidence_review_events
                (id,literature_evidence_id,prior_status,new_status,reviewed_by,reviewed_at,basis)
                VALUES(:id,:evidence,'VERIFIED','DISPUTED',:actor,
                    clock_timestamp(),'New concern')"""),
                {"id": uuid4(), "evidence": e["evidence"], "actor": e["reviewer"].actor_id},
            )
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert getattr(error.value.orig, "sqlstate", None) == "P17D3"
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM prior_art_relations")).scalar_one() == 1
        assert (
            conn.execute(
                text("SELECT review_status FROM literature_evidence WHERE id=:id"),
                {"id": e["evidence"]},
            ).scalar_one()
            == "VERIFIED"
        )


def test_populated_upgrade_cannot_be_lost_during_downgrade(
    novelty_env, phase2_database_url, monkeypatch
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from researchbase.persistence.novelty_repository import SqlAlchemyNoveltyRepository
    from tests.integration.phase2.test_pr2_18_concurrency import _witness

    e = novelty_env
    ready = Event()
    release = Event()
    pids = []
    original = SqlAlchemyNoveltyRepository.force_constraints

    def pause(repo):
        original(repo)
        pids.append(repo._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
        ready.set()
        assert release.wait(10)

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "force_constraints", pause)
    c = RecordSearchCoverageCommand(
        uuid4(), e["project"], e["plan"], e["executions"], "Selected scope."
    )
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", phase2_database_url)

    def downgrade():
        with pytest.raises(DBAPIError):
            command.downgrade(cfg, "0045_pr2_16_basic_approval")

    with ThreadPoolExecutor(max_workers=2) as pool:
        capture = pool.submit(e["service"].record_search_coverage, e["author"], c)
        assert ready.wait(10)
        down = pool.submit(downgrade)
        try:
            _witness(e["engine"], pids[0])
        finally:
            release.set()
        saved = capture.result(timeout=10)
        down.result(timeout=10)
    with e["engine"].connect() as conn:
        assert (
            conn.execute(
                text("SELECT content_hash FROM search_coverage WHERE id=:id"), {"id": saved.id}
            ).scalar_one()
            == saved.content_hash
        )


@pytest.mark.parametrize(
    "mutation", ["query_count+1", "result_count+1", "resolved_source_count+1", "providers", "empty"]
)
def test_normal_sql_false_aggregates_and_empty_sets_fail(novelty_env, novelty_sql_role, mutation):
    e = novelty_env
    original = e["service"].record_search_coverage(
        e["author"],
        RecordSearchCoverageCommand(
            uuid4(), e["project"], e["plan"], e["executions"], "Selected scope."
        ),
    )
    fresh = uuid4()
    counts = {
        name: name + "+1" if mutation == name + "+1" else name
        for name in ("query_count", "result_count", "resolved_source_count")
    }
    providers = "'[\"uninvoked\"]'::jsonb" if mutation == "providers" else "providers"
    from researchbase.persistence.novelty_repository import N

    with pytest.raises(DBAPIError) as error:
        with e["engine"].begin() as conn:
            conn.execute(text(f'SET LOCAL ROLE "{novelty_sql_role}"'))
            conn.execute(text("LOCK TABLE " + ",".join(N) + " IN SHARE MODE"))
            conn.execute(
                text(
                    """INSERT INTO search_coverage SELECT :id,created_at,created_by,
                search_plan_version_id,"""
                    + providers
                    + ","
                    + ",".join(counts.values())
                    + """,time_scope,
                coverage_limitations,content_hash,hash_scheme FROM search_coverage WHERE id=:old"""
                ),
                {"id": fresh, "old": original.id},
            )
            if mutation != "empty":
                conn.execute(
                    text("""INSERT INTO search_coverage_executions SELECT gen_random_uuid(),
                    created_at,created_by,:fresh,search_execution_id FROM search_coverage_executions
                    WHERE search_coverage_id=:old"""),
                    {"fresh": fresh, "old": original.id},
                )
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert getattr(error.value.orig, "sqlstate", None) == "P17D3"


def test_normal_sql_cannot_spoof_lock_inventory_with_temp_tables(novelty_env, novelty_sql_role):
    from researchbase.persistence.novelty_repository import N

    e = novelty_env
    with e["engine"].begin() as conn:
        conn.execute(text(f'SET LOCAL ROLE "{novelty_sql_role}"'))
        conn.execute(text("CREATE TEMP TABLE actors (id UUID)"))
        conn.execute(text("SET LOCAL search_path = pg_temp, public"))
        conn.execute(text("LOCK TABLE actors IN SHARE MODE"))
        conn.execute(
            text(
                "LOCK TABLE "
                + ",".join("public." + name for name in N if name != "actors")
                + " IN SHARE MODE"
            )
        )
        assert conn.execute(text("SELECT public.pr218_capture_prelocked()")).scalar_one() is False
