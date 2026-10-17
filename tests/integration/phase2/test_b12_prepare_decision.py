"""B12 conservative admission with real frozen manuscripts; no READY bypass."""

from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.decision import (
    GetPrepareSubmissionDecisionQuery,
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
    service,
)
from tests.integration.phase2.test_revision_action import decision_env, revision_env

_FIXTURES = (b04_env, b05_env, conclusion_env, phase2_database_url, decision_env, revision_env)
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


def prepare_command(env):
    return RecordPrepareSubmissionDecisionCommand(
        uuid4(), env[1].project_id, env[1].manuscript_version_id, "Prepare?", "Independent judgment"
    )


@pytest.mark.parametrize("review", [None, "ACCEPT", "REJECT", "UNCERTAIN"])
def test_unavailable_ready_lifecycle_denies_atomically(b05_env, review):
    env = b05_env
    seal(env)
    if review:
        create(env, recommendation=review)
    with pytest.raises(ResearchBaseError) as exc:
        service(env).record_prepare_submission_decision(env[3], prepare_command(env))
    assert exc.value.code == ErrorCode.INVALID_STATE_TRANSITION
    with env[5].connect() as conn:
        assert (
            conn.execute(
                text("SELECT lifecycle_status FROM publications WHERE id=:id"),
                {"id": env[1].publication_id},
            ).scalar_one()
            == "DRAFTING"
        )
        for table in (
            "decision_records",
            "approval_requests",
            "approval_decisions",
            "approval_grants",
        ):
            assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0


def test_unsealed_manuscript_denies(b05_env):
    with pytest.raises(ResearchBaseError) as exc:
        service(b05_env).record_prepare_submission_decision(b05_env[3], prepare_command(b05_env))
    assert exc.value.code == ErrorCode.FROZEN_REFERENCE_REQUIRED


def test_readiness_history_is_not_prepare_history(b05_env):
    from tests.integration.phase2.test_b11_readiness_decision import record

    env = b05_env
    seal(env)
    create(env)
    ready = record(env)
    with pytest.raises(ResearchBaseError) as exc:
        service(env).get_prepare_submission_decision(
            env[3], GetPrepareSubmissionDecisionQuery(env[1].project_id, ready.id)
        )
    assert exc.value.code == ErrorCode.NOT_FOUND
