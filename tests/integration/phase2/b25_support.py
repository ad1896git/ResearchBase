"""B25 test helpers using the accepted B04/B05 owner fixtures."""

from uuid import uuid4

from researchbase.application.governance import (
    CreateImpactAssessmentCommand,
    GovernanceService,
    ProposedImpactTarget,
)
from researchbase.application.manuscript_placement import ClaimPlacementService
from researchbase.application.manuscript_validity import (
    GetManuscriptAuditQuery,
    GetManuscriptValidityQuery,
    ManuscriptValidityService,
)
from researchbase.application.scientific_conclusion import ClaimInputRequest
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import SystemClock
from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE


def queries(env):
    q = env[1]
    service = ManuscriptValidityService(env[4], env[9], env[7])
    return (
        service,
        GetManuscriptValidityQuery(q.project_id, q.publication_id, q.manuscript_version_id),
        GetManuscriptAuditQuery(q.project_id, q.publication_id, q.manuscript_version_id),
    )


def place(env, *, conclusion=False, ordinal=0):
    q = env[1]
    identity = env[8]
    if conclusion:
        scientific = env[10][0]
        result = scientific.create(
            env[2],
            q.project_id,
            "B25 test conclusion",
            SCOPE,
            "MODERATE",
            None,
            (ClaimInputRequest(identity, "SUPPORTS"),),
            (),
            uuid4(),
        )
        scientific.freeze(env[2], q.project_id, result.conclusion_id, result.version_id, uuid4())
        identity = result.version_id
    ClaimPlacementService(env[4], env[9], env[7]).add(
        env[2],
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        None if conclusion else identity,
        identity if conclusion else None,
        "DISCUSSION" if conclusion else "RESULTS",
        {"kind": "PARAGRAPH", "value": f"p{ordinal}"},
        "SUPPORTED",
        ordinal,
        uuid4(),
    )
    return identity


def impact(env, kind, identity, state):
    return GovernanceService(env[4], SystemClock()).create_impact_assessment(
        CreateImpactAssessmentCommand(
            env[1].project_id,
            None,
            {"test": "B25"},
            state,
            (ProposedImpactTarget(kind, identity, state),),
            ExecutionContext(actor_id=env[2].actor_id, request_id=uuid4(), client_type="test"),
        )
    )


def source_transition(env, kind):
    from dataclasses import replace
    from uuid import UUID

    from researchbase.application.source_version import (
        CreateSourceVersion,
        SourceVersionService,
        TransitionSourceVersion,
        _material_from_row,
    )
    from researchbase.domain.source_version import FrozenSourceReference, SourceVersionKind
    from tests.integration.phase2.test_pr2_10_binding_contract import _artifact

    source = env[10][7]
    basis = _artifact(
        env[4], env[7], env[2], env[1].project_id, b"B25 source correction basis", "other"
    )
    with env[4]() as uow:
        old = uow.source_version.version(source)
        material = _material_from_row(uow.source_version, old)
        basis_row = uow.manuscript_freeze.artifact(basis, env[1].project_id)
    material = replace(
        material,
        version_kind=SourceVersionKind(kind),
        predecessor_source_version=FrozenSourceReference(source, old["content_hash"]),
        correction_basis_artifact=FrozenSourceReference(basis, basis_row["content_hash"]),
    )
    service = SourceVersionService(env[4], env[9])
    created = service.create(CreateSourceVersion(env[2], env[1].project_id, material, uuid4()))
    identity = UUID(str(created["source_version_id"]))
    service.freeze(TransitionSourceVersion(env[2], env[1].project_id, identity, uuid4()))
    return identity


def literature_conclusion(env, *, snapshot=False, source=None):
    from uuid import UUID

    from researchbase.application.scientific_conclusion import LiteratureInputRequest

    service = env[10][2]
    scientific = env[10][0]
    project = env[1].project_id
    created = service.create(env[2], project, source or env[10][7], "improved recall", uuid4())
    evidence = UUID(created["id"])
    service.review(env[3], project, evidence, "VERIFIED", "Independent evidence review", uuid4())
    support = None
    if snapshot:
        created_snapshot = service.snapshot(
            env[2],
            project,
            "ClaimVersion",
            env[8],
            [
                {
                    "evidence_id": evidence,
                    "relation_type": "SUPPORTS",
                    "qualification": "Relevant independent support",
                }
            ],
            uuid4(),
        )
        support = UUID(created_snapshot["id"])
    result = scientific.create(
        env[2],
        project,
        "B25 literature conclusion",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(env[8], "SUPPORTS", support),) if snapshot else (),
        () if snapshot else (LiteratureInputRequest(evidence, "SUPPORTS"),),
        uuid4(),
    )
    scientific.freeze(env[2], project, result.conclusion_id, result.version_id, uuid4())
    q = env[1]
    ClaimPlacementService(env[4], env[9], env[7]).add(
        env[2],
        project,
        q.publication_id,
        q.manuscript_version_id,
        None,
        result.version_id,
        "DISCUSSION",
        {"kind": "PARAGRAPH", "value": "literature"},
        "SUPPORTED",
        0,
        uuid4(),
    )
    return evidence, support, result.version_id
