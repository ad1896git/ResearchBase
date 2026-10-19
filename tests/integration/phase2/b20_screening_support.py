"""B20 builders reuse exact existing owners; retain every declared branch."""

from dataclasses import replace
from typing import Any
from uuid import UUID, uuid4

from researchbase.application.novelty import (
    RecordNoveltyAssessmentCommand,
    RecordSearchCoverageCommand,
)
from researchbase.domain.novelty import (
    ClosenessCriteria,
    NoveltyOutcome,
    ProbeDisposition,
    ProbeInput,
    ScreeningBasisInput,
    ScreeningDisposition,
    ScreeningResultInput,
)


def request(e):
    coverage = e["service"].record_search_coverage(
        e["author"],
        RecordSearchCoverageCommand(
            uuid4(), e["project"], e["plan"], e["all_executions"], "All exact-plan executions"
        ),
    )
    probes = []
    results = []
    with e["factory"]() as uow:
        for identity in coverage.search_execution_ids:
            history = uow.literature_search_execution.provenance(identity)
            execution = history["execution"]
            for i in range(len(execution.execution_context["queries"])):
                disposition = ProbeDisposition.INCOMPLETE
                if execution.status == "SUCCEEDED" and all(
                    a["status"] == "SUCCEEDED" and not a["warning_codes"]
                    for a in history["attempts"]
                ):
                    disposition = (
                        ProbeDisposition.SCREENED
                        if any(
                            a["query_index"] == i
                            and a["query_record_id"] == result.search_query_record_id
                            for a in history["attempts"]
                            for result in history["results"]
                        )
                        else ProbeDisposition.NO_HITS
                    )
                probes.append(ProbeInput(identity, i, disposition, "Retained intended query"))
            results.extend(
                ScreeningResultInput(
                    x.id, ScreeningDisposition.UNRESOLVED, (0,), "Unresolved retained hit"
                )
                for x in history["results"]
            )
    return RecordNoveltyAssessmentCommand(
        uuid4(),
        e["project"],
        e["claim"],
        coverage.id,
        NoveltyOutcome.INCONCLUSIVE,
        "Retrospective bounded coverage",
        scope_statement="All visible exact-plan executions",
        closeness_criteria=ClosenessCriteria(("Method differs",)),
        screening_basis=ScreeningBasisInput(tuple(probes), tuple(results)),
    )


def record(e, command):
    return e["service"].record_novelty_assessment(e["author"], command)


def successful_plan(
    e,
    *,
    hits=(),
    planned_providers=("test",),
    queries=("prior art",),
    warning_codes=(),
    hits_by_query=None,
) -> tuple[dict[str, Any], Any, Any]:
    """Create a separate frozen plan with one fully successful execution."""
    from datetime import UTC, datetime

    from sqlalchemy.orm import sessionmaker

    from researchbase.application.literature_search_execution import (
        CreateLiteratureSearchExecution,
        ExecuteLiteratureSearchExecution,
        LiteratureSearchExecutionService,
    )
    from researchbase.application.literature_search_plan import (
        CreateLiteratureSearchPlan,
        LiteratureSearchPlanService,
        TransitionLiteratureSearchPlanVersion,
        _material_from_rows,
    )
    from researchbase.application.literature_search_provider import (
        FakeSearchCapability,
        StaticSearchCapabilityRegistry,
    )
    from researchbase.domain.literature_search_execution import SearchResponse
    from researchbase.persistence.literature_search_execution_uow import (
        literature_search_execution_uow_factory,
    )

    with e["factory"]() as uow:
        row = uow.literature_search_plan.version(e["plan"])
        material = _material_from_rows(uow.literature_search_plan, e["project"], row)
    material = replace(material, plan_id=uuid4(), planned_providers=planned_providers)
    plans = LiteratureSearchPlanService(e["factory"], e["credentials"])
    value = plans.create(CreateLiteratureSearchPlan(e["author"], e["project"], material, uuid4()))
    plan = UUID(str(value["version_id"]))
    plans.freeze(
        TransitionLiteratureSearchPlanVersion(
            e["author"], e["project"], UUID(str(value["plan_id"])), plan, uuid4()
        )
    )
    provider = FakeSearchCapability(
        "test",
        "v1",
        responses=[
            SearchResponse.success(
                provider_id="test",
                provider_version="v1",
                normalized_query=query,
                provider_request_id=None,
                hits=hits if hits_by_query is None else hits_by_query[index],
                retrieved_at=datetime.now(UTC),
            )
            if not warning_codes
            else replace(
                SearchResponse.success(
                    provider_id="test",
                    provider_version="v1",
                    normalized_query=query,
                    provider_request_id=None,
                    hits=hits if hits_by_query is None else hits_by_query[index],
                    retrieved_at=datetime.now(UTC),
                ),
                warning_codes=warning_codes,
            )
            for index, query in enumerate(queries)
        ],
    )
    searches = LiteratureSearchExecutionService(
        literature_search_execution_uow_factory(
            sessionmaker(e["engine"], expire_on_commit=False, autoflush=False)
        ),
        StaticSearchCapabilityRegistry((provider,)),
        credential_verifier=e["credentials"],
    )
    value = searches.create(
        CreateLiteratureSearchExecution(
            e["project"],
            plan,
            e["author"].actor_id,
            e["author"].deployment_id,
            uuid4(),
            "test",
            "v1",
            queries,
            principal=e["author"],
            max_provider_attempts=len(queries),
        )
    )
    execution = UUID(value["execution_id"])
    searches.execute(
        ExecuteLiteratureSearchExecution(
            execution,
            e["author"].actor_id,
            e["author"].deployment_id,
            uuid4(),
            project_id=e["project"],
            principal=e["author"],
        )
    )
    return (
        dict(
            e,
            plan=plan,
            all_executions=(execution,),
            executions=(execution,),
            results=tuple(
                UUID(x["id"])
                for x in searches.get_provenance(e["author"], e["project"], execution)["results"]
            ),
        ),
        searches,
        provider,
    )


def compared(e, *, ambiguous_capture=False):
    from researchbase.application.novelty import RecordPriorArtRelationCommand
    from researchbase.domain.literature_search_execution import SearchHit
    from researchbase.domain.novelty import PriorArtKind
    from tests.integration.phase2.pr2_18_fixtures import add_resolution

    e, _, _ = successful_plan(e, hits=(SearchHit("1", "Prior paper", None, None, None),))
    witness = add_resolution(e, e["results"][0])
    if ambiguous_capture:
        add_resolution(e, e["results"][0], version=False)
    rc = RecordPriorArtRelationCommand(
        uuid4(),
        e["project"],
        e["claim"],
        e["source"],
        PriorArtKind.RELATED,
        "Independent comparison",
        (e["evidence"],),
    )
    relation = e["service"].record_prior_art_relation(e["author"], rc)
    c = request(e)
    assert c.screening_basis is not None
    c = replace(
        c,
        assessment=NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE,
        screening_basis=ScreeningBasisInput(
            c.screening_basis.probes,
            (
                ScreeningResultInput(
                    e["results"][0],
                    ScreeningDisposition.NOT_CLOSE,
                    (0,),
                    "Compared exact method",
                    relation.id,
                    witness["id"],
                ),
            ),
        ),
    )
    return e, c, rc, witness
