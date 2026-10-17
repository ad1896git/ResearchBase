"""Exact historical plan identity at admission, first start and subsequent outcome."""

from dataclasses import replace
from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from researchbase.application.literature_search_plan import (
    CreateLiteratureSearchPlan,
    LiteratureSearchPlanService,
    ReviseLiteratureSearchPlan,
    TransitionLiteratureSearchPlanVersion,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.test_pr2_00_challenges import _service as _identity_service
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _AlwaysValidCredential,
    _material,
)
from tests.integration.phase2.test_pr2_03_review_guards import _freeze
from tests.integration.phase2.test_pr2_04_idempotency_coverage import (
    _command,
    _execution_setup,
    _snapshot,
)


@pytest.fixture
def execution_case(phase2_database_url):
    yield from _execution_setup(phase2_database_url)


@pytest.mark.parametrize("case", ["missing", "foreign", "draft", "abandoned", "superseded"])
@pytest.mark.pr204_requirements("PR204-DOM-03", "PR204-DOM-04", "PR204-TRACE-01")
def test_pg_admission_rejects_invalid_exact_plan_without_effects(
    execution_case, phase2_database_url, case, pr204_trace: FactRecorder
):
    engine, service, provider, principal, project, command = execution_case
    identity, _, _ = _identity_service(phase2_database_url)
    other = principal
    other_project = identity.create_project_with_owner(
        other, name="invalid execution plan fixture", request_id=uuid4()
    )
    other_engine = engine
    plans = LiteratureSearchPlanService(
        lambda: SqlAlchemyUnitOfWork(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        ),
        _AlwaysValidCredential(),
    )
    created = plans.create(
        CreateLiteratureSearchPlan(
            other, other_project, _material(UUID(int=0), language_scope=()), uuid4()
        )
    )
    plan, version = UUID(str(created["plan_id"])), UUID(str(created["version_id"]))
    try:
        if case in {"foreign", "superseded"}:
            _freeze(other_engine, plans, other, other_project, plan, version)
        if case == "abandoned":
            plans.abandon(
                TransitionLiteratureSearchPlanVersion(other, other_project, plan, version, uuid4())
            )
        if case == "superseded":
            successor = plans.revise(
                ReviseLiteratureSearchPlan(other, other_project, plan, version, uuid4())
            )
            successor_id = UUID(str(successor["version_id"]))
            plans.freeze(
                TransitionLiteratureSearchPlanVersion(
                    other, other_project, plan, successor_id, uuid4()
                )
            )
            with engine.connect() as connection:
                assert (
                    connection.scalar(
                        text("SELECT status FROM literature_search_plan_versions WHERE id=:id"),
                        {"id": version},
                    )
                    == "SUPERSEDED"
                )
                assert (
                    connection.scalar(
                        text("SELECT current_version_id FROM literature_search_plans WHERE id=:id"),
                        {"id": plan},
                    )
                    == successor_id
                )
        # Foreign is a real frozen version, queried under the original authorized project.
        # Other cases use their valid same-project authority, isolating lifecycle validation.
        target = replace(command, plan_version_id=version)
        if case != "foreign":
            target = replace(
                target,
                project_id=other_project,
                actor_id=other.actor_id,
                deployment_id=other.deployment_id,
                principal=other,
            )
        if case == "missing":
            target = replace(target, plan_version_id=uuid4())
        before = _snapshot(engine, target.project_id)
        with pytest.raises(ResearchBaseError) as caught:
            service.create(target)
        after = _snapshot(engine, target.project_id)
        pr204_trace.record(
            case=case,
            supplied_plan=target.plan_version_id,
            error_code=caught.value.code.value,
            before=before,
            after=after,
            provider_calls=len(provider.calls),
        )
        expected = (
            ErrorCode.NOT_FOUND
            if case in {"missing", "foreign"}
            else ErrorCode.SEARCH_PLAN_NOT_FROZEN
        )
        assert caught.value.code is expected
        assert before == after and provider.calls == []
    finally:
        other_engine.dispose()


@pytest.mark.parametrize("timing", ["before_first_start", "during_provider"])
@pytest.mark.pr204_requirements("PR204-DOM-03", "PR204-DOM-04", "PR204-TRACE-01")
def test_pg_plan_supersession_never_substitutes_current_version(
    execution_case, phase2_database_url, timing, pr204_trace: FactRecorder
):
    engine, service, provider, principal, project, create = execution_case
    plans = LiteratureSearchPlanService(
        lambda: SqlAlchemyUnitOfWork(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        ),
        _AlwaysValidCredential(),
    )
    admitted = service.create(create)
    execution_id = UUID(admitted["execution_id"])
    initial = service.get_provenance(principal, project, execution_id)
    plan_id = UUID(initial["plan"]["material"]["plan_id"])
    successors = []

    def supersede(_request=None):
        successors.append(
            plans.revise(
                ReviseLiteratureSearchPlan(
                    principal, project, plan_id, create.plan_version_id, uuid4()
                )
            )
        )
        successor_id = UUID(str(successors[-1]["version_id"]))
        plans.freeze(
            TransitionLiteratureSearchPlanVersion(
                principal, project, plan_id, successor_id, uuid4()
            )
        )
        with engine.connect() as connection:
            assert (
                connection.scalar(
                    text("SELECT status FROM literature_search_plan_versions WHERE id=:id"),
                    {"id": create.plan_version_id},
                )
                == "SUPERSEDED"
            )
            assert (
                connection.scalar(
                    text("SELECT current_version_id FROM literature_search_plans WHERE id=:id"),
                    {"id": plan_id},
                )
                == successor_id
            )

    if timing == "before_first_start":
        supersede()
        before = _snapshot(engine, project)
        with pytest.raises(ResearchBaseError) as caught:
            service.execute(_command("execute", principal, project, execution_id))
        assert caught.value.code is ErrorCode.SEARCH_PLAN_NOT_FROZEN
        assert _snapshot(engine, project) == before and provider.calls == []
    else:
        provider.observer = supersede
        service.execute(_command("execute", principal, project, execution_id))
        assert len(provider.calls) == 1
    after = service.get_provenance(principal, project, execution_id)
    pr204_trace.record(
        timing=timing,
        initial=initial,
        after=after,
        successors=successors,
        provider_calls=len(provider.calls),
    )
    assert after["plan"]["plan_version_id"] == str(create.plan_version_id)
    assert after["plan"]["content_hash"] == initial["plan"]["content_hash"]
    assert successors[0]["version_id"] != str(create.plan_version_id)
    assert after["execution"]["status"] == (
        "PLANNED" if timing == "before_first_start" else "SUCCEEDED"
    )


@pytest.mark.parametrize("boundary", ["create", "first_start", "provenance"])
@pytest.mark.pr204_requirements("PR204-DOM-03", "PR204-TRACE-01")
def test_pg_corrupt_exact_plan_hash_rejects_without_current_pointer_substitution(
    execution_case, boundary, pr204_trace: FactRecorder
):
    engine, service, provider, principal, project, create = execution_case
    execution_id = None
    if boundary != "create":
        execution_id = UUID(service.create(create)["execution_id"])
    with engine.begin() as connection:
        original = connection.execute(
            text("SELECT content_hash FROM literature_search_plan_versions WHERE id=:id"),
            {"id": create.plan_version_id},
        ).scalar_one()
        # Deliberate privileged tampering in the disposable DB, followed by normal guarded reads.
        connection.execute(text("ALTER TABLE literature_search_plan_versions DISABLE TRIGGER USER"))
        connection.execute(
            text("UPDATE literature_search_plan_versions SET content_hash=:hash WHERE id=:id"),
            {"hash": "0" * 64, "id": create.plan_version_id},
        )
        connection.execute(text("ALTER TABLE literature_search_plan_versions ENABLE TRIGGER USER"))
    before = _snapshot(engine, project)
    operation = (
        (lambda: service.create(create))
        if boundary == "create"
        else (
            (lambda: service.execute(_command("execute", principal, project, execution_id)))
            if boundary == "first_start"
            else (lambda: service.get_provenance(principal, project, execution_id))
        )
    )
    with pytest.raises(ResearchBaseError) as caught:
        operation()
    after = _snapshot(engine, project)
    pr204_trace.record(
        boundary=boundary,
        original_plan_hash=original,
        stored_corrupt_hash="0" * 64,
        error_code=caught.value.code.value,
        before=before,
        after=after,
        provider_calls=len(provider.calls),
    )
    assert caught.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert before == after and provider.calls == []
