"""TEST ONLY principals and disposable PostgreSQL for PR2-14 initial review."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from researchbase.application.commands import CreateProjectCommand
from researchbase.application.governance import (
    CreateAuditFindingCommand,
    CreateImpactAssessmentCommand,
    GovernanceService,
    ProposedImpactTarget,
)
from researchbase.application.internal_review import InternalReviewService, ReviewIssueRequest
from researchbase.domain.organization import ProjectId
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.errors import ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import SystemClock
from tests.application_compat import LegacyApplicationService as ApplicationService
from tests.integration.phase2.test_pr2_11_r2_persistence import (
    conclusion_env as _conclusion_env,
)
from tests.integration.phase2.test_pr2_11_r2_persistence import (
    phase2_database_url as _phase2_database_url,
)
from tests.integration.phase2.test_pr2_13_claim_placement import _draft
from tests.integration.test_pr12_application import seed_claim

pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration
conclusion_env = _conclusion_env
phase2_database_url = _phase2_database_url


def test_independent_frozen_claim_review_and_issue_are_immutable(
    conclusion_env,
    phase2_database_url,
):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    _, factory, evidence_service, author, reviewer, project, claim_id, _, engine, credentials = (
        conclusion_env
    )
    service = InternalReviewService(factory, credentials, evidence_service)
    issue = ReviewIssueRequest("MAJOR", "UNSUPPORTED_CLAIM", "Check exact run support")
    request = uuid4()
    created = service.create(
        reviewer,
        project,
        "CLAIM_VERSION",
        claim_id,
        "SCIENTIFIC",
        "MAJOR_REVISION",
        "Independent test-only assessment",
        (issue,),
        request,
    )
    assert created.reviewer_actor_id == reviewer.actor_id
    assert created.target_id == claim_id and created.target_content_hash
    assert created.content_hash and len(created.content_hash) == 64
    assert len(created.issues) == 1 and created.issues[0].status == "OPEN"
    assert (
        service.create(
            reviewer,
            project,
            "CLAIM_VERSION",
            claim_id,
            "SCIENTIFIC",
            "MAJOR_REVISION",
            "Independent test-only assessment",
            (issue,),
            request,
        )
        == created
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        concurrent = list(
            pool.map(
                lambda _: service.create(
                    reviewer,
                    project,
                    "CLAIM_VERSION",
                    claim_id,
                    "SCIENTIFIC",
                    "MAJOR_REVISION",
                    "Independent test-only assessment",
                    (issue,),
                    request,
                ),
                range(2),
            )
        )
    assert concurrent == [created, created]
    with pytest.raises(ResearchBaseError):
        service.create(
            author,
            project,
            "CLAIM_VERSION",
            claim_id,
            "SCIENTIFIC",
            "ACCEPT",
            "Self review",
            (),
            uuid4(),
        )
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM internal_review_records")).scalar_one() == 1
        assert conn.execute(text("SELECT count(*) FROM review_issues")).scalar_one() == 1
        assert conn.execute(text("SELECT count(*) FROM review_issue_events")).scalar_one() == 1
        assert (
            conn.execute(
                text("SELECT count(*) FROM literature_evidence_review_events")
            ).scalar_one()
            == 0
        )
    with pytest.raises(DBAPIError), engine.begin() as conn:
        conn.execute(
            text("UPDATE internal_review_records SET summary='tampered' WHERE id=:id"),
            {"id": created.id},
        )
    with pytest.raises(DBAPIError), engine.begin() as conn:
        conn.execute(
            text("DELETE FROM review_issues WHERE review_record_id=:id"), {"id": created.id}
        )
    with pytest.raises(DBAPIError), engine.begin() as conn:
        conn.execute(
            text("UPDATE review_issue_events SET new_status='OPEN' WHERE issue_id=:id"),
            {"id": created.issues[0].id},
        )
    with pytest.raises(DBAPIError), engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO internal_review_records
          (id,project_id,claim_version_id,target_content_hash,reviewer_actor_id,
           review_type,recommendation,summary,created_at,content_hash,hash_scheme)
          SELECT :new_id,project_id,claim_version_id,:wrong_hash,reviewer_actor_id,
           review_type,recommendation,summary,created_at,content_hash,hash_scheme
          FROM internal_review_records WHERE id=:id"""),
            {"new_id": uuid4(), "wrong_hash": "0" * 64, "id": created.id},
        )
    with engine.connect() as conn:
        artifact_id = conn.execute(text("SELECT id FROM artifact_versions LIMIT 1")).scalar_one()
    with pytest.raises(DBAPIError), engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO internal_review_records
          (id,project_id,claim_version_id,artifact_version_id,target_content_hash,
           reviewer_actor_id,review_type,recommendation,summary,created_at,
           content_hash,hash_scheme)
          SELECT :new_id,project_id,claim_version_id,:artifact_id,target_content_hash,
           reviewer_actor_id,review_type,recommendation,summary,created_at,
           content_hash,hash_scheme FROM internal_review_records WHERE id=:id"""),
            {"new_id": uuid4(), "artifact_id": artifact_id, "id": created.id},
        )
    with pytest.raises(ResearchBaseError):
        service.create(
            reviewer,
            project,
            "CLAIM_VERSION",
            claim_id,
            "SCIENTIFIC",
            "ACCEPT",
            "Changed replay",
            (issue,),
            request,
        )
    with pytest.raises(ResearchBaseError):
        service.create(
            reviewer,
            project,
            "CLAIM_VERSION",
            claim_id,
            "SCIENTIFIC",
            "MAJOR_REVISION",
            "Independent test-only assessment",
            (),
            request,
        )
    with pytest.raises(ResearchBaseError):
        service.create(
            replace(reviewer, credential_id="forged-test-only"),
            project,
            "CLAIM_VERSION",
            claim_id,
            "SCIENTIFIC",
            "ACCEPT",
            "Forged credential",
            (),
            uuid4(),
        )
    with pytest.raises(DBAPIError):
        command.downgrade(config, "0039_pr2_13_citation_rebinding_guard")
    engine.dispose()
    assert (
        InternalReviewService(factory, credentials, evidence_service).read(
            reviewer, project, created.id
        )
        == created
    )


def test_draft_and_cross_project_review_targets_fail_closed(
    conclusion_env,
    phase2_database_url,
    tmp_path,
):
    _, factory, engine, credentials, author, project, claim_id, _, draft = _draft(
        conclusion_env, phase2_database_url, tmp_path
    )
    evidence_service, reviewer = conclusion_env[2], conclusion_env[4]
    service = InternalReviewService(factory, credentials, evidence_service)
    with pytest.raises(ResearchBaseError):
        service.create(
            reviewer,
            uuid4(),
            "CLAIM_VERSION",
            claim_id,
            "SCIENTIFIC",
            "ACCEPT",
            "No cross-project review",
            (),
            uuid4(),
        )
    with pytest.raises(ResearchBaseError):
        service.create(
            reviewer,
            project,
            "MANUSCRIPT_VERSION",
            draft.id,
            "EDITORIAL",
            "ACCEPT",
            "Draft is ineligible",
            (),
            uuid4(),
        )
    app = ApplicationService(
        factory, SystemClock(), ContentAddressedFilesystemArtifactStore(tmp_path / "draft-cas")
    )
    context = ExecutionContext(actor_id=author.actor_id, request_id=uuid4(), client_type="test")
    _, draft_claim = seed_claim(app, ProjectId(project), context, "Draft review target")
    with pytest.raises(ResearchBaseError):
        service.create(
            reviewer,
            project,
            "CLAIM_VERSION",
            UUID(str(draft_claim.id)),
            "SCIENTIFIC",
            "ACCEPT",
            "Draft claim is ineligible",
            (),
            uuid4(),
        )
    assert engine is not None


def test_missing_claim_and_denied_review_leave_no_partial_history(
    conclusion_env, phase2_database_url
):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    _, factory, evidence_service, author, reviewer, project, claim_id, _, engine, credentials = (
        conclusion_env
    )
    service = InternalReviewService(factory, credentials, evidence_service)
    issue = ReviewIssueRequest("MAJOR", "UNSUPPORTED_CLAIM", "Test-only issue")
    for principal, target in ((reviewer, uuid4()), (author, claim_id)):
        with pytest.raises(ResearchBaseError):
            service.create(
                principal, project, "CLAIM_VERSION", target, "SCIENTIFIC",
                "MAJOR_REVISION", "Denied exact review", (issue,), uuid4(),
            )
    with engine.connect() as conn:
        for table in ("internal_review_records", "review_issues", "review_issue_events"):
            assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0


def test_reviewer_role_expiry_and_revocation_deny_review(
    conclusion_env, phase2_database_url
):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    _, factory, evidence_service, author, reviewer, project, claim_id, _, engine, credentials = (
        conclusion_env
    )
    service = InternalReviewService(factory, credentials, evidence_service)
    with engine.connect() as conn:
        role = conn.execute(text("""SELECT id FROM project_role_assignments
          WHERE actor_id=:actor AND project_id=:project AND effective_until IS NULL"""),
          {"actor": reviewer.actor_id, "project": project}).scalar_one()
    from researchbase.application.phase2_identity import CloseProjectRole
    from tests.integration.phase2.test_pr2_00_challenges import _service

    identity, _, _ = _service(str(engine.url))
    identity.close_project_role(CloseProjectRole(
        author, project, role, "Test-only role revocation", uuid4()))
    with engine.connect() as conn:
        ended = conn.execute(text("""SELECT effective_until FROM project_role_assignments
          WHERE id=:id"""), {"id": role}).scalar_one()
        assert ended is not None
        assert conn.execute(text("""SELECT count(*) FROM project_role_events
          WHERE role_assignment_id=:id AND event_kind='CLOSED'"""),
          {"id": role}).scalar_one() == 1
    with pytest.raises(ResearchBaseError):
        service.create(reviewer, project, "CLAIM_VERSION", claim_id, "SCIENTIFIC",
                       "ACCEPT", "Role closed", (), uuid4())
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM internal_review_records")).scalar_one() == 0


def test_currently_stale_claim_and_cross_project_issue_reference_fail_closed(
    conclusion_env, phase2_database_url, tmp_path
):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    _, factory, evidence_service, author, reviewer, project, claim_id, _, engine, credentials = (
        conclusion_env
    )
    service = InternalReviewService(factory, credentials, evidence_service)
    app = ApplicationService(
        factory, SystemClock(), ContentAddressedFilesystemArtifactStore(tmp_path / "issue-cas")
    )
    context = ExecutionContext(actor_id=author.actor_id, request_id=uuid4(), client_type="test")
    other = app.create_project(CreateProjectCommand("Other test project", None, context))
    _, other_draft = seed_claim(app, ProjectId(other.id), context, "Other project claim")
    created = service.create(
        reviewer, project, "CLAIM_VERSION", claim_id, "SCIENTIFIC", "MAJOR_REVISION",
        "Independent test review", (ReviewIssueRequest("MAJOR", "CITATION", "Check source"),),
        uuid4(),
    )
    with pytest.raises(DBAPIError), engine.begin() as conn:
        conn.execute(text("""INSERT INTO review_issues
          (id,review_record_id,severity,issue_type,description,related_claim_version_id,
           status,created_at,ordinal)
          VALUES (:id,:review,'MAJOR','CITATION','Cross-project test reference',
                  :claim,'OPEN',clock_timestamp(),1)"""),
          {"id": uuid4(), "review": created.id, "claim": UUID(str(other_draft.id))})
    governance = GovernanceService(factory, SystemClock())
    finding = governance.create_audit_finding(CreateAuditFindingCommand(
        project, "code_bug", "major", "Test-only finding", "Claim needs recheck",
        "claim_version", claim_id, context,
    ))
    governance.create_impact_assessment(CreateImpactAssessmentCommand(
        project, finding.id, {"basis": "test-only"}, "stale",
        (ProposedImpactTarget("claim_version", claim_id, "stale"),), context,
    ))
    with pytest.raises(ResearchBaseError):
        service.create(reviewer, project, "CLAIM_VERSION", claim_id, "SCIENTIFIC",
                       "ACCEPT", "Stale target", (), uuid4())
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM internal_review_records")).scalar_one() == 1
        assert conn.execute(text("SELECT count(*) FROM review_issues")).scalar_one() == 1


def test_credential_revocation_while_request_lock_waits_is_rechecked(
    conclusion_env, phase2_database_url
):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    _, factory, evidence_service, _, reviewer, project, claim_id, _, engine, credentials = (
        conclusion_env
    )
    service = InternalReviewService(factory, credentials, evidence_service)
    request = uuid4()
    identity = uuid5(
        NAMESPACE_URL,
        f"pr214:{reviewer.deployment_id}:{project}:{reviewer.actor_id}:{request}",
    )
    checked = Event()
    original = credentials.is_valid

    def observed_valid(principal, at):
        result = original(principal, at)
        checked.set()
        return result

    credentials.is_valid = observed_valid
    with ThreadPoolExecutor(max_workers=1) as pool:
        with engine.begin() as holder:
            holder.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                           {"key": f"pr214:review:{identity}"})
            pending = pool.submit(
                service.create, reviewer, project, "CLAIM_VERSION", claim_id,
                "SCIENTIFIC", "ACCEPT", "Must recheck after lock wait", (), request,
            )
            assert checked.wait(timeout=10)
            credentials.enabled = False
        with pytest.raises(ResearchBaseError):
            pending.result(timeout=10)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM internal_review_records")).scalar_one() == 0


def test_credential_revocation_while_target_row_lock_waits_is_rechecked(
    conclusion_env, phase2_database_url
):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    _, factory, evidence_service, _, reviewer, project, claim_id, _, engine, credentials = (
        conclusion_env
    )
    service = InternalReviewService(factory, credentials, evidence_service)
    checked = Event()
    checks = 0
    original = credentials.is_valid

    def observed_valid(principal, at):
        nonlocal checks
        result = original(principal, at)
        checks += 1
        if checks == 2:
            checked.set()
        return result

    credentials.is_valid = observed_valid
    with ThreadPoolExecutor(max_workers=1) as pool:
        with engine.begin() as holder:
            holder.execute(text("SELECT id FROM claim_versions WHERE id=:id FOR UPDATE"),
                           {"id": claim_id}).scalar_one()
            pending = pool.submit(
                service.create, reviewer, project, "CLAIM_VERSION", claim_id,
                "SCIENTIFIC", "ACCEPT", "Must recheck after target wait", (), uuid4(),
            )
            assert checked.wait(timeout=10)
            credentials.enabled = False
        with pytest.raises(ResearchBaseError):
            pending.result(timeout=10)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM internal_review_records")).scalar_one() == 0


def test_empty_migration_downgrade_drops_only_new_review_objects(phase2_database_url):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    command.downgrade(config, "0039_pr2_13_citation_rebinding_guard")
    from sqlalchemy import create_engine

    engine = create_engine(phase2_database_url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0039_pr2_13_citation_rebinding_guard"
        )
        assert (
            conn.execute(text("SELECT to_regclass('internal_review_records')")).scalar_one() is None
        )
        assert conn.execute(text("SELECT to_regclass('claim_versions')")).scalar_one() is not None
    engine.dispose()
