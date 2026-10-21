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


def test_prepare_blocker_maintenance_persists_stale_and_event(b17_env):
    from sqlalchemy import text

    from researchbase.application.approval import EvaluateApprovalGrantCommand
    from researchbase.application.internal_review import ReviewIssueRequest
    from tests.integration.phase2.test_b05_manuscript_review import create

    f = b17_env
    create(f.env, issues=(ReviewIssueRequest("BLOCKING", "WRITING", "New PREPARE blocker"),))
    before = counts(f)
    result = f.approval.evaluate_approval_grant(
        f.actor, EvaluateApprovalGrantCommand(f.command.project_id, f.command.grant_id)
    )
    assert result.grant.status == "STALE"
    assert result.evaluation.unusable_code == ErrorCode.GRANT_STALE.value
    assert f.approval.get_grant(f.actor, f.command.project_id, f.command.grant_id).status == "STALE"
    with f.engine.connect() as conn:
        assert conn.execute(
            text(
                "SELECT prior_status,new_status FROM approval_grant_events "
                "WHERE grant_id=:id ORDER BY occurred_at,id"
            ),
            {"id": f.command.grant_id},
        ).all() == [(None, "ACTIVE"), ("ACTIVE", "STALE")]
    after = counts(f)
    assert after == (*before[:4], before[4] + 1, before[5])


def test_b32_freeze_preserves_ready_history_and_local_receipt(b17_env):
    from sqlalchemy import text

    from researchbase.application.publication import PublicationService

    f = b17_env
    with f.engine.connect() as conn:
        ready_history = conn.execute(
            text("SELECT * FROM publication_lifecycle_events ORDER BY id")
        ).all()
    ready_receipt = f.approval.get_grant_consumption(
        f.actor,
        f.command.project_id,
        f.ready_command.command_key,
    )
    assert f.command.grant_id != f.ready_command.grant_id
    receipt = f.app.freeze_prepared_submission(f.actor, f.command)
    assert receipt.command == "FREEZE_PREPARED_SUBMISSION"
    assert receipt.result_publication_id is None
    assert receipt.result_scientific_conclusion_version_id is None
    assert receipt.result_prepared_submission_version_id == f.command.result_id
    with f.engine.connect() as conn:
        assert (
            conn.execute(text("SELECT * FROM publication_lifecycle_events ORDER BY id")).all()
            == ready_history
        )
        assert conn.execute(
            text(
                "SELECT c.id, c.grant_id, p.status FROM prepared_submission_versions p "
                "JOIN approval_grant_consumptions c ON c.result_prepared_submission_version_id=p.id "
                "WHERE p.id=:id"
            ),
            {"id": f.command.result_id},
        ).one() == (receipt.id, f.command.grant_id, "FROZEN")
        assert (
            conn.execute(
                text("SELECT lifecycle_status FROM publications WHERE id=:id"),
                {"id": f.package_command.publication_id},
            ).scalar_one()
            == "READY"
        )
    assert (
        f.approval.get_grant_consumption(
            f.actor,
            f.command.project_id,
            f.ready_command.command_key,
        )
        == ready_receipt
    )
    before = counts(f)
    # A saved freeze key cannot become a different command through another owner.
    app = PublicationService(f.env[4], f.env[9], f.env[7])
    with pytest.raises(ResearchBaseError) as caught:
        app.transition_publication_ready(
            f.actor,
            replace(f.ready_command, command_key=f.command.command_key),
        )
    assert caught.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert counts(f) == before


def test_b32_exact_reads_and_completed_freeze_are_readonly_snapshots(b17_env):
    from sqlalchemy import event

    f = b17_env
    receipt = f.app.freeze_prepared_submission(f.actor, f.command)
    before = counts(f)
    observed = []

    def capture(conn, cursor, sql, params, context, many):
        observed.append(
            (sql.upper(), cursor.connection.isolation_level.name, cursor.connection.read_only)
        )

    event.listen(f.engine, "before_cursor_execute", capture)
    try:
        assert f.app.freeze_prepared_submission(f.actor, f.command) == receipt
        f.app.get_prepared_submission(f.actor, f.query)
        f.app.get_prepared_submission_history(f.actor, f.query)
        f.app.preview_prepared_submission(f.actor, f.query)
        assert (
            f.approval.get_grant_consumption(
                f.actor,
                f.command.project_id,
                f.command.command_key,
            )
            == receipt
        )
    finally:
        event.remove(f.engine, "before_cursor_execute", capture)
    assert observed and all(
        level == "REPEATABLE_READ" and readonly for _, level, readonly in observed
    )
    assert not any(
        token in sql
        for sql, _, _ in observed
        for token in (
            "LOCK TABLE",
            "PG_ADVISORY",
            "FOR UPDATE",
            "FOR SHARE",
            "INSERT ",
            "UPDATE ",
            "DELETE ",
            "SET CONSTRAINTS",
        )
    )
    assert counts(f) == before
