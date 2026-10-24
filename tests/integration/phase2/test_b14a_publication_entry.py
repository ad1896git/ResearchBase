"""B14a real Application admission and atomic effect on PostgreSQL."""

# SQL assertions retain the exact reviewed lock/guard literals.
# ruff: noqa: E501

from dataclasses import replace
from typing import Any, cast
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.internal_review import ReviewIssueRequest
from researchbase.application.publication import (
    PublicationService,
    TransitionPublicationInternalReviewCommand,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_b05_manuscript_review import (
    b04_env as b04_env,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    b05_env as b05_env,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    conclusion_env as conclusion_env,
)
from tests.integration.phase2.test_b05_manuscript_review import create, seal
from tests.integration.phase2.test_b05_manuscript_review import (
    phase2_database_url as phase2_database_url,
)
from tests.integration.phase2.test_revision_action import decision_env, revision_env

_FIXTURES = (b04_env, b05_env, conclusion_env, phase2_database_url, decision_env, revision_env)
pytestmark = pytest.mark.integration


def service(env):
    return PublicationService(env[4], env[9], env[7])


def command(env, **changes):
    with env[5].connect() as conn:
        digest = conn.execute(
            text("SELECT content_hash FROM manuscript_versions WHERE id=:id"),
            {"id": env[1].manuscript_version_id},
        ).scalar_one()
    return cast(Any, TransitionPublicationInternalReviewCommand)(
        **(
            dict(
                id=uuid4(),
                project_id=env[1].project_id,
                publication_id=env[1].publication_id,
                manuscript_version_id=env[1].manuscript_version_id,
                expected_content_hash=digest or "0" * 64,
            )
            | changes
        )
    )


def enter(env, cmd=None, principal=None):
    return service(env).transition_publication_internal_review(
        principal or env[2], cmd or command(env)
    )


def counts(env):
    with env[5].connect() as conn:
        p = conn.execute(
            text(
                "SELECT lifecycle_status,row_version,current_manuscript_version_id FROM publications WHERE id=:id"
            ),
            {"id": env[1].publication_id},
        ).one()
        n = conn.execute(
            text("SELECT count(*) FROM publication_lifecycle_events WHERE publication_id=:id"),
            {"id": env[1].publication_id},
        ).scalar_one()
        return tuple(p), n


def test_zero_reviews_author_may_enter_and_atomic_exact_result(b05_env):
    env = b05_env
    frozen = seal(env)
    before = counts(env)
    cmd = command(env)
    result = enter(env, cmd)
    assert result.id == cmd.id and result.actor_id == env[2].actor_id
    assert result.manuscript_content_hash == frozen.content_hash
    assert result.prior_status == "DRAFTING" and result.new_status == "INTERNAL_REVIEW"
    assert counts(env) == (("INTERNAL_REVIEW", before[0][1] + 1, cmd.manuscript_version_id), 2)
    with env[5].connect() as conn:
        event = conn.execute(
            text(
                "SELECT manuscript_version_id,basis_decision_id,basis_grant_consumption_id FROM publication_lifecycle_events WHERE id=:id"
            ),
            {"id": cmd.id},
        ).one()
        assert tuple(event) == (cmd.manuscript_version_id, None, None)
        assert (
            conn.execute(
                text("SELECT content_hash FROM manuscript_versions WHERE id=:id"),
                {"id": cmd.manuscript_version_id},
            ).scalar_one()
            == frozen.content_hash
        )
    assert enter(env, cmd) == result


@pytest.mark.parametrize(
    "recommendation", ["ACCEPT", "MINOR_REVISION", "MAJOR_REVISION", "REJECT", "UNCERTAIN"]
)
@pytest.mark.parametrize("severity", [None, "MINOR", "MAJOR", "BLOCKING"])
def test_recommendations_and_manuscript_issues(b05_env, recommendation, severity):
    env = b05_env
    seal(env)
    create(
        env,
        recommendation=recommendation,
        issues=() if severity is None else (ReviewIssueRequest(severity, "WRITING", "Concern"),),
    )
    before = counts(env)
    if severity == "BLOCKING":
        with pytest.raises(ResearchBaseError) as error:
            enter(env)
        assert error.value.code == ErrorCode.APPROVAL_GATE_FAILED
        assert counts(env) == before
    else:
        assert enter(env).new_status == "INTERNAL_REVIEW"


@pytest.mark.parametrize(
    "case,code",
    [
        ("unsealed", ErrorCode.FROZEN_REFERENCE_REQUIRED),
        ("hash", ErrorCode.CONCURRENT_MODIFICATION),
        ("missing_publication", ErrorCode.NOT_FOUND),
        ("missing_manuscript", ErrorCode.NOT_FOUND),
        ("foreign_project", ErrorCode.FORBIDDEN),
        ("credential", ErrorCode.FORBIDDEN),
        ("principal", ErrorCode.AUTHENTICATION_REQUIRED),
    ],
)
def test_first_use_error_order_and_no_effect(b05_env, case, code):
    env = b05_env
    if case != "unsealed":
        seal(env)
    cmd = command(env)
    principal = env[2]
    if case == "hash":
        cmd = replace(cmd, expected_content_hash="0" * 64)
    if case == "missing_publication":
        cmd = replace(cmd, publication_id=uuid4())
    if case == "missing_manuscript":
        cmd = replace(cmd, manuscript_version_id=uuid4())
    if case == "foreign_project":
        cmd = replace(cmd, project_id=uuid4())
    if case == "credential":
        principal = replace(principal, credential_id=str(uuid4()))
    if case == "principal":
        principal = object()
    before = counts(env)
    with pytest.raises(ResearchBaseError) as error:
        enter(env, cmd, principal)
    assert error.value.code == code
    assert counts(env) == before


def test_different_id_is_not_reentry(b05_env):
    seal(b05_env)
    enter(b05_env)
    before = counts(b05_env)
    with pytest.raises(ResearchBaseError) as error:
        enter(b05_env)
    assert error.value.code == ErrorCode.INVALID_STATE_TRANSITION
    assert counts(b05_env) == before


@pytest.mark.parametrize("reachable", [True, False])
def test_exact_reachable_claim_blocker_and_unrelated_ignored(b05_env, reachable):
    from tests.integration.phase2.test_b11_readiness_decision import place_claim

    env = b05_env
    if reachable:
        place_claim(env)
    seal(env)
    env[0].create(
        env[3],
        env[1].project_id,
        "CLAIM_VERSION",
        env[8],
        "SCIENTIFIC",
        "REJECT",
        "Upstream concern",
        (ReviewIssueRequest("BLOCKING", "OTHER", "Concern"),),
        uuid4(),
    )
    if reachable:
        with pytest.raises(ResearchBaseError) as error:
            enter(env)
        assert error.value.code == ErrorCode.APPROVAL_GATE_FAILED
    else:
        assert enter(env).new_status == "INTERNAL_REVIEW"


def test_document_artifact_review_is_verified_before_blocker(b05_env):
    from researchbase.domain.internal_review import review_material
    from researchbase.foundation.hashing import sha256_canonical_json

    env = b05_env
    seal(env)
    with env[5].begin() as conn:
        target, digest = conn.execute(
            text(
                "SELECT v.id,v.content_hash FROM manuscript_versions m JOIN artifact_versions v ON v.id=m.document_artifact_version_id WHERE m.id=:id"
            ),
            {"id": env[1].manuscript_version_id},
        ).one()
        rid = uuid4()
        hashed = str(
            sha256_canonical_json(
                review_material(
                    env[1].project_id,
                    "ArtifactVersion",
                    target,
                    digest,
                    env[3].actor_id,
                    "SCIENTIFIC",
                    "REJECT",
                    "Upstream",
                )
            )
        )
        conn.execute(
            text(
                "INSERT INTO internal_review_records(id,project_id,artifact_version_id,target_content_hash,reviewer_actor_id,review_type,recommendation,summary,created_at,content_hash,hash_scheme) VALUES (:id,:project,:target,:digest,:actor,'SCIENTIFIC','REJECT','Upstream',clock_timestamp(),:hash,'sha256-cjson-v1')"
            ),
            dict(
                id=rid,
                project=env[1].project_id,
                target=target,
                digest=digest,
                actor=env[3].actor_id,
                hash=hashed,
            ),
        )
        conn.execute(
            text(
                "INSERT INTO review_issues(id,review_record_id,severity,issue_type,description,status,created_at,ordinal) VALUES (:id,:review,'BLOCKING','OTHER','Concern','OPEN',clock_timestamp(),0)"
            ),
            dict(id=uuid4(), review=rid),
        )
    with pytest.raises(ResearchBaseError) as error:
        enter(env)
    assert error.value.code == ErrorCode.APPROVAL_GATE_FAILED


@pytest.mark.parametrize("at_entry", [False, True])
def test_invalid_science_denies_admission_but_preserves_history(b05_env, at_entry):
    from researchbase.application.governance import (
        CreateAuditFindingCommand,
        CreateImpactAssessmentCommand,
        GovernanceService,
        ProposedImpactTarget,
    )
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock
    from tests.integration.phase2.test_b11_readiness_decision import place_claim
    from tests.integration.phase2.test_b14a_entry_replay import read

    env = b05_env
    place_claim(env)
    seal(env)
    cmd = command(env)
    saved = enter(env, cmd) if at_entry else None
    context = ExecutionContext(actor_id=env[2].actor_id, request_id=uuid4(), client_type="test")
    governance = GovernanceService(env[4], SystemClock())
    finding = governance.create_audit_finding(
        CreateAuditFindingCommand(
            env[1].project_id,
            "code_bug",
            "major",
            "Problem",
            "Recheck",
            "claim_version",
            env[8],
            context,
        )
    )
    governance.create_impact_assessment(
        CreateImpactAssessmentCommand(
            env[1].project_id,
            finding.id,
            {"basis": "TEST ONLY"},
            "invalid",
            (ProposedImpactTarget("claim_version", env[8], "invalid"),),
            context,
        )
    )
    if saved:
        assert enter(env, cmd) == saved and read(env, saved.id) == saved
    else:
        with pytest.raises(ResearchBaseError) as error:
            enter(env, cmd)
        assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_missing_bytes_deny_admission(b05_env, monkeypatch):
    env = b05_env
    seal(env)
    before = counts(env)
    monkeypatch.setattr(type(env[7]), "verify", lambda *args: False)
    with pytest.raises(ResearchBaseError) as error:
        enter(env)
    assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert counts(env) == before


@pytest.mark.parametrize("actor_type", ["HUMAN", "AGENT"])
def test_shared_verified_caller_boundary(b05_env, actor_type):
    from tests.integration.phase2.test_pr2_00_ownership import _add_owner

    env = b05_env
    seal(env)
    aid = uuid4()
    with env[5].begin() as conn:
        at = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        conn.execute(
            text(
                "INSERT INTO actors(id,actor_type,display_name,created_at) VALUES (:id,:kind,'Entry caller',:at)"
            ),
            dict(id=aid, kind=actor_type, at=at),
        )
        if actor_type == "HUMAN":
            _add_owner(
                conn,
                actor_id=aid,
                project_id=env[1].project_id,
                now=at,
                event_kind="ACTIVATED",
                request_id=uuid4(),
                create_actor=False,
            )
    principal = replace(
        env[3], actor_id=aid, subject_value=str(aid.int), credential_id=f"uid:{aid.int}"
    )
    env[9].principals[aid] = principal
    if actor_type == "HUMAN":
        assert enter(env, principal=principal).actor_id == aid
    else:
        # Contract 16 reserves Agent enrollment for a reviewed adapter.
        with pytest.raises(ResearchBaseError) as error:
            enter(env, principal=principal)
        assert error.value.code == ErrorCode.FORBIDDEN


@pytest.mark.parametrize("damage", ["review_hash", "issue_history"])
def test_corrupt_review_or_issue_history_is_provenance_error(b05_env, monkeypatch, damage):
    from researchbase.persistence.decision_repository import SqlAlchemyDecisionRepository
    from researchbase.persistence.internal_review_repository import (
        SqlAlchemyInternalReviewRepository,
    )

    env = b05_env
    seal(env)
    create(env, issues=(ReviewIssueRequest("MINOR", "OTHER", "Concern"),))
    if damage == "review_hash":
        original = SqlAlchemyDecisionRepository.applicable_manuscript_reviews

        def changed(self, *args):
            return [{**r, "content_hash": "0" * 64} for r in original(self, *args)]

        monkeypatch.setattr(SqlAlchemyDecisionRepository, "applicable_manuscript_reviews", changed)
    else:
        original = SqlAlchemyInternalReviewRepository.issue_events

        def changed(self, *args):
            return [{**r, "new_status": "DISMISSED"} for r in original(self, *args)]

        monkeypatch.setattr(SqlAlchemyInternalReviewRepository, "issue_events", changed)
    with pytest.raises(ResearchBaseError) as error:
        enter(env)
    assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_verified_b08_terminal_history_is_not_a_blocker(b05_env, revision_env):
    from researchbase.application.manuscript_placement import ClaimPlacementService
    from tests.integration.phase2.b08_support import disposition_case

    env = b05_env
    reviews, actor, cmd, base, _ = disposition_case(revision_env, dismiss=True)
    reviews.record_issue_disposition(actor, cmd)
    conclusion = revision_env[2][3].version_id
    assert base[5] == env[1].project_id
    ClaimPlacementService(env[4], env[9]).add(
        env[2],
        env[1].project_id,
        env[1].publication_id,
        env[1].manuscript_version_id,
        None,
        conclusion,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "p1"},
        "SUPPORTED",
        0,
        uuid4(),
    )
    seal(env)
    assert enter(env).new_status == "INTERNAL_REVIEW"


def test_real_wrong_parent_cannot_replace_explicit_target(b05_env):
    env = b05_env
    seal(env)
    other = service(env).create_publication(
        env[2], env[1].project_id, "PAPER", "Other study", uuid4()
    )
    cmd = command(env, publication_id=other.id)
    before = counts(env)
    with pytest.raises(ResearchBaseError) as error:
        enter(env, cmd)
    assert error.value.code == ErrorCode.FORBIDDEN
    assert counts(env) == before
