"""Frozen pack §§6, 12, 13.2: admission-only exact frozen plan backstop."""

from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _AlwaysValidCredential,
    _material as _plan_material,
)
from tests.integration.phase2.test_pr2_03_review_guards import _freeze
from tests.integration.phase2.test_pr2_04_schema_coverage import (
    E,
    V,
    _execution_with_created_event,
    _material,
    _reject,
    _rows,
)

from researchbase.application.literature_search_execution import (
    CreateLiteratureSearchExecution,
    LiteratureSearchExecutionService,
    RecoverLiteratureSearchExecution,
)
from researchbase.application.literature_search_plan import (
    CreateLiteratureSearchPlan,
    ReviseLiteratureSearchPlan,
    TransitionLiteratureSearchPlanVersion,
)
from researchbase.persistence.literature_search_execution_uow import (
    literature_search_execution_uow_factory,
)


def _version(engine, version):
    with engine.connect() as connection:
        return dict(
            connection.execute(
                text("SELECT * FROM literature_search_plan_versions WHERE id=:id"),
                {"id": version},
            ).mappings().one()
        )


def _supersede(material):
    plans = material["plans"]
    principal, project, plan, version = (
        material[key] for key in ("principal", "project", "plan", "version")
    )
    revised = plans.revise(ReviseLiteratureSearchPlan(principal, project, plan, version, uuid4()))
    successor = UUID(revised["version_id"])
    plans.freeze(TransitionLiteratureSearchPlanVersion(principal, project, plan, successor, uuid4()))
    assert _version(material["engine"], version)["status"] == "SUPERSEDED"
    assert _version(material["engine"], successor)["status"] == "FROZEN"
    return successor


@pytest.mark.parametrize("state", ["DRAFT", "ABANDONED", "SUPERSEDED"])
@pytest.mark.pr204_requirements("PR204-DB-01")
def test_direct_sql_rejects_ineligible_initial_plan_state(
    phase2_database_url, pr204_trace: FactRecorder, state
):
    material = _material(phase2_database_url, "planned")
    engine = material["engine"]
    try:
        before = _rows(engine)
        row = {**before[E][0], "id": uuid4(), "idempotency_key": uuid4()}
        if state == "SUPERSEDED":
            _supersede(material)
        else:
            draft = material["plans"].create(
                CreateLiteratureSearchPlan(
                    material["principal"], material["project"],
                    _plan_material(UUID(int=0), language_scope=()), uuid4(),
                )
            )
            row["search_plan_version_id"] = UUID(draft["version_id"])
            if state == "ABANDONED":
                material["plans"].abandon(
                    TransitionLiteratureSearchPlanVersion(
                        material["principal"], material["project"], UUID(draft["plan_id"]),
                        row["search_plan_version_id"], uuid4(),
                    )
                )
        version = _version(engine, row["search_plan_version_id"])
        assert version["status"] == state
        pr204_trace.record(initial_plan=version, expected_sqlstate="P17D5")
        _reject(engine, lambda c: _execution_with_created_event(c, row, before[V][0]),
                "P17D5", pr204_trace, case=state)
        assert _version(engine, row["search_plan_version_id"]) == version
        assert material["provider"].calls == []
    finally:
        engine.dispose()


@pytest.mark.pr204_requirements("PR204-DB-01")
def test_direct_sql_accepts_exact_frozen_plan_in_same_project(
    phase2_database_url, pr204_trace: FactRecorder,
):
    material = _material(phase2_database_url, "planned")
    engine = material["engine"]
    try:
        before = _rows(engine)
        version = _version(engine, material["version"])
        row = {**before[E][0], "id": uuid4(), "idempotency_key": uuid4()}
        with engine.begin() as connection:
            project = connection.execute(
                text("SELECT project_id FROM literature_search_plans WHERE id=:id"),
                {"id": version["plan_id"]},
            ).scalar_one()
            _execution_with_created_event(connection, row, before[V][0])
        after = _rows(engine)
        admitted = next(x for x in after[E] if x["id"] == row["id"])
        pr204_trace.record(plan=version, owning_project=project, execution=admitted,
                           before_counts={t: len(v) for t, v in before.items()},
                           after_counts={t: len(v) for t, v in after.items()})
        assert version["status"] == "FROZEN"
        assert project == row["project_id"]
        assert admitted["search_plan_version_id"] == material["version"]
        assert admitted["execution_context"] == row["execution_context"]
        assert _version(engine, material["version"]) == version
        assert len(after[E]) == len(before[E]) + 1
        assert len(after[V]) == len(before[V]) + 1
        assert all(after[t] == before[t] for t in before if t not in {E, V})
        assert material["provider"].calls == []
    finally:
        engine.dispose()


@pytest.mark.pr204_requirements("PR204-DB-01")
def test_started_execution_recovers_and_replays_after_canonical_plan_supersession(
    phase2_database_url, pr204_trace: FactRecorder,
):
    material = _material(phase2_database_url, "sealed")
    engine = material["engine"]
    try:
        before = _rows(engine)
        original = _version(engine, material["version"])
        assert before[E][0]["status"] == "RUNNING"
        assert before[E][0]["started_at"] is not None
        assert original["status"] == "FROZEN"
        successor = _supersede(material)
        historical = _version(engine, material["version"])
        assert {k: v for k, v in historical.items() if k not in {"status", "row_version"}} == {
            k: v for k, v in original.items() if k not in {"status", "row_version"}
        }
        service = LiteratureSearchExecutionService(
            literature_search_execution_uow_factory(
                sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
            ), material["provider"], credential_verifier=_AlwaysValidCredential(),
        )
        principal = material["principal"]
        command = RecoverLiteratureSearchExecution(
            material["execution"], principal.actor_id, principal.deployment_id, uuid4(),
            project_id=material["project"], principal=principal,
        )
        calls = len(material["provider"].calls)
        result = service.recover(command)
        after = _rows(engine)
        replay = service.recover(command)
        assert _rows(engine) == after
        create_replay = service.create(CreateLiteratureSearchExecution(
            material["project"], material["version"], principal.actor_id,
            principal.deployment_id, before[E][0]["idempotency_key"], "provider-a", "1",
            ("normalization evidence",), principal=principal,
        ))
        assert _rows(engine) == after
        pr204_trace.record(original_plan=original, historical_plan=historical,
                           successor_version=successor, execution_before=before[E],
                           execution_after=after[E], recovery=result, replay=replay,
                           create_replay=create_replay, provider_calls_before=calls,
                           provider_calls_after=len(material["provider"].calls))
        assert result == replay
        assert create_replay["execution_id"] == str(material["execution"])
        assert after[E][0]["status"] == "SUCCEEDED"
        assert after[E][0]["search_plan_version_id"] == material["version"]
        assert after[E][0]["execution_context"] == before[E][0]["execution_context"]
        assert _version(engine, material["version"]) == historical
        assert len(material["provider"].calls) == calls
    finally:
        engine.dispose()


@pytest.mark.parametrize("field", ["content_hash", "objective"])
@pytest.mark.pr204_requirements("PR204-DB-01")
def test_admitted_plan_material_and_hash_remain_immutable(
    phase2_database_url, pr204_trace: FactRecorder, field
):
    material = _material(phase2_database_url, "planned")
    engine = material["engine"]
    try:
        original = _version(engine, material["version"])
        replacement = "0" * 64 if field == "content_hash" else "changed scientific objective"
        _reject(
            engine,
            lambda c: c.execute(
                text(f"UPDATE literature_search_plan_versions SET {field}=:value WHERE id=:id"),
                {"id": material["version"], "value": replacement},
            ),
            "P17D1",
            pr204_trace,
            case=field,
        )
        after = _version(engine, material["version"])
        pr204_trace.record(original_plan=original, after_plan=after)
        assert after == original
        assert material["provider"].calls == []
    finally:
        engine.dispose()
