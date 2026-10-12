"""TEST ONLY ScientificConclusionVersion internal-review integration."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from uuid import NAMESPACE_URL, uuid4, uuid5

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
from researchbase.application.phase2_identity import CloseProjectRole
from researchbase.application.scientific_conclusion import ClaimInputRequest
from researchbase.domain.organization import ProjectId
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.errors import ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import SystemClock
from tests.application_compat import LegacyApplicationService as ApplicationService
from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service
from tests.integration.phase2.test_pr2_11_r2_persistence import (
    SCOPE,
)
from tests.integration.phase2.test_pr2_11_r2_persistence import (
    conclusion_env as _conclusion_env,
)
from tests.integration.phase2.test_pr2_11_r2_persistence import (
    phase2_database_url as _phase2_database_url,
)
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker
from tests.integration.test_pr12_application import seed_claim

pytestmark = pytest.mark.integration
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
conclusion_env = _conclusion_env
phase2_database_url = _phase2_database_url


def _frozen_conclusion(env):
    scientific, factory, evidence, author, reviewer, project, claim_id, _, engine, credentials = env
    created = scientific.create(
        author, project, "Test-only exact conclusion", SCOPE, "MODERATE", None,
        (ClaimInputRequest(claim_id, "SUPPORTS"),), (), uuid4(),
    )
    scientific.freeze(author, project, created.conclusion_id, created.version_id, uuid4())
    return (
        InternalReviewService(factory, credentials, evidence), author, reviewer,
        project, created.version_id, engine,
    )


def test_conclusion_review_exact_frozen_target_and_initial_issue(
    conclusion_env, phase2_database_url,
):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    service, _, reviewer, project, version, engine = _frozen_conclusion(conclusion_env)
    request = uuid4()
    issue = ReviewIssueRequest("MAJOR", "OVERCLAIM", "Test-only concern")

    created = service.create(
        reviewer, project, "SCIENTIFIC_CONCLUSION_VERSION", version,
        "SCIENTIFIC", "MAJOR_REVISION", "Test-only independent assessment",
        (issue,), request,
    )
    assert created.target_id == version
    assert created.target_kind == "SCIENTIFIC_CONCLUSION_VERSION"
    assert created.issues[0].status == "OPEN"
    assert service.read(reviewer, project, created.id) == created
    assert service.create(
        reviewer, project, "SCIENTIFIC_CONCLUSION_VERSION", version,
        "SCIENTIFIC", "MAJOR_REVISION", "Test-only independent assessment",
        (issue,), request,
    ) == created
    with ThreadPoolExecutor(max_workers=2) as pool:
        same = list(pool.map(lambda _: service.create(
            reviewer, project, "SCIENTIFIC_CONCLUSION_VERSION", version,
            "SCIENTIFIC", "MAJOR_REVISION", "Test-only independent assessment",
            (issue,), request,
        ), range(2)))
    assert same == [created, created]
    with pytest.raises(ResearchBaseError):
        service.create(
            reviewer, project, "SCIENTIFIC_CONCLUSION_VERSION", version,
            "SCIENTIFIC", "ACCEPT", "Changed replay", (issue,), request,
        )
    with engine.connect() as conn:
        row = conn.execute(text("""SELECT claim_version_id,scientific_conclusion_version_id,
          target_content_hash FROM internal_review_records WHERE id=:id"""),
          {"id": created.id}).one()
        assert row.claim_version_id is None
        assert row.scientific_conclusion_version_id == version
        assert row.target_content_hash == created.target_content_hash
        assert conn.execute(text("SELECT count(*) FROM review_issue_events")).scalar_one() == 1
        assert conn.execute(
            text("SELECT count(*) FROM decision_records")
        ).scalar_one() == 0
    with pytest.raises(DBAPIError), engine.begin() as conn:
        conn.execute(text("""INSERT INTO internal_review_records
          (id,project_id,scientific_conclusion_version_id,target_content_hash,
           reviewer_actor_id,review_type,recommendation,summary,created_at,
           content_hash,hash_scheme)
          SELECT :new_id,project_id,scientific_conclusion_version_id,:wrong_hash,
           reviewer_actor_id,review_type,recommendation,summary,created_at,
           content_hash,hash_scheme FROM internal_review_records WHERE id=:id"""),
          {"new_id": uuid4(), "wrong_hash": "0" * 64, "id": created.id})


def test_conclusion_review_rejects_missing_draft_cross_project_and_self_review(
    conclusion_env, phase2_database_url,
):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    scientific, factory, evidence, author, reviewer, project, claim_id, _, engine, credentials = (
        conclusion_env
    )
    service = InternalReviewService(factory, credentials, evidence)
    draft = scientific.create(
        author, project, "Test-only draft conclusion", SCOPE, "MODERATE", None,
        (ClaimInputRequest(claim_id, "SUPPORTS"),), (), uuid4(),
    )
    cases = (
        (reviewer, project, uuid4()),
        (reviewer, project, draft.version_id),
        (reviewer, uuid4(), draft.version_id),
    )
    for principal, target_project, version in cases:
        with pytest.raises(ResearchBaseError):
            service.create(
                principal, target_project, "SCIENTIFIC_CONCLUSION_VERSION", version,
                "SCIENTIFIC", "ACCEPT", "Test-only review", (), uuid4(),
            )
    scientific.freeze(author, project, draft.conclusion_id, draft.version_id, uuid4())
    with pytest.raises(ResearchBaseError):
        service.create(
            author, project, "SCIENTIFIC_CONCLUSION_VERSION", draft.version_id,
            "SCIENTIFIC", "ACCEPT", "Self review denied", (), uuid4(),
        )
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM internal_review_records")).scalar_one() == 0
        assert conn.execute(text("SELECT count(*) FROM review_issues")).scalar_one() == 0
        assert conn.execute(text("SELECT count(*) FROM review_issue_events")).scalar_one() == 0


def test_conclusion_review_role_revocation_and_issue_reference_are_atomic(
    conclusion_env, phase2_database_url, tmp_path,
):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    service, author, reviewer, project, version, engine = _frozen_conclusion(conclusion_env)
    created = service.create(
        reviewer, project, "SCIENTIFIC_CONCLUSION_VERSION", version,
        "SCIENTIFIC", "MAJOR_REVISION", "Test-only assessment",
        (ReviewIssueRequest("BLOCKING", "OVERCLAIM", "Test-only blocking issue"),),
        uuid4(),
    )
    factory = conclusion_env[1]
    app = ApplicationService(
        factory, SystemClock(), ContentAddressedFilesystemArtifactStore(tmp_path / "other-cas")
    )
    context = ExecutionContext(actor_id=author.actor_id, request_id=uuid4(), client_type="test")
    other = app.create_project(CreateProjectCommand("Other test-only project", None, context))
    _, other_draft = seed_claim(app, ProjectId(other.id), context, "Other project claim")
    with pytest.raises(DBAPIError), engine.begin() as conn:
        conn.execute(text("""INSERT INTO review_issues
          (id,review_record_id,severity,issue_type,description,related_claim_version_id,
           status,created_at,ordinal)
          VALUES (:id,:review,'MAJOR','OVERCLAIM','Bad cross-project issue',
                  :claim,'OPEN',clock_timestamp(),1)"""),
          {"id": uuid4(), "review": created.id, "claim": other_draft.id})
    with engine.connect() as conn:
        role = conn.execute(text("""SELECT id FROM project_role_assignments
          WHERE actor_id=:actor AND project_id=:project AND effective_until IS NULL"""),
          {"actor": reviewer.actor_id, "project": project}).scalar_one()
    identity, _, _ = identity_service(str(engine.url))
    identity.close_project_role(CloseProjectRole(
        author, project, role, "Test-only reviewer role closure", uuid4(),
    ))
    with pytest.raises(ResearchBaseError):
        service.create(
            reviewer, project, "SCIENTIFIC_CONCLUSION_VERSION", version,
            "SCIENTIFIC", "ACCEPT", "Denied after role closure", (), uuid4(),
        )
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM internal_review_records")).scalar_one() == 1
        assert conn.execute(text("SELECT count(*) FROM review_issues")).scalar_one() == 1
        assert conn.execute(text("SELECT count(*) FROM review_issue_events")).scalar_one() == 1


def test_conclusion_review_rejects_currently_stale_input(
    conclusion_env, phase2_database_url,
):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    service, author, reviewer, project, version, engine = _frozen_conclusion(conclusion_env)
    _, factory, _, _, _, _, claim_id, _, _, _ = conclusion_env
    context = ExecutionContext(actor_id=author.actor_id, request_id=uuid4(), client_type="test")
    governance = GovernanceService(factory, SystemClock())
    finding = governance.create_audit_finding(CreateAuditFindingCommand(
        project, "code_bug", "major", "Test-only stale input", "Claim needs recheck",
        "claim_version", claim_id, context,
    ))
    governance.create_impact_assessment(CreateImpactAssessmentCommand(
        project, finding.id, {"basis": "test-only"}, "stale",
        (ProposedImpactTarget("claim_version", claim_id, "stale"),), context,
    ))
    with pytest.raises(ResearchBaseError):
        service.create(
            reviewer, project, "SCIENTIFIC_CONCLUSION_VERSION", version,
            "SCIENTIFIC", "ACCEPT", "Stale target denied", (), uuid4(),
        )
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM internal_review_records")).scalar_one() == 0


def test_historical_conclusion_review_remains_readable_after_upstream_stales(
    conclusion_env, phase2_database_url,
):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    service, author, reviewer, project, version, engine = _frozen_conclusion(conclusion_env)
    prior = service.create(
        reviewer, project, "SCIENTIFIC_CONCLUSION_VERSION", version,
        "SCIENTIFIC", "UNCERTAIN", "Test-only historical assessment", (), uuid4(),
    )
    _, factory, _, _, _, _, claim_id, _, _, _ = conclusion_env
    context = ExecutionContext(actor_id=author.actor_id, request_id=uuid4(), client_type="test")
    governance = GovernanceService(factory, SystemClock())
    finding = governance.create_audit_finding(CreateAuditFindingCommand(
        project, "code_bug", "major", "Test-only late impact", "Claim needs recheck",
        "claim_version", claim_id, context,
    ))
    governance.create_impact_assessment(CreateImpactAssessmentCommand(
        project, finding.id, {"basis": "test-only"}, "stale",
        (ProposedImpactTarget("claim_version", claim_id, "stale"),), context,
    ))
    assert service.read(reviewer, project, prior.id) == prior
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM internal_review_records")).scalar_one() == 1


def test_conclusion_review_rechecks_credential_after_observed_target_lock_wait(
    conclusion_env, phase2_database_url,
):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    service, _, reviewer, project, version, engine = _frozen_conclusion(conclusion_env)
    credentials = conclusion_env[-1]
    with ThreadPoolExecutor(max_workers=1) as pool:
        with engine.begin() as holder:
            holder_pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            holder.execute(text("""SELECT id FROM scientific_conclusion_versions
              WHERE id=:id FOR UPDATE"""), {"id": version}).scalar_one()
            pending = pool.submit(
                service.create, reviewer, project, "SCIENTIFIC_CONCLUSION_VERSION", version,
                "SCIENTIFIC", "ACCEPT", "Denied after lock wait", (), uuid4(),
            )
            witness = _wait_for_pg_blocker(engine, holder_pid, "transactionid")
            assert "scientific_conclusion_versions" in witness["query"]
            assert not pending.done()
            credentials.enabled = False
            assert not credentials.is_valid(reviewer, witness["observed_at"])
            again = _wait_for_pg_blocker(engine, holder_pid, "transactionid")
            assert again["pid"] == witness["pid"]
        with pytest.raises(ResearchBaseError):
            pending.result(timeout=10)
    with engine.connect() as conn:
        for table in ("internal_review_records", "review_issues", "review_issue_events"):
            assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0


def test_conclusion_review_rechecks_scheduled_role_expiry_after_request_lock_wait(
    conclusion_env, phase2_database_url,
):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    service, _, reviewer, project, version, engine = _frozen_conclusion(conclusion_env)
    with engine.begin() as conn:
        role = conn.execute(text("""SELECT id FROM project_role_assignments
          WHERE actor_id=:actor AND project_id=:project AND effective_until IS NULL"""),
          {"actor": reviewer.actor_id, "project": project}).scalar_one()
        until = conn.execute(text("""UPDATE project_role_assignments
          SET effective_until=clock_timestamp() + interval '8 seconds',
              row_version=row_version+1 WHERE id=:id RETURNING effective_until"""),
          {"id": role}).scalar_one()
        conn.execute(text("""INSERT INTO project_role_events
          (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id)
          VALUES (:id,:role,:actor,'CLOSED',:until,'Test-only expiry',:request)"""),
          {"id": uuid4(), "role": role, "actor": reviewer.actor_id,
           "until": until, "request": uuid4()})
    request = uuid4()
    identity = uuid5(NAMESPACE_URL,
        f"pr214:{reviewer.deployment_id}:{project}:{reviewer.actor_id}:{request}")
    with ThreadPoolExecutor(max_workers=1) as pool:
        with engine.begin() as holder:
            holder_pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            holder.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                           {"key": f"pr214:review:{identity}"})
            pending = pool.submit(
                service.create, reviewer, project, "SCIENTIFIC_CONCLUSION_VERSION", version,
                "SCIENTIFIC", "ACCEPT", "Expired while waiting", (), request,
            )
            before = _wait_for_pg_blocker(engine, holder_pid, "advisory")
            assert before["observed_at"] < until
            holder.execute(text("""SELECT pg_sleep(GREATEST(0,
              EXTRACT(EPOCH FROM (:until-clock_timestamp()))+0.1))"""), {"until": until})
            after = _wait_for_pg_blocker(engine, holder_pid, "advisory")
            assert after["pid"] == before["pid"]
            assert after["observed_at"] >= until
            assert not pending.done()
        with pytest.raises(ResearchBaseError):
            pending.result(timeout=10)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM internal_review_records")).scalar_one() == 0


def test_existing_issue_insert_coordinates_target_before_review(
    conclusion_env, phase2_database_url,
):
    """Frozen PR2-15 prerequisite; no DecisionRecord is created by this test."""
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    service, _, reviewer, project, version, engine = _frozen_conclusion(conclusion_env)
    created = service.create(
        reviewer, project, "SCIENTIFIC_CONCLUSION_VERSION", version,
        "SCIENTIFIC", "UNCERTAIN", "Test-only initial review", (), uuid4(),
    )
    def insert_issue(ordinal: int) -> None:
        with engine.begin() as conn:
            conn.execute(text("""INSERT INTO review_issues
              (id,review_record_id,severity,issue_type,description,status,created_at,ordinal)
              VALUES (:id,:review,'BLOCKING','OVERCLAIM','Test-only diagnostic',
                      'OPEN',clock_timestamp(),:ordinal)"""),
              {"id": uuid4(), "review": created.id, "ordinal": ordinal})
    with ThreadPoolExecutor(max_workers=1) as pool:
        with engine.begin() as target_holder:
            holder_pid = target_holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            target_holder.execute(text("""SELECT id FROM scientific_conclusion_versions
              WHERE id=:id FOR UPDATE"""), {"id": version}).scalar_one()
            pending = pool.submit(insert_issue, 0)
            witness = _wait_for_pg_blocker(engine, holder_pid, "transactionid")
            assert "review_issues" in witness["query"]
            assert not pending.done()
        pending.result(timeout=10)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with engine.begin() as review_holder:
            holder_pid = review_holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            review_holder.execute(text("""SELECT id FROM internal_review_records
              WHERE id=:id FOR UPDATE"""), {"id": created.id}).scalar_one()
            pending = pool.submit(insert_issue, 1)
            witness = _wait_for_pg_blocker(engine, holder_pid, "transactionid")
            assert "review_issues" in witness["query"]
            assert not pending.done()
        pending.result(timeout=10)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM review_issues")).scalar_one() == 2
        assert conn.execute(text("SELECT count(*) FROM review_issue_events")).scalar_one() == 2
