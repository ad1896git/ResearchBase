"""B25 exact recorded concerns, attribution and malformed saved history."""

# ruff: noqa: E501

from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.internal_review import ReviewIssueRequest
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b25_support import place, queries
from tests.integration.phase2.test_b05_manuscript_review import (  # noqa: F401
    b04_env as _b04_env,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    b05_env as _b05_env,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    conclusion_env as _conclusion_env,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    phase2_database_url as _phase2_database_url,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    seal,
)

b04_env = _b04_env
b05_env = _b05_env
conclusion_env = _conclusion_env
phase2_database_url = _phase2_database_url

pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "kind", ["MANUSCRIPT_VERSION", "CLAIM_VERSION", "SCIENTIFIC_CONCLUSION_VERSION"]
)
@pytest.mark.parametrize("severity", ["INFO", "MINOR", "MAJOR", "BLOCKING"])
def test_exact_concerns_and_every_occurrence(b05_env, kind, severity):
    env = b05_env
    conclusion = place(env, conclusion=True)
    place(env)
    place(env, ordinal=1)
    seal(env)
    identity = {
        "MANUSCRIPT_VERSION": env[1].manuscript_version_id,
        "CLAIM_VERSION": env[8],
        "SCIENTIFIC_CONCLUSION_VERSION": conclusion,
    }[kind]
    result = env[0].create(
        env[3],
        env[1].project_id,
        kind,
        identity,
        "SCIENTIFIC",
        "ACCEPT",
        "Recorded assessment",
        (
            ReviewIssueRequest(severity, "UNSUPPORTED_CLAIM", "Recorded unsupported concern"),
            ReviewIssueRequest("BLOCKING", "WRITING", "Other blocking issue"),
            ReviewIssueRequest("MAJOR", "OVERCLAIM", "Distinct overclaim"),
        ),
        uuid4(),
    )
    service, _, aq = queries(env)
    audit = service.get_manuscript_audit(env[3], aq)
    assert audit.validity.current_validity == "VALID"
    assert len(audit.unsupported_concerns) == 1
    concern = audit.unsupported_concerns[0]
    assert concern.issue_id == result.issues[0].id
    assert (
        concern.review_record_id == result.id and concern.review_content_hash == result.content_hash
    )
    assert concern.target_content_hash == result.target_content_hash
    assert concern.description == "Recorded unsupported concern"
    assert concern.event_actor_id == env[3].actor_id
    assert concern.review_target.id == identity
    assert (
        len(concern.occurrences)
        == {"MANUSCRIPT_VERSION": 0, "CLAIM_VERSION": 3, "SCIENTIFIC_CONCLUSION_VERSION": 1}[kind]
    )
    assert all(path.nodes[-1] == concern.review_target for path in concern.occurrences)
    expected_blocking = [result.issues[1].id] + (
        [result.issues[0].id] if severity == "BLOCKING" else []
    )
    assert audit.blocking_issue_ids == tuple(sorted(expected_blocking, key=str))
    with env[5].connect() as conn:
        event = conn.execute(
            text("SELECT id,occurred_at FROM review_issue_events WHERE issue_id=:id"),
            {"id": concern.issue_id},
        ).one()
    assert (concern.event_id, concern.occurred_at) == tuple(event)


@pytest.mark.parametrize(
    "target", ["MANUSCRIPT_VERSION", "CLAIM_VERSION", "SCIENTIFIC_CONCLUSION_VERSION"]
)
@pytest.mark.parametrize(
    "failure",
    [
        "review_hash",
        "binding",
        "issue_type",
        "severity",
        "text",
        "ordinal",
        "root",
        "actor",
        "time",
    ],
)
def test_saved_review_and_issue_corruption_fails_closed(b05_env, target, failure):
    env = b05_env
    conclusion = place(env, conclusion=True)
    seal(env)
    identity = {
        "MANUSCRIPT_VERSION": env[1].manuscript_version_id,
        "CLAIM_VERSION": env[8],
        "SCIENTIFIC_CONCLUSION_VERSION": conclusion,
    }[target]
    env[0].create(
        env[3],
        env[1].project_id,
        target,
        identity,
        "SCIENTIFIC",
        "ACCEPT",
        "Review",
        (ReviewIssueRequest("MAJOR", "UNSUPPORTED_CLAIM", "Concern"),),
        uuid4(),
    )
    sql = {
        "review_hash": "UPDATE internal_review_records SET content_hash=repeat('0',64)",
        "binding": "UPDATE internal_review_records SET created_at='1900-01-01'",
        "issue_type": "UPDATE review_issues SET issue_type='OTHER'",  # valid enum but no hash binding by design; use corrupt adapter below
        "severity": "UPDATE review_issues SET severity='INFO'",
        "text": "UPDATE review_issues SET description='e' || chr(769)",
        "ordinal": "UPDATE review_issues SET ordinal=3",
        "root": "DELETE FROM review_issue_events",
        "actor": "UPDATE review_issue_events SET actor_id=:actor",
        "time": "UPDATE review_issue_events SET occurred_at=occurred_at+interval '1 second'",
    }[failure]
    if failure in {"issue_type", "severity"}:
        # Persist invalid enum while retaining the other columns, bypassing CHECK only in read adapter.
        from unittest.mock import patch

        from researchbase.persistence.internal_review_repository import (
            SqlAlchemyInternalReviewRepository,
        )

        original = SqlAlchemyInternalReviewRepository.audit_issues

        def malformed(self, identity):
            rows = original(self, identity)
            rows[0][failure] = "UNRECOGNIZED"
            return rows

        service, _, aq = queries(env)
        with patch.object(SqlAlchemyInternalReviewRepository, "audit_issues", malformed):
            with pytest.raises(ResearchBaseError) as error:
                service.get_manuscript_audit(env[3], aq)
        assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
        return
    with env[5].begin() as conn:
        conn.execute(text("SET LOCAL session_replication_role='replica'"))
        conn.execute(text(sql), {"actor": env[2].actor_id})
    service, _, aq = queries(env)
    with pytest.raises(ResearchBaseError) as error:
        service.get_manuscript_audit(env[3], aq)
    assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_unrelated_exact_claim_review_excluded(b05_env):
    env = b05_env
    seal(env)
    # Existing frozen Claim is not placed in this manuscript.
    env[0].create(
        env[3],
        env[1].project_id,
        "CLAIM_VERSION",
        env[8],
        "SCIENTIFIC",
        "ACCEPT",
        "Unrelated",
        (ReviewIssueRequest("BLOCKING", "UNSUPPORTED_CLAIM", "Elsewhere"),),
        uuid4(),
    )
    service, _, aq = queries(env)
    audit = service.get_manuscript_audit(env[3], aq)
    assert audit.unsupported_concerns == audit.blocking_issue_ids == ()


def test_ambiguous_saved_target_fails_before_legacy_verifier(b05_env, monkeypatch):
    from researchbase.persistence.internal_review_repository import (
        SqlAlchemyInternalReviewRepository,
    )

    env = b05_env
    place(env)
    seal(env)
    env[0].create(
        env[3],
        env[1].project_id,
        "CLAIM_VERSION",
        env[8],
        "SCIENTIFIC",
        "ACCEPT",
        "Independent review",
        (),
        uuid4(),
    )
    original = SqlAlchemyInternalReviewRepository.scoped_reviews

    def ambiguous(self, *args):
        rows = original(self, *args)
        rows[0]["artifact_version_id"] = uuid4()
        return rows

    monkeypatch.setattr(SqlAlchemyInternalReviewRepository, "scoped_reviews", ambiguous)
    service, _, aq = queries(env)
    with pytest.raises(ResearchBaseError, match="ambiguous") as error:
        service.get_manuscript_audit(env[3], aq)
    assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
