"""Completed reassessment admission denies unrelated and nonterminal results."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.revision_action import (
    RecordNoveltyRevisionCommand,
    RecordRevisionActionCommand,
    RevisionActionService,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_b23_novelty_review import _review, _root


@pytest.mark.parametrize("case", ["self", "independent", "descendant", "superseded", "missing"])
def test_invalid_results_atomic(novelty_env, case):
    e = novelty_env
    c, root = _root(e)
    _, review = _review(e, root)
    result_id = root.id
    if case == "independent":
        result_id = e["service"].record_novelty_assessment(e["author"], replace(c, id=uuid4())).id
    if case in ("descendant", "superseded"):
        successor = e["service"].record_novelty_assessment(
            e["author"], replace(c, id=uuid4(), supersedes_assessment_id=root.id)
        )
        descendant = e["service"].record_novelty_assessment(
            e["author"], replace(c, id=uuid4(), supersedes_assessment_id=successor.id)
        )
        result_id = descendant.id if case == "descendant" else successor.id
    if case == "missing":
        result_id = uuid4()
    service = RevisionActionService(e["factory"], e["credentials"], e["literature"])
    with pytest.raises(ResearchBaseError) as error:
        service.record_novelty_revision(
            e["author"],
            RecordNoveltyRevisionCommand(uuid4(), e["project"], review.issues[0].id, result_id),
        )
    assert error.value.code is (
        ErrorCode.NOT_FOUND
        if case == "missing"
        else ErrorCode.INVALID_STATE_TRANSITION
        if case == "superseded"
        else ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    )
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM revision_actions")).scalar_one() == 0
        assert (
            conn.execute(
                text("SELECT status FROM review_issues WHERE id=:id"), {"id": review.issues[0].id}
            ).scalar_one()
            == "OPEN"
        )


def test_same_basis_correction_and_no_legacy_novelty_path(novelty_env):
    e = novelty_env
    c, root = _root(e)
    _, review = _review(e, root)
    result = e["service"].record_novelty_assessment(
        e["author"], replace(c, id=uuid4(), supersedes_assessment_id=root.id)
    )
    service = RevisionActionService(e["factory"], e["credentials"], e["literature"])
    command = RecordNoveltyRevisionCommand(uuid4(), e["project"], review.issues[0].id, result.id)
    first = service.record_novelty_revision(e["author"], command)
    correction = service.record_novelty_revision(
        e["author"], replace(command, id=uuid4(), supersedes_revision_action_id=first.id)
    )
    assert correction.predecessor.id == first.id
    assert service.read_revision_action(e["author"], e["project"], first.id).has_superseding_action
    with pytest.raises(ResearchBaseError) as error:
        service.record_novelty_revision(
            e["author"], replace(command, id=uuid4(), supersedes_revision_action_id=first.id)
        )
    assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION
    with pytest.raises(ResearchBaseError) as error:
        service.record_revision_action(
            e["author"],
            RecordRevisionActionCommand(
                uuid4(), e["project"], "NO_CHANGE", review_issue_id=review.issues[0].id
            ),
        )
    assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION


@pytest.mark.parametrize("change", ["comparison", "evidence", "CORRECTED", "RETRACTED"])
def test_unusable_result_denies_new_action_but_keeps_saved_history(novelty_env, change):
    from researchbase.domain.source_version import SourceVersionKind
    from tests.integration.phase2.b19_basis_support import record, setup, source_change

    e = novelty_env
    c, rc, relation, _ = setup(e)
    root = record(e, c)
    reviews, review = _review(e, root)
    result = record(e, replace(c, id=uuid4(), supersedes_assessment_id=root.id))
    actions = RevisionActionService(e["factory"], e["credentials"], e["literature"])
    cmd = RecordNoveltyRevisionCommand(uuid4(), e["project"], review.issues[0].id, result.id)
    saved = actions.record_novelty_revision(e["researcher"], cmd)
    if change == "comparison":
        e["service"].record_prior_art_relation(
            e["author"], replace(rc, id=uuid4(), supersedes_prior_art_relation_id=relation.id)
        )
    elif change == "evidence":
        e["literature"].review(
            e["reviewer"],
            e["project"],
            e["evidence"],
            "DISPUTED",
            "Later independent inspection",
            uuid4(),
        )
    else:
        sources, freeze = source_change(e, SourceVersionKind(change))
        sources.freeze(freeze)
    replay = actions.record_novelty_revision(e["researcher"], cmd)
    assert replay.content_hash == saved.content_hash
    assert not replay.result.current_validity.usable_for_current_judgment
    assert reviews.read(e["reviewer"], e["project"], review.id).content_hash == review.content_hash
    # Intact stale material is still reviewable.
    assert _review(e, result)[1].target_content_hash == result.content_hash
    with pytest.raises(ResearchBaseError) as error:
        actions.record_novelty_revision(e["researcher"], replace(cmd, id=uuid4()))
    assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM revision_actions")).scalar_one() == 1


@pytest.mark.parametrize("same_identity", [False, True])
def test_other_exact_claim_or_version_denied(novelty_env, same_identity):
    from researchbase.application.commands import (
        FreezeClaimVersionCommand,
        LinkEvidenceCommand,
        ReviseClaimCommand,
    )
    from researchbase.domain.claim import ClaimVersionId
    from researchbase.domain.organization import ProjectId
    from tests.integration.test_pr12_application import seed_claim, seed_measurement

    e = novelty_env
    c, root = _root(e)
    _, review = _review(e, root)
    app, ctx = e["application"], e["context"]
    if same_identity:
        old = app.get_claim_version(ClaimVersionId(e["claim"]))
        parent = app.get_claim(old.claim_id)
        app.revise_claim(
            ReviseClaimCommand(
                parent.id, "Different exact version", {}, None, parent.row_version, ctx
            )
        )
        draft = app.get_current_claim_version(parent.id)
    else:
        parent, draft = seed_claim(app, ProjectId(e["project"]), ctx)
    measurement = seed_measurement(app, ProjectId(e["project"]), ctx, "B23 different target")
    app.link_evidence(
        LinkEvidenceCommand(
            parent.id, draft.id, measurement, None, "supports", None, draft.row_version, ctx
        )
    )
    draft = app.get_current_claim_version(parent.id)
    frozen = app.freeze_claim_version(
        FreezeClaimVersionCommand(parent.id, draft.id, ctx, draft.row_version)
    )
    other = e["service"].record_novelty_assessment(
        e["author"], replace(c, id=uuid4(), claim_version_id=frozen.id)
    )
    actions = RevisionActionService(e["factory"], e["credentials"], e["literature"])
    with pytest.raises(ResearchBaseError) as error:
        actions.record_novelty_revision(
            e["researcher"],
            RecordNoveltyRevisionCommand(uuid4(), e["project"], review.issues[0].id, other.id),
        )
    assert error.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM revision_actions")).scalar_one() == 0
