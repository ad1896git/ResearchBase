"""TEST ONLY principals and disposable PostgreSQL for PR2-14 initial review."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from researchbase.application.internal_review import InternalReviewService, ReviewIssueRequest
from researchbase.foundation.errors import ResearchBaseError
from tests.integration.phase2.test_pr2_11_r2_persistence import (
    conclusion_env as _conclusion_env,
)
from tests.integration.phase2.test_pr2_11_r2_persistence import (
    phase2_database_url as _phase2_database_url,
)
from tests.integration.phase2.test_pr2_13_claim_placement import _draft

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
        concurrent = list(pool.map(lambda _: service.create(
            reviewer, project, "CLAIM_VERSION", claim_id, "SCIENTIFIC",
            "MAJOR_REVISION", "Independent test-only assessment", (issue,), request,
        ), range(2)))
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
        conn.execute(text("""INSERT INTO internal_review_records
          (id,project_id,claim_version_id,target_content_hash,reviewer_actor_id,
           review_type,recommendation,summary,created_at,content_hash,hash_scheme)
          SELECT :new_id,project_id,claim_version_id,:wrong_hash,reviewer_actor_id,
           review_type,recommendation,summary,created_at,content_hash,hash_scheme
          FROM internal_review_records WHERE id=:id"""),
          {"new_id": uuid4(), "wrong_hash": "0" * 64, "id": created.id})
    with pytest.raises(ResearchBaseError):
        service.create(reviewer, project, "CLAIM_VERSION", claim_id,
                       "SCIENTIFIC", "ACCEPT", "Changed replay", (issue,), request)
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
    _, factory, engine, credentials, _author, project, claim_id, _, draft = _draft(
        conclusion_env, phase2_database_url, tmp_path
    )
    evidence_service, reviewer = conclusion_env[2], conclusion_env[4]
    service = InternalReviewService(factory, credentials, evidence_service)
    with pytest.raises(ResearchBaseError):
        service.create(reviewer, uuid4(), "CLAIM_VERSION", claim_id,
                       "SCIENTIFIC", "ACCEPT", "No cross-project review", (), uuid4())
    with pytest.raises(ResearchBaseError):
        service.create(reviewer, project, "MANUSCRIPT_VERSION", draft.id,
                       "EDITORIAL", "ACCEPT", "Draft is ineligible", (), uuid4())
    assert engine is not None


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
        assert conn.execute(text("SELECT to_regclass('internal_review_records')"))\
            .scalar_one() is None
        assert conn.execute(text("SELECT to_regclass('claim_versions')"))\
            .scalar_one() is not None
    engine.dispose()
