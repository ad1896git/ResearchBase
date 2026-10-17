"""B12 conservative admission with real frozen manuscripts; no READY bypass."""

from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.decision import (
    RecordPrepareSubmissionDecisionCommand,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_b11_readiness_decision import (
    b04_env,
    b05_env,
    conclusion_env,
    create,
    phase2_database_url,
    seal,
)
from tests.integration.phase2.test_revision_action import decision_env, revision_env

_FIXTURES = (b04_env, b05_env, conclusion_env, phase2_database_url, decision_env, revision_env)
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


def prepare_command(env):
    return RecordPrepareSubmissionDecisionCommand(
        uuid4(), env[1].project_id, env[1].manuscript_version_id, "Prepare?", "Independent judgment"
    )


@pytest.mark.parametrize("purpose", ["READY_FOR_SUBMISSION", "PREPARE_SUBMISSION"])
def test_readiness_decision_cannot_authorize_prepare(b05_env, purpose):
    from researchbase.application.approval import ApprovalService, RequestApprovalCommand
    from researchbase.application.literature_evidence import LiteratureEvidenceService
    from tests.integration.phase2.test_b11_readiness_decision import record

    env = b05_env
    seal(env)
    review = create(env)
    ready = record(env)
    approval = ApprovalService(env[4], env[9], LiteratureEvidenceService(env[4], env[9], env[7]))
    cmd = RequestApprovalCommand(
        uuid4(),
        env[1].project_id,
        None,
        ready.id,
        (review.id,),
        approval_purpose=purpose,
        manuscript_version_id=env[1].manuscript_version_id,
    )
    with pytest.raises(ResearchBaseError) as exc:
        approval.request_approval(env[2], cmd)
    assert exc.value.code == ErrorCode.DECISION_BASIS_INVALID
    with env[5].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM approval_requests")).scalar_one() == 0


@pytest.mark.parametrize(
    "count,code", [(100, ErrorCode.DECISION_BASIS_INVALID), (101, ErrorCode.VALIDATION_ERROR)]
)
def test_approval_review_limit_does_not_truncate(b05_env, count, code):
    from researchbase.application.approval import ApprovalService, RequestApprovalCommand
    from researchbase.application.literature_evidence import LiteratureEvidenceService

    env = b05_env
    seal(env)
    cmd = RequestApprovalCommand(
        uuid4(),
        env[1].project_id,
        None,
        uuid4(),
        tuple(uuid4() for _ in range(count)),
        approval_purpose="PREPARE_SUBMISSION",
        manuscript_version_id=env[1].manuscript_version_id,
    )
    approval = ApprovalService(env[4], env[9], LiteratureEvidenceService(env[4], env[9], env[7]))
    with pytest.raises(ResearchBaseError) as exc:
        approval.request_approval(env[2], cmd)
    assert exc.value.code == code
    assert len(cmd.review_ids) == count
