"""B17 local freeze admission and atomic concrete receipt."""

# Literal SQL retains exact artifact selection.
# ruff: noqa: E501

from dataclasses import replace
from uuid import uuid4

import pytest

from researchbase.domain.approval import PreparedSubmissionFreezeResult
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b17_fixtures import (
    b04_env,
    b05_env,
    b17_env,
    build,
    conclusion_env,
    counts,
    decision_env,
    phase2_database_url,
    revision_env,
)

_FIXTURES = (
    b04_env,
    b05_env,
    b17_env,
    conclusion_env,
    decision_env,
    phase2_database_url,
    revision_env,
)
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


def test_complete_freeze_and_concrete_receipt(b17_env):
    f = b17_env
    receipt = f.app.freeze_prepared_submission(f.actor, f.command)
    assert isinstance(receipt.result, PreparedSubmissionFreezeResult)
    assert receipt.result.prepared_submission_version_id == f.command.result_id
    saved = f.app.get_prepared_submission(f.actor, f.query)
    assert saved.status == "FROZEN" and saved.row_version == 2
    assert saved.current_validity == "VALID" and saved.validity_reasons == ()
    assert saved.package_manifest_hash == f.command.expected_package_manifest_hash
    assert saved.content_hash and saved.frozen_at == receipt.consumed_at
    assert saved.consumption_id == receipt.id and saved.grant_id == receipt.grant_id
    assert [i.target.id for i in saved.items if i.category == "AUTHOR_CONSENT"] == [f.consent.id]
    assert (
        f.app.preview_prepared_submission(f.actor, f.query).candidate_manifest_hash
        == saved.package_manifest_hash
    )
    assert (
        f.approval.get_grant_consumption(f.actor, f.command.project_id, f.command.command_key)
        == receipt
    )


@pytest.mark.parametrize(
    "field,change,code",
    [
        ("expected_package_manifest_hash", "1" * 64, ErrorCode.CONCURRENT_MODIFICATION),
        ("checked_review_ids", (uuid4(),), ErrorCode.DECISION_BASIS_INVALID),
        ("grant_id", None, ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID),
    ],
)
def test_substitution_has_no_partial_effect(b17_env, field, change, code):
    f = b17_env
    before = counts(f)
    if field == "grant_id":
        change = f.ready_command.grant_id
    with pytest.raises(ResearchBaseError) as exc:
        f.app.freeze_prepared_submission(f.actor, replace(f.command, **{field: change}))
    assert exc.value.code == code
    assert counts(f) == before
    assert f.app.get_prepared_submission(f.actor, f.query).status == "PREPARED"


@pytest.mark.parametrize("case", ["missing_consent", "condition"])
def test_consent_is_mandatory(b05_env, case):
    f = build(b05_env, consent=case != "missing_consent", condition=case != "condition")
    before = counts(f)
    with pytest.raises(ResearchBaseError) as exc:
        f.app.freeze_prepared_submission(f.actor, f.command)
    assert exc.value.code == ErrorCode.APPROVAL_GATE_FAILED
    assert counts(f) == before


@pytest.mark.parametrize("kind", ["document", "consent"])
@pytest.mark.parametrize("corruption", ["missing", "corrupt"])
def test_exact_retained_bytes_required_and_zero_partial_effect(b17_env, kind, corruption):
    from sqlalchemy import text

    f = b17_env
    before = counts(f)
    if kind == "consent":
        digest = f.consent.evidence_artifact.content_hash
    else:
        with f.engine.connect() as conn:
            digest = conn.execute(
                text(
                    "SELECT a.content_hash FROM manuscript_versions m JOIN artifact_versions a ON a.id=m.document_artifact_version_id WHERE m.id=:id"
                ),
                {"id": f.package_command.manuscript_version_id},
            ).scalar_one()
    path = f.env[7]._path_for(digest)
    if corruption == "missing":
        path.unlink()
    else:
        path.write_bytes(b"corrupt retained bytes")
    with pytest.raises(ResearchBaseError) as exc:
        f.app.freeze_prepared_submission(f.actor, f.command)
    assert exc.value.code == (
        ErrorCode.FROZEN_REFERENCE_REQUIRED
        if corruption == "missing"
        else ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    )
    assert counts(f) == before


def test_consumed_grant_cannot_freeze_a_fresh_package(b17_env):
    from tests.integration.phase2.b17_fixtures import next_package

    f = b17_env
    f.app.freeze_prepared_submission(f.actor, f.command)
    fresh = next_package(f)
    before = counts(f)
    with pytest.raises(ResearchBaseError) as exc:
        fresh.app.freeze_prepared_submission(
            fresh.actor, replace(fresh.command, grant_id=f.command.grant_id)
        )
    assert exc.value.code == ErrorCode.GRANT_INVALID
    assert counts(f) == before


@pytest.mark.parametrize("change", ["omit", "add"])
def test_complete_sealed_multi_review_set_cannot_be_changed(b05_env, change):
    f = build(b05_env, extra_reviews=1)
    before = counts(f)
    reviews = (
        f.command.checked_review_ids[:1]
        if change == "omit"
        else f.command.checked_review_ids + (uuid4(),)
    )
    with pytest.raises(ResearchBaseError) as exc:
        f.app.freeze_prepared_submission(f.actor, replace(f.command, checked_review_ids=reviews))
    assert exc.value.code == ErrorCode.DECISION_BASIS_INVALID and counts(f) == before


def test_later_real_blocking_issue_denies_without_staling_maintenance(b17_env):
    from researchbase.application.internal_review import ReviewIssueRequest
    from tests.integration.phase2.test_b05_manuscript_review import create

    f = b17_env
    create(
        f.env, issues=(ReviewIssueRequest("BLOCKING", "OTHER", "Unresolved scientific blocker"),)
    )
    before = counts(f)
    with pytest.raises(ResearchBaseError) as exc:
        f.app.freeze_prepared_submission(f.actor, f.command)
    assert exc.value.code == ErrorCode.APPROVAL_GATE_FAILED and counts(f) == before
    assert (
        f.approval.get_grant(f.actor, f.command.project_id, f.command.grant_id).status == "ACTIVE"
    )


def test_current_scientific_invalidation_precedes_package_authority(b17_env):
    from sqlalchemy import text

    from researchbase.application.governance import (
        CreateImpactAssessmentCommand,
        GovernanceService,
        ProposedImpactTarget,
    )
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock

    f = b17_env
    with f.engine.connect() as conn:
        document = conn.execute(
            text("SELECT document_artifact_version_id FROM manuscript_versions WHERE id=:id"),
            {"id": f.package_command.manuscript_version_id},
        ).scalar_one()
    GovernanceService(f.env[4], SystemClock()).create_impact_assessment(
        CreateImpactAssessmentCommand(
            f.command.project_id,
            None,
            {"test": "Invalid document fact"},
            "invalid",
            (ProposedImpactTarget("artifact_version", document, "invalid"),),
            ExecutionContext(actor_id=f.actor.actor_id, request_id=uuid4(), client_type="test"),
        )
    )
    before = counts(f)
    with pytest.raises(ResearchBaseError) as exc:
        f.app.freeze_prepared_submission(f.actor, f.command)
    assert exc.value.code == ErrorCode.APPROVAL_TARGET_STALE and counts(f) == before


def test_missing_immutable_consent_condition_is_unusable_and_sql_lifecycle_agrees(b05_env):
    from researchbase.application.approval import EvaluateApprovalGrantCommand

    f = build(b05_env, condition=False)
    grant = f.approval.get_grant(f.actor, f.command.project_id, f.command.grant_id)
    assert (
        grant.status == "ACTIVE"
        and not grant.usable
        and grant.unusable_code == "APPROVAL_GATE_FAILED"
    )
    before = counts(f)
    with pytest.raises(ResearchBaseError) as exc:
        f.app.freeze_prepared_submission(f.actor, f.command)
    assert exc.value.code == ErrorCode.APPROVAL_GATE_FAILED and counts(f) == before
    terminal = f.approval.evaluate_approval_grant(
        f.actor, EvaluateApprovalGrantCommand(f.command.project_id, f.command.grant_id)
    )
    assert terminal.grant.status == "STALE" and not terminal.grant.usable


def test_every_current_author_is_captured_at_zero_based_authored_position(b05_env):
    from sqlalchemy import text

    from tests.integration.phase2.test_b14r_ready_approval import approver

    coauthor = approver(b05_env)
    f = build(b05_env, coauthors=(coauthor,))
    f.app.freeze_prepared_submission(f.actor, f.command)
    saved = f.app.get_prepared_submission(f.actor, f.query)
    captured = [item for item in saved.items if item.category == "AUTHOR_CONSENT"]
    assert [item.ordinal for item in captured] == [0, 1]
    with f.engine.connect() as conn:
        authors = [
            conn.execute(
                text("SELECT actor_id FROM author_consents WHERE id=:id"), {"id": item.target.id}
            ).scalar_one()
            for item in captured
        ]
    assert authors == [f.actor.actor_id, coauthor.actor_id]
    assert saved.current_validity == "VALID" and len(saved.consents) == 2
