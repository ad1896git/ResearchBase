"""B15 accepted B04/S1 fixtures and exact PREPARED Application lifecycle."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.prepared_submission import (
    WithdrawPreparedSubmissionCommand,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b15_support import (  # noqa: F401
    b04_env as _b04_env,
)
from tests.integration.phase2.b15_support import (
    b15_env as _b15_env,
)
from tests.integration.phase2.b15_support import (
    conclusion_env as _conclusion_env,
)
from tests.integration.phase2.b15_support import (
    consent_command,
    prepared,
)

b04_env = _b04_env
b15_env = _b15_env
conclusion_env = _conclusion_env

pytestmark = pytest.mark.integration


def test_owner_withdrawal_preserves_context_and_replay(b15_env):
    service, command, actor, *_ = b15_env
    result, query = prepared(b15_env)
    consent = consent_command(b15_env, result.id)
    root = service.record_author_consent(actor, consent)
    withdraw = WithdrawPreparedSubmissionCommand(command.project_id, result.id, "e\u0301 reason")
    event = service.withdraw_prepared_submission(actor, withdraw)
    assert event.reason == "é reason"
    assert service.withdraw_prepared_submission(actor, withdraw) == event
    saved = service.get_prepared_submission(actor, query)
    assert saved.status == "WITHDRAWN" and saved.row_version == 2
    assert saved.consents == (root,) and len(saved.events) == 2
    assert saved.content_hash is saved.package_manifest_hash is saved.frozen_at is None
    assert service.prepare_submission(actor, command) == saved
    assert service.record_author_consent(actor, consent) == root
    assert service.preview_prepared_submission(actor, query).candidate_manifest_hash is None
    with pytest.raises(ResearchBaseError) as exc:
        service.withdraw_prepared_submission(actor, replace(withdraw, reason="changed"))
    assert exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT


@pytest.mark.parametrize("method", ["insert_package", "insert_event", "force_constraints"])
def test_preparation_failure_atomicity(b15_env, monkeypatch, method):
    from researchbase.persistence.prepared_submission_repository import (
        SqlAlchemyPreparedSubmissionRepository,
    )

    service, command, actor, _, engine, *_ = b15_env
    original = getattr(SqlAlchemyPreparedSubmissionRepository, method)

    def injected(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise RuntimeError("injected after effect")

    monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, method, injected)
    with pytest.raises(RuntimeError, match="injected"):
        service.prepare_submission(actor, command)
    with engine.connect() as conn:
        for table in (
            "prepared_submission_versions",
            "prepared_submission_manifest_items",
            "prepared_submission_events",
            "author_consents",
            "approval_grant_consumptions",
        ):
            assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0


@pytest.mark.parametrize("method", ["withdraw", "insert_event", "force_constraints"])
def test_withdrawal_failure_atomicity(b15_env, monkeypatch, method):
    from researchbase.persistence.prepared_submission_repository import (
        SqlAlchemyPreparedSubmissionRepository,
    )

    service, command, actor, _, engine, *_ = b15_env
    result, query = prepared(b15_env)
    original = getattr(SqlAlchemyPreparedSubmissionRepository, method)

    def injected(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise RuntimeError("injected after effect")

    monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, method, injected)
    with pytest.raises(RuntimeError, match="injected"):
        service.withdraw_prepared_submission(
            actor, WithdrawPreparedSubmissionCommand(command.project_id, result.id, "stop")
        )
    assert service.get_prepared_submission(actor, query) == result


@pytest.mark.parametrize("operation", ["prepare", "consent", "withdraw"])
def test_final_authorization_failure_rolls_back_effects(b15_env, monkeypatch, operation):
    from researchbase.persistence.prepared_submission_repository import (
        SqlAlchemyPreparedSubmissionRepository,
    )

    service, command, actor, _, engine, _, credentials = b15_env
    package = None
    if operation != "prepare":
        package, query = prepared(b15_env)
    consent = (
        consent_command(b15_env, package.id)
        if package is not None and operation == "consent"
        else None
    )
    original = SqlAlchemyPreparedSubmissionRepository.force_constraints

    def constraints(self):
        original(self)
        credentials.enabled = False

    monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, "force_constraints", constraints)
    with pytest.raises(ResearchBaseError) as exc:
        if operation == "prepare":
            service.prepare_submission(actor, command)
        elif operation == "consent":
            service.record_author_consent(actor, consent)
        else:
            assert package is not None
            service.withdraw_prepared_submission(
                actor, WithdrawPreparedSubmissionCommand(command.project_id, package.id, "withdraw")
            )
    assert exc.value.code == (
        ErrorCode.FORBIDDEN if operation == "consent" else ErrorCode.AUTHENTICATION_REQUIRED
    )
    credentials.enabled = True
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM author_consents")).scalar_one() == 0
        assert conn.execute(
            text("SELECT count(*) FROM prepared_submission_events")
        ).scalar_one() == (0 if operation == "prepare" else 1)
        assert (
            conn.execute(text("SELECT count(*) FROM approval_grant_consumptions")).scalar_one() == 0
        )
    if package:
        assert service.get_prepared_submission(actor, query) == package


def test_item_insert_failure_rolls_back_complete_package(b04_env, monkeypatch):
    from researchbase.application.manuscript_placement import ArtifactPlacementService
    from researchbase.persistence.prepared_submission_repository import (
        SqlAlchemyPreparedSubmissionRepository,
    )
    from tests.integration.phase2.b15_support import build_env
    from tests.integration.phase2.test_pr2_10_binding_contract import _artifact

    _, q, actor, factory, engine, credentials, store, *_ = b04_env
    target = _artifact(factory, store, actor, q.project_id, b"figure bytes", "figure")
    ArtifactPlacementService(factory, credentials).add(
        actor,
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        target,
        "FIGURES",
        {"kind": "ANCHOR", "value": "figure"},
        "FIGURE",
        0,
        uuid4(),
    )
    env = build_env(b04_env)
    original = SqlAlchemyPreparedSubmissionRepository.insert_item

    def fail(self, row):
        original(self, row)
        raise RuntimeError("after item insert")

    monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, "insert_item", fail)
    with pytest.raises(RuntimeError, match="after item"):
        env[0].prepare_submission(actor, env[1])
    with engine.connect() as conn:
        for table in (
            "prepared_submission_versions",
            "prepared_submission_manifest_items",
            "prepared_submission_events",
        ):
            assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0


def test_consent_insert_failure_retains_only_original_package(b15_env, monkeypatch):
    from researchbase.persistence.prepared_submission_repository import (
        SqlAlchemyPreparedSubmissionRepository,
    )

    service, _, actor, *_ = b15_env
    package, query = prepared(b15_env)
    cmd = consent_command(b15_env, package.id)
    original = SqlAlchemyPreparedSubmissionRepository.insert_consent

    def fail(self, row):
        original(self, row)
        raise RuntimeError("after root insert")

    monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, "insert_consent", fail)
    with pytest.raises(RuntimeError, match="after root"):
        service.record_author_consent(actor, cmd)
    assert service.get_prepared_submission(actor, query) == package
