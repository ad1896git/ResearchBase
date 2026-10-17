"""B12 conservative admission with real frozen manuscripts; no READY bypass."""

from uuid import uuid4

import pytest

from researchbase.application.decision import (
    GetPrepareSubmissionDecisionQuery,
    RecordPrepareSubmissionDecisionCommand,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_b11_readiness_decision import (
    b04_env,
    b05_env,
    conclusion_env,
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


def test_read_and_admission_preflight_have_no_exclusion_locks(b05_env):
    from sqlalchemy import event

    env = b05_env
    seal(env)
    sql = []

    def observe(conn, cursor, statement, parameters, context, executemany):
        sql.append(statement.upper())

    event.listen(env[5], "before_cursor_execute", observe)
    try:
        with pytest.raises(ResearchBaseError) as exc:
            service(env).get_prepare_submission_decision(
                env[3], GetPrepareSubmissionDecisionQuery(env[1].project_id, uuid4())
            )
        assert exc.value.code == ErrorCode.NOT_FOUND
    finally:
        event.remove(env[5], "before_cursor_execute", observe)
    assert sql
    assert not any(
        any(k in statement for k in ("LOCK TABLE", "PG_ADVISORY", "FOR UPDATE", "FOR SHARE"))
        for statement in sql
    )


def test_missing_read_entitlement_denies_before_lookup(b05_env):
    env = b05_env
    with pytest.raises(ResearchBaseError) as exc:
        service(env).get_prepare_submission_decision(
            None, GetPrepareSubmissionDecisionQuery(env[1].project_id, uuid4())
        )
    assert exc.value.code == ErrorCode.AUTHENTICATION_REQUIRED
