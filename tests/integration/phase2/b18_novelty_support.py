"""Bounded consumer fixture; every new canonical write uses its owning service."""

from dataclasses import asdict, replace
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from researchbase.application.literature_search_execution import (
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
    LiteratureSearchExecutionService,
)
from researchbase.application.literature_search_provider import (
    FakeSearchCapability,
    StaticSearchCapabilityRegistry,
)
from researchbase.application.novelty import (
    ExactReadQuery,
    RecordNoveltyAssessmentCommand,
    RecordPriorArtRelationCommand,
    RecordSearchCoverageCommand,
)
from researchbase.application.search_result_resolution import (
    RecordSearchResultResolutionCommand,
    SearchResultResolutionService,
)
from researchbase.application.source_identity import (
    AddSourceIdentifier,
    SourceIdentityService,
    VerifySourceIdentifier,
)
from researchbase.domain.literature_search_execution import SearchHit, SearchResponse
from researchbase.domain.novelty import NoveltyOutcome, PriorArtKind
from researchbase.domain.source_identity import IdentifierType
from researchbase.persistence.literature_search_execution_uow import (
    literature_search_execution_uow_factory,
)
from tests.integration.phase2 import pr2_20_support as s
from tests.integration.phase2.b01_support import record

KINDS = ("coverage", "prior_art", "novelty")
NOVELTY_CASES = tuple(
    f"{kind}-{operation}" for kind in KINDS for operation in ("first", "replay", "read")
)
SIDE_EFFECT_TABLES = (
    "claim_versions",
    "evidence_relations",
    "literature_support_snapshots",
    "internal_review_records",
    "decision_records",
    "approval_requests",
    "approval_grants",
    "approval_grant_consumptions",
    "prepared_submission_versions",
    "author_consents",
)
NOVELTY_TABLES = (
    "search_coverage",
    "search_coverage_executions",
    "search_coverage_resolutions",
    "prior_art_relations",
    "prior_art_evidence_inputs",
    "novelty_assessments",
)
CARDINALITIES = dict(
    selected_executions=1,
    queries=1,
    results=2,
    resolved_sources=1,
    unresolved_results=1,
    verified_evidence_inputs=1,
    frozen_claims=1,
)
PHANTOM_REFERENCES = (
    "test_b01_resolution_concurrency.py::test_both_coverage_commit_orders_and_empty_history_phantom",
    "test_b01_resolution_concurrency.py::test_b01_append_after_source_only_stays_ambiguous",
)


def stable(value):
    """Compare complete DTOs except explicitly timestamped current observations."""

    def normalize(item):
        if isinstance(item, dict):
            output = {}
            for key, val in item.items():
                if key == "observed_at":
                    assert isinstance(val, datetime) and val.utcoffset() == UTC.utcoffset(val)
                    output[key] = "<current observation time>"
                else:
                    output[key] = normalize(val)
            return output
        if isinstance(item, tuple | list):
            return tuple(normalize(x) for x in item)
        return item

    return normalize(asdict(value))


@pytest.fixture
def b18_env(novelty_env):
    return build(dict(novelty_env))


def build(e: dict[str, Any], *, assessment=True) -> dict[str, Any]:
    """Reuse the owning search/resolution graph with optional assessment absence."""
    with e["engine"].connect() as conn:
        source, artifact = conn.execute(
            text(
                "SELECT literature_source_id,fulltext_artifact_version_id "
                "FROM source_versions WHERE id=:id"
            ),
            {"id": e["source"]},
        ).one()
    identities = SourceIdentityService(e["factory"], e["credentials"])
    added = identities.add_source_identifier(
        AddSourceIdentifier(
            e["author"], e["project"], source, IdentifierType.DOI, "10.1234/b18", True, uuid4()
        )
    )
    identities.verify_source_identifier(
        VerifySourceIdentifier(
            e["author"],
            e["project"],
            UUID(str(added["identifier_id"])),
            artifact,
            "Independent identifier inspection against retained fixture bytes",
            uuid4(),
        )
    )
    response = SearchResponse.success(
        provider_id="test",
        provider_version="v1",
        normalized_query="bounded novelty",
        provider_request_id=None,
        retrieved_at=datetime.now(UTC),
        hits=tuple(
            SearchHit(str(i), "Technical fixture", "https://doi.org/10.1234/b18", None, None)
            for i in (1, 2)
        ),
    )
    sf = sessionmaker(e["engine"], expire_on_commit=False, autoflush=False)
    searches = LiteratureSearchExecutionService(
        literature_search_execution_uow_factory(sf),
        StaticSearchCapabilityRegistry((FakeSearchCapability("test", "v1", responses=[response]),)),
        credential_verifier=e["credentials"],
    )
    execution = UUID(
        searches.create(
            CreateLiteratureSearchExecution(
                e["project"],
                e["plan"],
                e["author"].actor_id,
                e["author"].deployment_id,
                uuid4(),
                "test",
                "v1",
                ("bounded novelty",),
                principal=e["author"],
                max_provider_attempts=1,
            )
        )["execution_id"]
    )
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
    results = tuple(
        UUID(row["id"])
        for row in searches.get_provenance(e["author"], e["project"], execution)["results"]
    )
    resolution = dict(
        service=SearchResultResolutionService(e["factory"], e["credentials"], e["store"]),
        principal=e["author"],
        command=RecordSearchResultResolutionCommand(
            uuid4(),
            e["project"],
            results[0],
            source,
            e["source"],
            "Verified DOI and exact title with retained bytes",
        ),
    )
    record(resolution)
    e.update(executions=(execution,), results=results, resolution=resolution)
    e["commands"] = {
        "coverage": RecordSearchCoverageCommand(
            uuid4(),
            e["project"],
            e["plan"],
            (execution,),
            "Selected bounded scope; no screening or priority assertion",
        ),
        "prior_art": RecordPriorArtRelationCommand(
            uuid4(),
            e["project"],
            e["claim"],
            e["source"],
            PriorArtKind.RELATED,
            "Exact verified comparison",
            (e["evidence"],),
        ),
    }
    protected = protected_manifest(e)
    coverage = e["service"].record_search_coverage(e["author"], e["commands"]["coverage"])
    e["commands"]["novelty"] = RecordNoveltyAssessmentCommand(
        uuid4(),
        e["project"],
        e["claim"],
        coverage.id,
        NoveltyOutcome.INCONCLUSIVE,
        "Bounded selected coverage cannot establish universal priority",
    )
    e["saved"] = {"coverage": coverage}
    for kind in KINDS[1:] if assessment else ("prior_art",):
        e["saved"][kind] = invoke(e, kind, "first")
    assert (coverage.query_count, coverage.result_count, coverage.resolved_source_count) == (
        1,
        2,
        1,
    )
    assert coverage.quality.current_unresolved_result_count == 1
    assert protected_manifest(e) == protected
    return e


def invoke(e, kind, operation, *, command=None, service=None):
    service = service or e["service"]
    suffix = {
        "coverage": "search_coverage",
        "prior_art": "prior_art_relation",
        "novelty": "novelty_assessment",
    }[kind]
    cmd = command or e["commands"][kind]
    if operation == "read":
        return getattr(service, "read_" + suffix)(e["author"], ExactReadQuery(e["project"], cmd.id))
    return getattr(service, "record_" + suffix)(e["author"], cmd)


def resolve_remaining(e):
    return record(e["resolution"], id=uuid4(), search_result_record_id=e["results"][1])


def protected_manifest(e):
    with e["engine"].connect() as conn:
        present = set(
            conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
            ).scalars()
        )
    existing = tuple(t for t in SIDE_EFFECT_TABLES if t in present)
    result = s.manifest(e["engine"], existing)
    for table in SIDE_EFFECT_TABLES:
        if table not in present:
            result[table] = {"count": 0, "schema": "ABSENT"}
    return result


def fresh_command(e, kind):
    return replace(e["commands"][kind], id=uuid4())
