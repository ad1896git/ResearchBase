"""B15 accepted B04/S1 fixtures and exact PREPARED Application lifecycle."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b15_support import (  # noqa: F401
    b04_env as _b04_env,
)
from tests.integration.phase2.b15_support import (
    b15_env as _b15_env,
)
from tests.integration.phase2.b15_support import (
    build_env,
    prepared,
)
from tests.integration.phase2.b15_support import (
    conclusion_env as _conclusion_env,
)
from tests.integration.phase2.test_pr2_10_binding_contract import _artifact

b04_env = _b04_env
b15_env = _b15_env
conclusion_env = _conclusion_env

pytestmark = pytest.mark.integration


def test_prepare_exact_replay_and_version_allocation(b15_env):
    service, command, actor, *_ = b15_env
    result, query = prepared(b15_env)
    assert result.status == "PREPARED" and result.row_version == 1 and result.items == ()
    assert result.content_hash is result.package_manifest_hash is result.frozen_at is None
    assert result.current_validity == "NOT_FROZEN"
    assert result.validity_reasons == ("CONSENT_MISSING", "NOT_FROZEN")
    assert service.prepare_submission(actor, command) == result
    assert service.get_prepared_submission(actor, query) == result
    second = service.prepare_submission(actor, replace(command, id=uuid4()))
    assert second.version_number == result.version_number + 1
    with pytest.raises(ResearchBaseError) as exc:
        service.prepare_submission(actor, replace(command, authorship_snapshot_id=uuid4()))
    assert exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT


@pytest.mark.parametrize("other", [False, True])
def test_direct_occurrences_preserve_multiplicity_and_other_denies(b04_env, other):
    from researchbase.application.manuscript_placement import (
        ArtifactPlacementService,
        CitationPlacementService,
        ClaimPlacementService,
    )
    from researchbase.application.scientific_conclusion import ClaimInputRequest
    from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE

    b04, q, actor, factory, _, credentials, store, claim, base = b04_env
    conclusion = base[0].create(
        actor,
        q.project_id,
        "Exact conclusion",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(claim, "SUPPORTS"),),
        (),
        uuid4(),
    )
    base[0].freeze(actor, q.project_id, conclusion.conclusion_id, conclusion.version_id, uuid4())
    placements = ClaimPlacementService(factory, credentials, store)
    for ordinal, (target, final) in enumerate(((claim, None), (None, conclusion.version_id))):
        placements.add(
            actor,
            q.project_id,
            q.publication_id,
            q.manuscript_version_id,
            target,
            final,
            "RESULTS",
            {"kind": "PARAGRAPH", "value": str(ordinal)},
            "SUPPORTED",
            ordinal,
            uuid4(),
        )
    CitationPlacementService(factory, credentials).add(
        actor,
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        base[7],
        "INTRO",
        {"kind": "PARAGRAPH", "value": "cite"},
        "BACKGROUND",
        0,
        uuid4(),
    )
    artifact = _artifact(factory, store, actor, q.project_id, b"direct figure", "figure")
    for ordinal, role in enumerate(("FIGURE", "TABLE", "OTHER" if other else "FIGURE")):
        ArtifactPlacementService(factory, credentials).add(
            actor,
            q.project_id,
            q.publication_id,
            q.manuscript_version_id,
            artifact,
            "Z",
            {"kind": "ANCHOR", "value": str(ordinal)},
            role,
            ordinal,
            uuid4(),
        )
    # Invoke the fixture's underlying builder only after canonical placement commands.
    env = build_env(b04_env)
    if other:
        with pytest.raises(ResearchBaseError) as exc:
            prepared(env)
        assert exc.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
        return
    result, _ = prepared(env)
    assert [i.category for i in result.items] == [
        "CITATION",
        "CLAIM",
        "CONCLUSION",
        "FIGURE",
        "FIGURE",
        "TABLE",
    ]
    assert [i.target.id for i in result.items if i.category == "FIGURE"] == [artifact, artifact]


def test_version_exhaustion_maps_to_closed_transition(b15_env, monkeypatch):
    from researchbase.persistence.prepared_submission_repository import (
        SqlAlchemyPreparedSubmissionRepository,
    )

    service, command, actor, _, engine, *_ = b15_env
    original = SqlAlchemyPreparedSubmissionRepository.next_version
    monkeypatch.setattr(
        SqlAlchemyPreparedSubmissionRepository, "next_version", lambda self, publication: 2147483647
    )
    assert service.prepare_submission(actor, command).version_number == 2147483647
    monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, "next_version", original)
    with pytest.raises(ResearchBaseError) as exc:
        service.prepare_submission(actor, replace(command, id=uuid4()))
    assert exc.value.code == ErrorCode.INVALID_STATE_TRANSITION
    with engine.connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM prepared_submission_versions")).scalar_one()
            == 1
        )
