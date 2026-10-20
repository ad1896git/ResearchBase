"""B11 uses Application-frozen manuscripts in disposable PostgreSQL databases."""

# SQL and independent literal hash vectors preserve contract spelling.
# ruff: noqa: E501

from dataclasses import replace
from typing import Any, cast
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.decision import (
    DecisionService,
    GetReadyForSubmissionDecisionQuery,
    RecordReadyForSubmissionDecisionCommand,
)
from researchbase.application.internal_review import ReviewIssueRequest
from researchbase.application.literature_evidence import LiteratureEvidenceService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_b05_manuscript_review import (
    b04_env as _b04_env,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    b05_env as _b05_env,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    conclusion_env as _conclusion_env,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    create,
    seal,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    phase2_database_url as _phase2_database_url,
)
from tests.integration.phase2.test_revision_action import decision_env, revision_env

_ADDITIONAL_FIXTURES = (decision_env, revision_env)
b04_env = _b04_env
b05_env = _b05_env
conclusion_env = _conclusion_env
phase2_database_url = _phase2_database_url
pytestmark = pytest.mark.integration


def service(env):
    return DecisionService(
        env[4], env[9], LiteratureEvidenceService(env[4], env[9], env[7]), env[7]
    )


def command(env, **changes):
    return cast(Any, RecordReadyForSubmissionDecisionCommand)(
        **(
            dict(
                id=uuid4(),
                project_id=env[1].project_id,
                manuscript_version_id=env[1].manuscript_version_id,
                question="Ready?",
                rationale="Independent judgment",
            )
            | changes
        )
    )


def record(env, cmd=None, principal=None):
    return service(env).record_ready_for_submission_decision(
        principal or env[3], cmd or command(env)
    )


def read(env, identity, principal=None):
    return service(env).get_ready_for_submission_decision(
        principal or env[3], GetReadyForSubmissionDecisionQuery(env[1].project_id, identity)
    )


def test_complete_adverse_reviews_and_no_lifecycle_effect(b05_env):
    env = b05_env
    seal(env)
    reviews = [create(env, recommendation=r) for r in ("REJECT", "UNCERTAIN", "ACCEPT")]
    result = record(env)
    assert result.current_validity == "VALID" and not result.current_blocking_issue_ids
    assert [r.id for r in result.basis[:-1]] == sorted([r.id for r in reviews], key=str)
    assert result.basis[-1].type == "ManuscriptVersion"
    assert result.evaluated_at.tzinfo is not None
    with env[5].connect() as conn:
        assert (
            conn.execute(
                text("SELECT lifecycle_status FROM publications WHERE id=:id"),
                {"id": env[1].publication_id},
            ).scalar_one()
            == "DRAFTING"
        )
        for table in (
            "approval_requests",
            "approval_decisions",
            "approval_grants",
            "review_issues",
        ):
            assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0
    assert read(env, result.id).content_hash == result.content_hash


@pytest.mark.parametrize(
    "case,expected",
    [
        ("draft", ErrorCode.FROZEN_REFERENCE_REQUIRED),
        ("missing", ErrorCode.NOT_FOUND),
        ("author", ErrorCode.CONFLICT_OF_INTEREST),
        ("no_reviews", ErrorCode.DECISION_BASIS_INVALID),
        ("blocker", ErrorCode.DECISION_BASIS_INVALID),
        ("credential", ErrorCode.FORBIDDEN),
    ],
)
def test_creation_denials(b05_env, case, expected):
    env = b05_env
    if case != "draft":
        seal(env)
    if case not in ("draft", "no_reviews"):
        create(
            env,
            issues=(ReviewIssueRequest("BLOCKING", "OTHER", "Concern"),)
            if case == "blocker"
            else (),
        )
    cmd = command(env, manuscript_version_id=uuid4()) if case == "missing" else command(env)
    principal = (
        env[2]
        if case == "author"
        else replace(env[3], credential_id="bad")
        if case == "credential"
        else env[3]
    )
    with pytest.raises(ResearchBaseError) as exc:
        record(env, cmd, principal)
    assert exc.value.code == expected
    with env[5].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM decision_records")).scalar_one() == 0


@pytest.mark.parametrize("severity", ["INFO", "MINOR", "MAJOR"])
def test_nonblocking_does_not_veto(b05_env, severity):
    seal(b05_env)
    create(b05_env, issues=(ReviewIssueRequest(severity, "OTHER", "Concern"),))
    assert not record(b05_env).current_blocking_issue_ids


def place_claim(env):
    from researchbase.application.manuscript_placement import ClaimPlacementService

    ClaimPlacementService(env[4], env[9]).add(
        env[2],
        env[1].project_id,
        env[1].publication_id,
        env[1].manuscript_version_id,
        env[8],
        None,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "p1"},
        "SUPPORTED",
        0,
        uuid4(),
    )


@pytest.mark.parametrize("target_kind", ["claim", "document"])
def test_exact_upstream_blocker_including_document(b05_env, target_kind):
    env = b05_env
    if target_kind == "claim":
        place_claim(env)
    seal(env)
    create(env)
    with env[5].begin() as conn:
        if target_kind == "claim":
            target = env[8]
            column = "claim_version_id"
            table = "claim_versions"
        else:
            target = conn.execute(
                text("SELECT document_artifact_version_id FROM manuscript_versions WHERE id=:id"),
                {"id": env[1].manuscript_version_id},
            ).scalar_one()
            column = "artifact_version_id"
            table = "artifact_versions"
        digest = conn.execute(
            text(f"SELECT content_hash FROM {table} WHERE id=:id"), {"id": target}
        ).scalar_one()
        review = uuid4()
        kind = "ClaimVersion" if target_kind == "claim" else "ArtifactVersion"
        from researchbase.foundation.hashing import sha256_canonical_json

        hashed = str(
            sha256_canonical_json(
                dict(
                    type="InternalReviewRecord",
                    material_version=1,
                    project_id=str(env[1].project_id),
                    target=dict(type=kind, id=str(target), content_hash=digest),
                    reviewer_actor_id=str(env[3].actor_id),
                    review_type="SCIENTIFIC",
                    recommendation="REJECT",
                    summary="Upstream",
                )
            )
        )
        conn.execute(
            text(f"""INSERT INTO internal_review_records
        (id,project_id,{column},target_content_hash,reviewer_actor_id,review_type,recommendation,summary,created_at,content_hash,hash_scheme)
        VALUES (:id,:project,:target,:digest,:actor,'SCIENTIFIC','REJECT','Upstream',clock_timestamp(),:hash,'sha256-cjson-v1')"""),
            dict(
                id=review,
                project=env[1].project_id,
                target=target,
                digest=digest,
                actor=env[3].actor_id,
                hash=hashed,
            ),
        )
        conn.execute(
            text("""INSERT INTO review_issues(id,review_record_id,severity,issue_type,description,status,created_at,ordinal)
        VALUES (:id,:review,'BLOCKING','OTHER','Upstream blocker','OPEN',clock_timestamp(),0)"""),
            dict(id=uuid4(), review=review),
        )
    with pytest.raises(ResearchBaseError) as exc:
        record(env)
    assert exc.value.code == ErrorCode.DECISION_BASIS_INVALID
    with env[4]() as uow:
        rows = uow.decision.applicable_manuscript_reviews(
            env[1].manuscript_version_id, env[1].project_id
        )
        assert review in {r["id"] for r in rows}
        assert uow.decision.material_authors(
            env[1].manuscript_version_id, manuscript=True
        ) == frozenset(
            uow._session.execute(
                text("SELECT b11_authors(:id)"), {"id": env[1].manuscript_version_id}
            ).scalars()
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "manuscript_hash",
        "placement_hash",
        "review_hash",
        "review_target",
        "reviewer_role",
        "document_bytes",
    ],
)
def test_corrupt_saved_closure_fails_closed(b05_env, mutation):
    env = b05_env
    seal(env)
    review = create(env)
    if mutation == "document_bytes":
        with env[5].connect() as conn:
            digest = conn.execute(
                text(
                    "SELECT a.content_hash FROM artifact_versions a JOIN manuscript_versions m ON m.document_artifact_version_id=a.id WHERE m.id=:id"
                ),
                {"id": env[1].manuscript_version_id},
            ).scalar_one()
        env[7]._path_for(digest).write_bytes(b"corrupt")
    else:
        table = (
            "manuscript_versions"
            if mutation in {"manuscript_hash", "placement_hash"}
            else "project_role_assignments"
            if mutation == "reviewer_role"
            else "internal_review_records"
        )
        field = {
            "manuscript_hash": "content_hash",
            "placement_hash": "placement_set_hash",
            "review_hash": "content_hash",
            "review_target": "target_content_hash",
            "reviewer_role": "effective_from",
        }[mutation]
        with env[5].begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER USER"))
            if mutation == "reviewer_role":
                conn.execute(
                    text(
                        "UPDATE project_role_assignments SET effective_from=clock_timestamp() WHERE actor_id=:id"
                    ),
                    {"id": env[3].actor_id},
                )
            else:
                conn.execute(
                    text(f"UPDATE {table} SET {field}=:hash WHERE id=:id"),
                    {
                        "hash": "0" * 64,
                        "id": env[1].manuscript_version_id
                        if table == "manuscript_versions"
                        else review.id,
                    },
                )
            conn.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER USER"))
    with pytest.raises(ResearchBaseError) as exc:
        record(env)
    assert exc.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


@pytest.mark.parametrize("state", ["STALE", "INVALID"])
def test_current_invalidity_denies_new_but_keeps_saved_history(b05_env, state):
    from researchbase.application.governance import (
        CreateAuditFindingCommand,
        CreateImpactAssessmentCommand,
        GovernanceService,
        ProposedImpactTarget,
    )
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock

    env = b05_env
    place_claim(env)
    seal(env)
    create(env)
    cmd = command(env)
    saved = record(env, cmd)
    context = ExecutionContext(actor_id=env[2].actor_id, request_id=uuid4(), client_type="test")
    governance = GovernanceService(env[4], SystemClock())
    finding = governance.create_audit_finding(
        CreateAuditFindingCommand(
            env[1].project_id,
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
            env[1].project_id,
            finding.id,
            {"basis": "TEST ONLY"},
            state.lower(),
            (ProposedImpactTarget("claim_version", env[8], state.lower()),),
            context,
        )
    )
    assert read(env, saved.id).current_validity == state
    assert record(env, cmd).content_hash == saved.content_hash
    with pytest.raises(ResearchBaseError) as exc:
        record(env)
    assert exc.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


@pytest.mark.parametrize("role", ["OWNER", "APPROVER", "RESEARCHER", "REVIEWER", "VIEWER"])
def test_read_roles_and_write_policy(b05_env, role):
    from researchbase.application.phase2_identity import AssignProjectRole, CloseProjectRole
    from tests.integration.phase2.test_pr2_15_decision import identity_service

    env = b05_env
    seal(env)
    create(env)
    saved = record(env)
    identity, _, _ = identity_service(env[5].url.render_as_string(hide_password=False))
    if role != "OWNER":
        identity.assign_project_role(
            AssignProjectRole(
                env[3], env[1].project_id, env[3].actor_id, role, "TEST ONLY", uuid4()
            )
        )
        with env[5].connect() as conn:
            roles = conn.execute(
                text(
                    "SELECT id,role FROM project_role_assignments WHERE actor_id=:id AND effective_until IS NULL"
                ),
                {"id": env[3].actor_id},
            ).all()
        for rid, name in roles:
            if name != role:
                identity.close_project_role(
                    CloseProjectRole(env[2], env[1].project_id, rid, "TEST ONLY", uuid4())
                )
    assert read(env, saved.id).content_hash == saved.content_hash
    with pytest.raises(ResearchBaseError) as exc:
        record(env)
    assert exc.value.code == (
        ErrorCode.IDEMPOTENCY_CONFLICT if role in {"OWNER", "APPROVER"} else ErrorCode.FORBIDDEN
    )


def test_10001_reviews_denied_as_complete_set_without_truncation(b05_env):
    env = b05_env
    seal(env)
    review = create(env)
    with env[5].begin() as conn:
        conn.execute(
            text("""INSERT INTO internal_review_records
        SELECT gen_random_uuid(),r.project_id,r.manuscript_version_id,r.claim_version_id,r.scientific_conclusion_version_id,r.artifact_version_id,
        r.target_content_hash,r.reviewer_actor_id,r.review_type,r.recommendation,r.summary,clock_timestamp(),r.content_hash,r.hash_scheme
        FROM internal_review_records r CROSS JOIN generate_series(1,10000) WHERE r.id=:id"""),
            {"id": review.id},
        )
    with pytest.raises(ResearchBaseError) as exc:
        record(env)
    assert exc.value.code == ErrorCode.DECISION_BASIS_INVALID
    with env[5].connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM internal_review_records")).scalar_one() == 10001
        )
        assert conn.execute(text("SELECT count(*) FROM decision_records")).scalar_one() == 0


@pytest.mark.parametrize(
    "stage", ["INTERNAL_REVIEW", "READY_FOR_SUBMISSION", "SUBMITTED", "ACCEPTED", "PUBLISHED"]
)
def test_stage_admission_and_historical_stage_diagnostics(b05_env, monkeypatch, stage):
    env = b05_env
    seal(env)
    create(env)
    cmd = command(env)
    saved = record(env, cmd)
    # Future lifecycle states are read-policy inputs; B11 does not enable them.
    from researchbase.persistence.publication_repository import SqlAlchemyPublicationRepository

    original = SqlAlchemyPublicationRepository.publication

    def stage_projection(self, *args, **kwargs):
        row = original(self, *args, **kwargs)
        return {**row, "lifecycle_status": stage} if row else row

    monkeypatch.setattr(SqlAlchemyPublicationRepository, "publication", stage_projection)
    assert read(env, saved.id).content_hash == saved.content_hash
    assert record(env, cmd).content_hash == saved.content_hash
    with pytest.raises(ResearchBaseError) as exc:
        record(env)
    assert exc.value.code == (
        ErrorCode.IDEMPOTENCY_CONFLICT
        if stage == "INTERNAL_REVIEW"
        else ErrorCode.INVALID_STATE_TRANSITION
    )


def test_unreachable_exact_claim_blocker_does_not_expand_scope(b05_env):
    env = b05_env
    seal(env)
    create(env)
    env[0].create(
        env[3],
        env[1].project_id,
        "CLAIM_VERSION",
        env[8],
        "SCIENTIFIC",
        "REJECT",
        "Unplaced concern",
        (ReviewIssueRequest("BLOCKING", "OTHER", "Unplaced exact claim"),),
        uuid4(),
    )
    saved = record(env)
    assert not saved.current_blocking_issue_ids and len(saved.basis) == 2


def test_verified_b08_terminal_upstream_issue_is_excluded(b05_env, revision_env):
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
    create(env)
    result = record(env)
    assert not result.current_blocking_issue_ids
    # Historical terminal history and all nested verification stay lock-free.
    assert read(env, result.id).content_hash == result.content_hash
