"""Deterministic-count disposable benchmark science built only by owning services."""

from __future__ import annotations

from dataclasses import replace
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text

from researchbase.application.commands import FreezeClaimVersionCommand, LinkEvidenceCommand
from researchbase.application.decision import DecisionService, RecordDecisionCommand
from researchbase.application.internal_review import InternalReviewService, ReviewIssueRequest
from researchbase.application.manuscript_placement import ClaimPlacementService
from researchbase.application.manuscript_scientific_trace import ManuscriptScientificTraceService
from researchbase.application.publication import PublicationService
from researchbase.application.scientific_conclusion import (
    ClaimInputRequest,
    ScientificConclusionService,
)
from researchbase.application.source_identity import (
    AddSourceIdentifier,
    RegisterLiteratureSource,
    SourceIdentityService,
    VerifySourceIdentifier,
)
from researchbase.application.source_version import (
    CreateSourceVersion,
    SourceVersionService,
    TransitionSourceVersion,
)
from researchbase.domain.organization import ProjectId
from researchbase.domain.source_identity import IdentifierType, SourceKind
from researchbase.domain.source_version import (
    SourceVersionKind,
    SourceVersionMaterial,
)
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import SystemClock
from tests.application_compat import LegacyApplicationService
from tests.integration.phase2 import pr2_20_support as s
from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service
from tests.integration.phase2.test_pr2_10_binding_contract import _artifact
from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE
from tests.integration.test_pr12_application import seed_claim, seed_measurement


def build(m3, url, tmp_path, counts: dict[str, int]) -> dict[str, Any]:
    literature, author, reviewer, project, existing_version, _, document, engine, credentials = m3
    s.upgrade(url)
    factory = literature._factory
    sources = SourceIdentityService(factory, credentials)
    versions = SourceVersionService(factory, credentials)
    identity, _, _ = identity_service(url, credential_verifier=credentials)
    projects = [project] + [
        identity.create_project_with_owner(
            author, name=f"TEST ONLY PR220 project {i}", request_id=uuid4()
        )
        for i in range(1, counts["projects"])
    ]
    with engine.connect() as conn:
        existing_source = conn.execute(
            text("SELECT literature_source_id FROM source_versions WHERE id=:id"),
            {"id": existing_version},
        ).scalar_one()
    source_rows = []
    for index in range(counts["sources"]):
        owner = (
            project
            if index < counts["busy_project_sources"]
            else projects[1 + (index - counts["busy_project_sources"]) % (len(projects) - 1)]
        )
        title = "Technical fixture" if index == 0 else f"TEST ONLY PR220 source {index}"
        doi = f"10.2202/pr220-{index}"
        if index == 0:
            source_id = existing_source
            identifier = sources.add_source_identifier(
                AddSourceIdentifier(
                    author, owner, source_id, IdentifierType.DOI, doi, True, uuid4()
                )
            )
        else:
            identifier = sources.register_literature_source(
                RegisterLiteratureSource(
                    author, owner, SourceKind.PAPER, title, uuid4(), IdentifierType.DOI, doi
                )
            )
            source_id = UUID(str(identifier["source_id"]))
        sources.add_source_identifier(
            AddSourceIdentifier(
                author,
                owner,
                source_id,
                IdentifierType.URL,
                f"https://example.org/pr220/{index}",
                False,
                uuid4(),
            )
        )
        if index < counts["shared_sources"]:
            sources.verify_source_identifier(
                VerifySourceIdentifier(
                    author,
                    owner,
                    UUID(str(identifier["identifier_id"])),
                    UUID(document["artifact_version_id"]),
                    "TEST ONLY shared source identity basis",
                    uuid4(),
                )
            )
            linked = sources.register_literature_source(
                RegisterLiteratureSource(
                    author, projects[1], SourceKind.PAPER, title, uuid4(), IdentifierType.DOI, doi
                )
            )
            assert UUID(str(linked["source_id"])) == source_id
        for version_number in range(1 if index else 2, 3):
            material = SourceVersionMaterial(
                source_id,
                SourceVersionKind.PUBLISHED,
                None,
                None,
                f"{title} version {version_number}",
                None,
                (),
                None,
                None,
                None,
                None,
                None,
            )
            created = versions.create(CreateSourceVersion(author, owner, material, uuid4()))
            versions.freeze(
                TransitionSourceVersion(
                    author, owner, UUID(str(created["source_version_id"])), uuid4()
                )
            )
        source_rows.append((owner, source_id, doi))
    store = ContentAddressedFilesystemArtifactStore(tmp_path / "pr220-cas")
    app = LegacyApplicationService(factory, SystemClock(), store)
    execution = ExecutionContext(actor_id=author.actor_id, request_id=uuid4(), client_type="test")
    measurements = [
        seed_measurement(app, ProjectId(project), execution, f"pr220-m{i}") for i in range(4)
    ]
    claims = []
    for _ in range(counts["claims"]):
        claim, draft = seed_claim(app, ProjectId(project), execution)
        for measurement in measurements:
            current = app.get_current_claim_version(claim.id)
            app.link_evidence(
                LinkEvidenceCommand(
                    claim.id,
                    draft.id,
                    measurement,
                    None,
                    "supports",
                    None,
                    current.row_version,
                    execution,
                )
            )
        current = app.get_current_claim_version(claim.id)
        frozen = app.freeze_claim_version(
            FreezeClaimVersionCommand(claim.id, draft.id, execution, current.row_version)
        )
        claims.append(UUID(str(frozen.id)))
    publications = PublicationService(factory, credentials, store)
    artifact = _artifact(
        factory, store, author, project, b"TEST ONLY PR220 manuscript", "manuscript"
    )
    manuscripts = []
    for index in range(counts["manuscripts"]):
        publication = publications.create_publication(
            author, project, "PAPER", f"TEST ONLY paper {index}", uuid4()
        )
        draft = publications.create_draft(
            author, project, publication.id, artifact, "TEST ONLY paper", None, "INITIAL", uuid4()
        )
        manuscripts.append((publication.id, draft.id))
        size = counts["high_placements"] if index == 1 else counts["typical_placements"]
        for ordinal in range(size):
            ClaimPlacementService(factory, credentials).add(
                author,
                project,
                publication.id,
                draft.id,
                claims[ordinal % len(claims)],
                None,
                "RESULTS",
                {"kind": "PARAGRAPH", "value": f"p{ordinal}"},
                "DESCRIPTIVE",
                ordinal,
                uuid4(),
            )
    conclusions = ScientificConclusionService(factory, credentials, literature)
    reviews = InternalReviewService(factory, credentials, literature)
    targets = []
    per_target = counts["reviews"] // counts["conclusion_targets"]
    per_review = counts["issues"] // counts["reviews"]
    for index in range(counts["conclusion_targets"]):
        created = conclusions.create(
            author,
            project,
            f"TEST ONLY conclusion {index}",
            SCOPE,
            "MODERATE",
            None,
            (ClaimInputRequest(claims[index % len(claims)], "SUPPORTS"),),
            (),
            uuid4(),
        )
        conclusions.freeze(author, project, created.conclusion_id, created.version_id, uuid4())
        for _ in range(per_target):
            reviews.create(
                reviewer,
                project,
                "SCIENTIFIC_CONCLUSION_VERSION",
                created.version_id,
                "SCIENTIFIC",
                "ACCEPT",
                "TEST ONLY complete independent review",
                tuple(
                    ReviewIssueRequest("INFO", "OTHER", f"TEST ONLY issue {i}")
                    for i in range(per_review)
                ),
                uuid4(),
            )
        targets.append(created.version_id)
    tables = {
        "projects": "projects",
        "sources": "literature_sources",
        "source_versions": "source_versions",
        "identifiers": "source_identifiers",
        "project_links": "literature_source_project_links",
        "claims": "claim_versions",
        "manuscripts": "manuscript_versions",
        "conclusion_targets": "scientific_conclusion_versions",
        "reviews": "internal_review_records",
        "issues": "review_issues",
    }
    actual = dict(counts)
    with engine.connect() as conn:
        for key, table in tables.items():
            actual[key] = conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
        assert (
            conn.execute(
                text("SELECT count(*) FROM source_versions WHERE status IN ('FROZEN','SUPERSEDED')")
            ).scalar_one()
            == counts["source_versions"]
        )
        assert (
            conn.execute(text("SELECT count(*) FROM evidence_relations")).scalar_one()
            == counts["claims"] * 4
        )
        distribution = (
            conn.execute(
                text(
                    "SELECT count(*) FROM literature_source_project_links GROUP BY lite"
                    "rature_source_id"
                )
            )
            .scalars()
            .all()
        )
        assert distribution.count(2) == counts["shared_sources"]
        assert max(distribution) == 2
        assert (
            conn.execute(
                text("SELECT count(*) FROM literature_source_project_links WHERE project_id=:id"),
                {"id": project},
            ).scalar_one()
            == counts["busy_project_sources"]
        )
    assert actual == counts
    with engine.begin() as conn:
        conn.execute(text("ANALYZE"))
    canonical = s.manifest(
        engine,
        tuple(tables.values()) + ("evidence_relations", "scientific_conclusion_claim_inputs"),
    )
    canonical = s.persist_manifest("benchmark-fixture", canonical)
    s.save_observation(
        "benchmark-fixture",
        {
            "actual_counts": actual,
            "manifest": canonical,
            "limitation": "Superseded manuscript history BLOCKED: owning lifecycle unavailable",
        },
    )
    decisions = DecisionService(factory, credentials, literature)
    commands = [
        RecordDecisionCommand(uuid4(), project, target, "q" * 128, "r" * 128) for target in targets
    ]
    s.save_observation(
        "benchmark-request-identities",
        {
            "requests": [
                {
                    "request_id": str(command.id),
                    "target_version_id": str(command.scientific_conclusion_version_id),
                }
                for command in commands
            ]
        },
    )
    saved = {}
    trace = ManuscriptScientificTraceService(factory, credentials)
    expected_traces = [trace.trace(author, project, *pair) for pair in manuscripts[:2]]

    def prepare(case):
        if case == "decision-replay":
            for i, request in enumerate(commands):
                saved[i] = decisions.record_decision(reviewer, request)

    def call(case, index):
        if case.startswith("lookup"):
            caller = replace(author, actor_id=uuid4()) if case == "lookup-denied" else author
            identifier = "10.2202/pr220-0" if case != "lookup-miss" else "10.2202/absent"
            try:
                result = sources.find_source_by_identifier(
                    caller, project, IdentifierType.DOI, identifier
                )
            except ResearchBaseError as error:
                assert error.code == (
                    ErrorCode.AUTHENTICATION_REQUIRED
                    if case == "lookup-denied"
                    else ErrorCode.SOURCE_NOT_FOUND
                )
                return error.code.value
            assert case == "lookup-hit" and UUID(str(result["source_id"])) == existing_source
            return result
        if case.startswith("trace"):
            position = 1 if case == "trace-high" else 0
            result = trace.trace(author, project, *manuscripts[position])
            assert result == expected_traces[position]
            return result
        if case in {"decision-first-write", "review-gate"}:
            assert index not in saved, "first-write must have a fresh exact target/request"
            result = decisions.record_decision(reviewer, commands[index])
            assert (
                len([ref for ref in result.basis if ref.type == "InternalReviewRecord"])
                == per_target
            )
            saved[index] = result
            return result
        assert case == "decision-replay" and index in saved
        result = decisions.record_decision(reviewer, commands[index])
        assert result == saved[index]
        return result

    return {
        "counts": actual,
        "call": call,
        "prepare": prepare,
        "limitation": "Superseded manuscript history BLOCKED: owning lifecycle unavailable",
    }
