"""Completed exact replay uses narrow current permission and never repeats effects."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.prepared_submission import PreparedSubmissionService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b16_fixtures import (  # noqa: F401
    b04_env as _b04_env,
)
from tests.integration.phase2.b16_fixtures import (
    b15_env as _b15_env,
)
from tests.integration.phase2.b16_fixtures import (
    conclusion_env as _conclusion_env,
)
from tests.integration.phase2.b16_fixtures import (
    rooted,
    successor,
)
from tests.integration.phase2.test_b16_offboarding import offboard

b04_env = _b04_env
b15_env = _b15_env
conclusion_env = _conclusion_env


def test_withdrawal_restart_replay_after_role_loss_and_old_head_loses(b15_env):
    service, _, actor, factory, engine, store, credentials = b15_env
    _, _, cmd, root = rooted(b15_env)
    withdraw = successor(cmd, root)
    saved = service.record_author_consent(actor, withdraw)
    offboard(b15_env)
    restarted = PreparedSubmissionService(factory, credentials, store)
    assert restarted.record_author_consent(actor, withdraw) == saved
    with pytest.raises(ResearchBaseError) as exc:
        restarted.record_author_consent(actor, replace(withdraw, id=uuid4()))
    assert exc.value.code == ErrorCode.CONCURRENT_MODIFICATION
    with pytest.raises(ResearchBaseError) as exc:
        restarted.record_author_consent(
            actor, replace(withdraw, evidence_artifact_version_id=uuid4())
        )
    assert exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    with pytest.raises(ResearchBaseError) as exc:
        restarted.record_author_consent(actor, cmd)
    assert exc.value.code == ErrorCode.FORBIDDEN
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM author_consents")).scalar_one() == 2
        assert conn.execute(text("SELECT count(*) FROM approval_grant_events")).scalar_one() == 0


def test_completed_withdrawal_replay_does_not_require_upstream_admission(b15_env, monkeypatch):
    service, _, actor, *_ = b15_env
    _, _, cmd, root = rooted(b15_env)
    withdraw = successor(cmd, root)
    saved = service.record_author_consent(actor, withdraw)

    def no_admission(*args, **kwargs):
        raise AssertionError("completed withdrawal cannot rerun scientific admission")

    monkeypatch.setattr(service, "_context", no_admission)
    monkeypatch.setattr(service, "_stage", no_admission)
    assert service.record_author_consent(actor, withdraw) == saved
