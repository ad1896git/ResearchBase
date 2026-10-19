"""Use existing owning commands and resolution fixture for a selected positive basis."""

from uuid import uuid4

from researchbase.application.novelty import (
    RecordNoveltyAssessmentCommand,
    RecordPriorArtRelationCommand,
    RecordSearchCoverageCommand,
)
from researchbase.domain.novelty import (
    ClosenessCriteria,
    NoveltyOutcome,
    PriorArtBasisInput,
    PriorArtKind,
)
from tests.integration.phase2.pr2_18_fixtures import add_resolution


def setup(e, *, kind=PriorArtKind.IDENTICAL, coverage=None):
    cov = coverage or e["service"].record_search_coverage(
        e["author"],
        RecordSearchCoverageCommand(
            uuid4(), e["project"], e["plan"], e["executions"], "Selected scope; not exhaustive"
        ),
    )
    # Witness intentionally postdates capture: saved coverage counts stay unchanged.
    witness = add_resolution(e, e["results"][0])
    relation_command = RecordPriorArtRelationCommand(
        uuid4(),
        e["project"],
        e["claim"],
        e["source"],
        kind,
        "Independent inspected comparison",
        (e["evidence"],),
    )
    relation = e["service"].record_prior_art_relation(e["author"], relation_command)
    c = RecordNoveltyAssessmentCommand(
        uuid4(),
        e["project"],
        e["claim"],
        cov.id,
        NoveltyOutcome.CLOSE_PRIOR_ART_FOUND,
        "Selected comparison only",
        prior_art_basis=(PriorArtBasisInput(relation.id, witness["id"]),),
        scope_statement="Inspected selected executions",
        closeness_criteria=ClosenessCriteria(("Same method", "Same result")),
    )
    return c, relation_command, relation, witness


def record(e, c):
    return e["service"].record_novelty_assessment(e["author"], c)


def source_change(e, kind):
    from uuid import UUID

    from researchbase.application.source_version import (
        CreateSourceVersion,
        SourceVersionService,
        TransitionSourceVersion,
    )
    from researchbase.domain.source_version import FrozenSourceReference, SourceVersionMaterial

    with e["factory"]() as uow:
        old = uow.source_version.version(e["source"])
        artifact = uow.literature_evidence.artifact(
            old["fulltext_artifact_version_id"], e["project"]
        )
    service = SourceVersionService(e["factory"], e["credentials"])
    draft = service.create(
        CreateSourceVersion(
            e["author"],
            e["project"],
            SourceVersionMaterial(
                old["literature_source_id"],
                kind,
                FrozenSourceReference(old["id"], old["content_hash"]),
                FrozenSourceReference(artifact["id"], artifact["content_hash"]),
                "Source notice",
                None,
                (),
                None,
                None,
                None,
                None,
                None,
            ),
            uuid4(),
        )
    )
    command = TransitionSourceVersion(
        e["author"], e["project"], UUID(str(draft["source_version_id"])), uuid4()
    )
    return service, command


def legacy_coverage(e):
    """Seed v1 coverage at the pre-B21 revision for populated migration witnesses."""
    from researchbase.domain.novelty import HashRef, coverage_material
    from researchbase.foundation.hashing import sha256_canonical_json

    identity = uuid4()
    with e["factory"]() as uow:
        repo = uow.novelty
        repo.prepare("coverage", identity)
        plan, providers, queries, results, resolved, scope, _, _ = e["service"]._capture(
            uow, e["project"], e["plan"], e["executions"]
        )
        material = coverage_material(
            plan,
            e["executions"],
            providers,
            queries,
            results,
            resolved,
            scope,
            "Legacy selected scope",
        )
        at = repo.at()
        repo.insert(
            "coverage",
            dict(
                id=identity,
                created_at=at,
                created_by=e["author"].actor_id,
                search_plan_version_id=e["plan"],
                providers=list(providers),
                query_count=queries,
                result_count=results,
                resolved_source_count=resolved,
                time_scope=scope.material() if scope else None,
                coverage_limitations="Legacy selected scope",
                content_hash=str(sha256_canonical_json(material)),
                hash_scheme="sha256-cjson-v1",
            ),
        )
        for execution in e["executions"]:
            repo.insert_child(
                "coverage",
                dict(
                    id=uuid4(),
                    created_at=at,
                    created_by=e["author"].actor_id,
                    search_coverage_id=identity,
                    search_execution_id=execution,
                ),
            )
        repo.force_constraints()
        result = HashRef("SearchCoverage", identity, str(sha256_canonical_json(material)))
        uow.commit()
        return result
