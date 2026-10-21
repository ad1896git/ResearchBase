"""B14r issuance uses real freeze, entry, review and B11 judgment commands."""

# SQL assertions preserve the literal lock and guard protocol.
# ruff: noqa: E501

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.approval import (
    ApprovalService,
    DecideApprovalCommand,
    RequestApprovalCommand,
)
from researchbase.application.internal_review import ReviewIssueRequest
from researchbase.application.literature_evidence import LiteratureEvidenceService
from researchbase.application.phase2_identity import AssignProjectRole
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_approval import _actor
from tests.integration.phase2.test_b11_readiness_decision import (
    b04_env,
    b05_env,
    conclusion_env,
    create,
    phase2_database_url,
    record,
    seal,
)
from tests.integration.phase2.test_b14a_publication_entry import counts as publication_counts
from tests.integration.phase2.test_b14a_publication_entry import enter
from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service
from tests.integration.phase2.test_revision_action import decision_env, revision_env

_FIXTURES = (b04_env, b05_env, conclusion_env, phase2_database_url, decision_env, revision_env)
pytestmark = pytest.mark.integration


def service(env):
    return ApprovalService(env[4], env[9], LiteratureEvidenceService(env[4], env[9], env[7]))


def approver(env):
    actor = _actor((None, None, env[3], env[10]))
    identity, _, _ = identity_service(env[5].url.render_as_string(hide_password=False))
    identity.assign_project_role(
        AssignProjectRole(
            env[3],
            env[1].project_id,
            actor.actor_id,
            "APPROVER",
            "TEST independent approver",
            uuid4(),
        )
    )
    return actor


def setup(env, *, entry=True):
    seal(env)
    review = create(env)
    basis = record(env)
    if entry:
        enter(env)
    cmd = RequestApprovalCommand(
        uuid4(),
        env[1].project_id,
        None,
        basis.id,
        (review.id,),
        approval_purpose="READY_FOR_SUBMISSION",
        manuscript_version_id=env[1].manuscript_version_id,
    )
    return service(env), cmd, approver(env)


def decide(cmd, outcome="APPROVE", **changes):
    return DecideApprovalCommand(
        uuid4(), cmd.project_id, cmd.id, outcome, "Independent permission", **changes
    )


def counts(env):
    with env[5].connect() as conn:
        return tuple(
            conn.execute(text(f"SELECT count(*) FROM {t}")).scalar_one()
            for t in (
                "approval_requests",
                "approval_request_reviews",
                "approval_request_events",
                "approval_decisions",
                "approval_grants",
                "approval_grant_events",
            )
        )


@pytest.mark.parametrize("outcome", ["APPROVE", "APPROVE_WITH_CONDITIONS", "REJECT"])
def test_exact_atomic_permission_without_effect(b05_env, outcome):
    env = b05_env
    app, cmd, actor = setup(env)
    before = publication_counts(env)
    request = app.request_approval(env[2], cmd)
    assert (
        request.status == "PENDING" and request.manuscript_version_id == cmd.manuscript_version_id
    )
    with env[5].connect() as conn:
        expiry = conn.execute(text("SELECT clock_timestamp()+interval '1 hour'")).scalar_one()
    command = decide(
        cmd, outcome, **({"valid_until": expiry} if outcome == "APPROVE_WITH_CONDITIONS" else {})
    )
    result = app.decide_approval(actor, command)
    assert not result.requires_current_author_consent
    assert counts(env) == (1, 1, 2, 1, int(outcome != "REJECT"), int(outcome != "REJECT"))
    if outcome == "REJECT":
        assert result.grant is None
    else:
        grant = result.grant
        assert grant is not None and grant.status == "ACTIVE" and grant.usable
        assert grant.unusable_code is None
        assert grant.allowed_command == "transition_publication_ready" and grant.max_uses == 1
        assert (
            grant.purpose == "READY_FOR_SUBMISSION"
            and grant.manuscript_version_id == cmd.manuscript_version_id
        )
        assert grant.target_content_hash == request.target_content_hash
        assert grant.valid_until == (
            expiry
            if outcome == "APPROVE_WITH_CONDITIONS"
            else result.decided_at + timedelta(hours=720)
        )
    assert publication_counts(env) == before
    with env[5].connect() as conn:
        for table in (
            "approval_grant_consumptions",
            "authorship_snapshots",
            "contribution_records",
        ):
            assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0


def test_prior_drafting_basis_becomes_eligible_only_after_real_entry(b05_env):
    env = b05_env
    app, cmd, _ = setup(env, entry=False)
    with pytest.raises(ResearchBaseError) as error:
        app.request_approval(env[2], cmd)
    assert error.value.code == ErrorCode.APPROVAL_GATE_FAILED and counts(env) == (0,) * 6
    enter(env)
    assert app.request_approval(env[2], cmd).status == "PENDING"


@pytest.mark.parametrize(
    "case", ["basis", "target", "purpose", "missing_review", "extra_review", "successor"]
)
def test_basis_substitutions_roll_back(b05_env, case):
    env = b05_env
    app, cmd, _ = setup(env)
    changes = {
        "basis": {"basis_decision_id": uuid4()},
        "target": {"manuscript_version_id": uuid4()},
        "purpose": {"approval_purpose": "PREPARE_SUBMISSION"},
        "missing_review": {"review_ids": (uuid4(),)},
        "extra_review": {"review_ids": cmd.review_ids + (uuid4(),)},
        "successor": {"prior_rejected_request_id": uuid4(), "reconsideration_decision_id": uuid4()},
    }
    with pytest.raises(ResearchBaseError) as error:
        app.request_approval(env[2], replace(cmd, **changes[case]))
    assert error.value.code == (
        ErrorCode.NOT_FOUND if case == "target" else ErrorCode.DECISION_BASIS_INVALID
    )
    assert counts(env) == (0,) * 6


@pytest.mark.parametrize(
    "recommendation", ["ACCEPT", "MINOR_REVISION", "MAJOR_REVISION", "REJECT", "UNCERTAIN"]
)
def test_later_reviews_are_validated_without_refreshing_saved_basis(b05_env, recommendation):
    env = b05_env
    app, cmd, actor = setup(env)
    later = create(env, recommendation=recommendation)
    request = app.request_approval(env[2], cmd)
    assert tuple(r.id for r in request.reviews) == cmd.review_ids
    assert later.id not in cmd.review_ids
    assert app.decide_approval(actor, decide(cmd)).grant is not None


def test_later_blocker_denies_decision_but_history_remains_readable(b05_env):
    env = b05_env
    app, cmd, actor = setup(env)
    saved = app.request_approval(env[2], cmd)
    create(env, issues=(ReviewIssueRequest("BLOCKING", "WRITING", "Unresolved"),))
    before = counts(env)
    with pytest.raises(ResearchBaseError) as error:
        app.decide_approval(actor, decide(cmd))
    assert error.value.code == ErrorCode.APPROVAL_GATE_FAILED
    assert counts(env) == before and app.get_request(env[2], cmd.project_id, cmd.id) == saved


@pytest.mark.parametrize(
    "case", ["requester", "reviewer", "owner_only", "consent", "expiry", "rationale"]
)
def test_independent_finite_human_permission(b05_env, case):
    env = b05_env
    app, cmd, actor = setup(env)
    if case == "reviewer":
        with pytest.raises(ResearchBaseError) as error:
            app.request_approval(env[3], cmd)
        assert error.value.code == ErrorCode.CONFLICT_OF_INTEREST
        return
    app.request_approval(env[2], cmd)
    if case in {"requester", "owner_only"}:
        actor = env[2]
    with env[5].connect() as conn:
        now = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
    changes = {
        "consent": {
            "valid_until": now + timedelta(hours=1),
            "requires_current_author_consent": True,
        },
        "expiry": {"valid_until": now + timedelta(hours=721)},
        "rationale": {"rationale": "x" * 16385},
    }.get(case, {})
    command = decide(cmd)
    if case in {"consent", "expiry"}:
        changes["decision"] = "APPROVE_WITH_CONDITIONS"
    with pytest.raises(ResearchBaseError) as error:
        app.decide_approval(actor, replace(command, **changes))
    assert error.value.code in {
        ErrorCode.FORBIDDEN,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.CONFLICT_OF_INTEREST,
    }
    assert counts(env) == (1, 1, 1, 0, 0, 0)


@pytest.mark.parametrize("overlap", ["requester_author", "basis_decider_reviewer"])
def test_approver_role_does_not_waive_independence(b05_env, overlap):
    env = b05_env
    app, cmd, _ = setup(env)
    actor = env[2] if overlap == "requester_author" else env[3]
    identity, _, _ = identity_service(env[5].url.render_as_string(hide_password=False))
    identity.assign_project_role(
        AssignProjectRole(
            actor, cmd.project_id, actor.actor_id, "APPROVER", "Overlap test", uuid4()
        )
    )
    app.request_approval(env[2], cmd)
    with pytest.raises(ResearchBaseError) as error:
        app.decide_approval(actor, decide(cmd))
    assert error.value.code == ErrorCode.CONFLICT_OF_INTEREST
    assert counts(env) == (1, 1, 1, 0, 0, 0)


@pytest.mark.parametrize("phase", ["request", "decision"])
def test_cas_byte_corruption_never_yields_permission(b05_env, phase):
    env = b05_env
    app, cmd, actor = setup(env)
    if phase == "decision":
        app.request_approval(env[2], cmd)
    before = counts(env)
    with env[5].connect() as conn:
        digest = conn.execute(
            text(
                "SELECT a.content_hash FROM artifact_versions a JOIN manuscript_versions m ON m.document_artifact_version_id=a.id WHERE m.id=:id"
            ),
            {"id": cmd.manuscript_version_id},
        ).scalar_one()
    env[7]._path_for(digest).write_bytes(b"tampered document")
    with pytest.raises(ResearchBaseError) as error:
        app.request_approval(env[2], cmd) if phase == "request" else app.decide_approval(
            actor, decide(cmd)
        )
    assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert counts(env) == before


@pytest.mark.parametrize(
    "count,code", [(100, ErrorCode.DECISION_BASIS_INVALID), (101, ErrorCode.VALIDATION_ERROR)]
)
def test_review_admission_ceiling_without_truncation(b05_env, count, code):
    env = b05_env
    app, cmd, _ = setup(env)
    command = replace(cmd, review_ids=tuple(uuid4() for _ in range(count)))
    with pytest.raises(ResearchBaseError) as error:
        app.request_approval(env[2], command)
    assert error.value.code == code and len(command.review_ids) == count
    assert counts(env) == (0,) * 6


def test_saved_101_review_b11_basis_cannot_be_truncated_for_approval(b05_env):
    env = b05_env
    seal(env)
    reviews = [create(env, summary=f"Review {i}") for i in range(101)]
    basis = record(env)
    enter(env)
    app = service(env)
    cmd = RequestApprovalCommand(
        uuid4(),
        env[1].project_id,
        None,
        basis.id,
        tuple(r.id for r in reviews[:100]),
        approval_purpose="READY_FOR_SUBMISSION",
        manuscript_version_id=env[1].manuscript_version_id,
    )
    with pytest.raises(ResearchBaseError) as error:
        app.request_approval(env[2], cmd)
    assert error.value.code == ErrorCode.DECISION_BASIS_INVALID
    assert counts(env) == (0,) * 6


@pytest.mark.parametrize("state", ["STALE", "INVALID"])
def test_current_transitive_invalidity_denies_write_keeps_history(b05_env, state):
    from researchbase.application.governance import (
        CreateAuditFindingCommand,
        CreateImpactAssessmentCommand,
        GovernanceService,
        ProposedImpactTarget,
    )
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock
    from tests.integration.phase2.test_b11_readiness_decision import place_claim

    env = b05_env
    place_claim(env)
    app, cmd, actor = setup(env)
    saved = app.request_approval(env[2], cmd)
    context = ExecutionContext(actor_id=env[2].actor_id, request_id=uuid4(), client_type="test")
    governance = GovernanceService(env[4], SystemClock())
    finding = governance.create_audit_finding(
        CreateAuditFindingCommand(
            cmd.project_id,
            "code_bug",
            "major",
            "Later problem",
            "Recheck",
            "claim_version",
            env[8],
            context,
        )
    )
    governance.create_impact_assessment(
        CreateImpactAssessmentCommand(
            cmd.project_id,
            finding.id,
            {"basis": "TEST"},
            state.lower(),
            (ProposedImpactTarget("claim_version", env[8], state.lower()),),
            context,
        )
    )
    with pytest.raises(ResearchBaseError) as error:
        app.decide_approval(actor, decide(cmd))
    assert error.value.code == ErrorCode.APPROVAL_TARGET_STALE
    assert app.get_request(env[2], cmd.project_id, cmd.id) == saved
    assert counts(env) == (1, 1, 1, 0, 0, 0)


def another_target(env):
    """A second real Publication/manuscript, using the same project and CAS."""
    from researchbase.application.manuscript_freeze import GetManuscriptVersionQuery
    from researchbase.application.publication import PublicationService
    from tests.integration.phase2.test_pr2_10_binding_contract import _artifact

    pub = PublicationService(env[4], env[9], env[7])
    document = _artifact(
        env[4], env[7], env[2], env[1].project_id, b"Another manuscript", "manuscript"
    )
    parent = pub.create_publication(env[2], env[1].project_id, "PAPER", "Another study", uuid4())
    draft = pub.create_draft(
        env[2], env[1].project_id, parent.id, document, "Another study", None, "INITIAL", uuid4()
    )
    other = (env[0], GetManuscriptVersionQuery(env[1].project_id, parent.id, draft.id), *env[2:])
    seal(other)
    review = create(other)
    basis = record(other)
    enter(other)
    cmd = RequestApprovalCommand(
        uuid4(),
        env[1].project_id,
        None,
        basis.id,
        (review.id,),
        approval_purpose="READY_FOR_SUBMISSION",
        manuscript_version_id=draft.id,
    )
    return other, cmd


def test_newer_exact_target_stales_only_ready_grants_and_old_pending_denies(b05_env):
    env = b05_env
    app, first, actor = setup(env)
    app.request_approval(env[2], first)
    granted = app.decide_approval(actor, decide(first))
    assert granted.grant
    old_pending = replace(first, id=uuid4())
    app.request_approval(env[2], old_pending)
    _, second = another_target(env)
    app.request_approval(env[2], second)
    assert app.get_grant(env[2], first.project_id, granted.grant.id).status == "STALE"
    with pytest.raises(ResearchBaseError) as error:
        app.decide_approval(actor, decide(old_pending))
    assert error.value.code == ErrorCode.APPROVAL_TARGET_STALE
    app.decide_approval(actor, decide(second, "REJECT"))
    with pytest.raises(ResearchBaseError) as error:
        app.decide_approval(actor, decide(old_pending))
    assert error.value.code == ErrorCode.REJECTION_RECONSIDERATION_REQUIRED


def test_later_reviewer_is_not_silently_added_to_required_independence_set(b05_env):
    env = b05_env
    app, cmd, actor = setup(env)
    create(env, principal=actor, recommendation="REJECT")
    saved = app.request_approval(env[2], cmd)
    assert tuple(r.id for r in saved.reviews) == cmd.review_ids
    assert app.decide_approval(actor, decide(cmd)).grant is not None


def test_unsupported_ready_successor_keeps_basis_error_even_with_rejection_fence(b05_env):
    env = b05_env
    app, cmd, actor = setup(env)
    app.request_approval(env[2], cmd)
    app.decide_approval(actor, decide(cmd, "REJECT"))
    before = counts(env)
    unsupported = replace(
        cmd, id=uuid4(), prior_rejected_request_id=cmd.id, reconsideration_decision_id=uuid4()
    )
    with pytest.raises(ResearchBaseError) as error:
        app.request_approval(env[2], unsupported)
    assert error.value.code == ErrorCode.DECISION_BASIS_INVALID
    assert counts(env) == before
