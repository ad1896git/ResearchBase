from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from researchbase.application.literature_search_plan import (
    CreateLiteratureSearchPlan,
    LiteratureSearchPlanService,
    UpdateLiteratureSearchPlanDraft,
)
from researchbase.domain.literature_search_plan import (
    LiteratureSearchPlanMaterial,
    LiteratureSearchStrategy,
    LiteratureSourceScope,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.test_pr2_01_source_identity import _authorized_service
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _AlwaysValidCredential,
    _material,
)


def _service(engine):
    return LiteratureSearchPlanService(
        lambda: SqlAlchemyUnitOfWork(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        ),
        _AlwaysValidCredential(),
    )


def _create_material(objective="Find relevant evidence"):
    return LiteratureSearchPlanMaterial(
        plan_id=UUID(int=0),
        research_question_refs=(),
        objective=objective,
        source_scope=LiteratureSourceScope.BIBLIOGRAPHIC,
        inclusion_criteria={"statements": ["peer-reviewed"]},
        exclusion_criteria=None,
        time_range={"from": date(2020, 1, 1), "through": None},
        language_scope=None,
        search_strategy=LiteratureSearchStrategy.KEYWORD,
        planned_providers=("provider-a",),
        stopping_rule=None,
    )


def _expected_create_hash(project_id, objective="Find relevant evidence"):
    return str(
        sha256_canonical_json(
            {
                "project_id": str(project_id),
                "objective": objective,
                "source_scope": "BIBLIOGRAPHIC",
                "inclusion_criteria": {"statements": ["peer-reviewed"]},
                "exclusion_criteria": None,
                "time_range": {"from": "2020-01-01", "through": None},
                "language_scope": None,
                "search_strategy": "KEYWORD",
                "planned_providers": ["provider-a"],
                "stopping_rule": None,
                "research_question_version_ids": [],
            }
        )
    )


def _capture_state(engine, principal, project_id, request_id, record_property):
    with engine.connect() as connection:
        counts = dict(
            connection.execute(
                text(
                    "SELECT (SELECT count(*) FROM literature_search_plans "
                    "WHERE project_id=:project) "
                    "AS plan_count, (SELECT count(*) FROM literature_search_plan_versions v "
                    "JOIN literature_search_plans p ON p.id=v.plan_id WHERE p.project_id=:project) "
                    "AS version_count"
                ),
                {"project": project_id},
            )
            .mappings()
            .one()
        )
        receipts = [
            dict(row)
            for row in connection.execute(
                text(
                    "SELECT deployment_id,actor_id,project_id,command_name,request_id,request_hash,"
                    "result_plan_id,result_plan_version_id,result_dto FROM "
                    "literature_search_plan_command_receipts WHERE deployment_id=:deployment "
                    "AND actor_id=:actor AND project_id=:project AND request_id=:request "
                    "ORDER BY command_name"
                ),
                {
                    "deployment": principal.deployment_id,
                    "actor": principal.actor_id,
                    "project": project_id,
                    "request": request_id,
                },
            ).mappings()
        ]
    record_property(
        "idempotency_evidence",
        json.dumps(
            {
                "project_id": project_id,
                "counts": counts,
                "receipts": receipts,
            },
            default=str,
            sort_keys=True,
        ),
    )
    return counts, receipts


def _create(service, principal, project_id, request_id, objective="Find relevant evidence"):
    return service.create(
        CreateLiteratureSearchPlan(
            principal,
            project_id,
            _create_material(objective),
            request_id,
        )
    )


def test_same_key_replays_and_changed_canonical_request_conflicts(
    phase2_database_url: str, record_property
) -> None:
    engine, _, _, principal, project_id = _authorized_service(phase2_database_url)
    service = _service(engine)
    request_id = uuid4()
    original = _create(service, principal, project_id, request_id)
    replayed = _create(service, principal, project_id, request_id)
    assert replayed == original
    with pytest.raises(ResearchBaseError) as conflict:
        _create(service, principal, project_id, request_id, objective="A different objective")
    assert conflict.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    counts, receipts = _capture_state(engine, principal, project_id, request_id, record_property)
    assert counts == {"plan_count": 1, "version_count": 1}
    assert len(receipts) == 1
    assert receipts[0]["request_hash"] == _expected_create_hash(project_id)
    assert receipts[0]["request_hash"] != _expected_create_hash(project_id, "A different objective")
    assert receipts[0]["result_dto"] == original == replayed
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM literature_search_plans WHERE project_id=:project"),
                {"project": project_id},
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM literature_search_plan_command_receipts "
                    "WHERE project_id=:project AND command_name='CREATE_LITERATURE_SEARCH_PLAN' "
                    "AND request_id=:request"
                ),
                {"project": project_id, "request": request_id},
            ).scalar_one()
            == 1
        )
    engine.dispose()


def test_request_id_reuse_across_projects_and_command_names_is_allowed(
    phase2_database_url: str, record_property
) -> None:
    engine, identity, _, principal, project_id = _authorized_service(phase2_database_url)
    service = _service(engine)
    request_id = uuid4()
    first = _create(service, principal, project_id, request_id)
    second_project = identity.create_project_with_owner(
        principal, name="Second search-plan project", request_id=uuid4()
    )
    second = _create(service, principal, second_project, request_id)
    assert first["plan_id"] != second["plan_id"]

    plan_id, version_id = UUID(str(first["plan_id"])), UUID(str(first["version_id"]))
    updated = service.update(
        UpdateLiteratureSearchPlanDraft(
            principal,
            project_id,
            plan_id,
            version_id,
            _material(plan_id, language_scope=None),
            request_id,
        )
    )
    assert updated["plan_id"] == first["plan_id"]
    counts, receipts = _capture_state(engine, principal, project_id, request_id, record_property)
    second_counts, second_receipts = _capture_state(
        engine, principal, second_project, request_id, record_property
    )
    assert counts == second_counts == {"plan_count": 1, "version_count": 1}
    assert {row["command_name"] for row in receipts} == {
        "CREATE_LITERATURE_SEARCH_PLAN",
        "UPDATE_LITERATURE_SEARCH_PLAN_DRAFT",
    }
    assert len(receipts) == 2 and len(second_receipts) == 1
    assert second_receipts[0]["request_hash"] == _expected_create_hash(second_project)
    assert second_receipts[0]["result_dto"] == second
    with engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM literature_search_plan_command_receipts "
                    "WHERE project_id=:project AND request_id=:request"
                ),
                {"project": project_id, "request": request_id},
            ).scalar_one()
            == 2
        )
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM literature_search_plan_command_receipts "
                    "WHERE project_id=:project AND request_id=:request"
                ),
                {"project": second_project, "request": request_id},
            ).scalar_one()
            == 1
        )
    engine.dispose()


def test_concurrent_same_key_create_has_one_durable_mutation_and_replay(
    phase2_database_url: str, record_property
) -> None:
    engine, _, _, principal, project_id = _authorized_service(phase2_database_url)
    service = _service(engine)
    request_id = uuid4()
    barrier = Barrier(2)

    def invoke():
        barrier.wait(timeout=10)
        return _create(service, principal, project_id, request_id)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: invoke(), range(2)))
        assert results[0] == results[1]
        counts, receipts = _capture_state(
            engine, principal, project_id, request_id, record_property
        )
        assert counts == {"plan_count": 1, "version_count": 1}
        assert len(receipts) == 1
        assert receipts[0]["request_hash"] == _expected_create_hash(project_id)
        assert receipts[0]["result_dto"] == results[0] == results[1]
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT count(*) FROM literature_search_plans WHERE project_id=:project"),
                    {"project": project_id},
                ).scalar_one()
                == 1
            )
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM literature_search_plan_versions WHERE plan_id=:plan"
                    ),
                    {"plan": UUID(str(results[0]["plan_id"]))},
                ).scalar_one()
                == 1
            )
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM literature_search_plan_command_receipts "
                        "WHERE project_id=:project "
                        "AND command_name='CREATE_LITERATURE_SEARCH_PLAN' "
                        "AND request_id=:request"
                    ),
                    {"project": project_id, "request": request_id},
                ).scalar_one()
                == 1
            )
    finally:
        engine.dispose()
