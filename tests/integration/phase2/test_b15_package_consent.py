"""B15 accepted B04/S1 fixtures and exact PREPARED Application lifecycle."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.prepared_submission import (
    GetAuthorConsentQuery,
    PreparedSubmissionService,
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


def test_root_consent_preview_is_transient_and_restart(b15_env):
    service, command, actor, factory, engine, store, credentials = b15_env
    result, query = prepared(b15_env)
    assert service.preview_prepared_submission(actor, query).candidate_manifest_hash is None
    consent = consent_command(b15_env, result.id)
    saved = service.record_author_consent(actor, consent)
    assert service.record_author_consent(actor, consent) == saved
    assert (
        service.get_author_consent(actor, GetAuthorConsentQuery(command.project_id, saved.id))
        == saved
    )
    restarted = PreparedSubmissionService(factory, credentials, store)
    preview = restarted.preview_prepared_submission(actor, query)
    assert preview.candidate_manifest_hash and preview.missing_author_ids == ()
    assert [(i.id, i.category, i.ordinal) for i in preview.items] == [
        (saved.id, "AUTHOR_CONSENT", 0)
    ]
    assert preview.current_validity == "NOT_FROZEN"
    with engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM prepared_submission_manifest_items")
            ).scalar_one()
            == 0
        )
        assert (
            conn.execute(text("SELECT count(*) FROM approval_grant_consumptions")).scalar_one() == 0
        )
    with pytest.raises(ResearchBaseError) as exc:
        service.record_author_consent(actor, replace(consent, id=uuid4()))
    assert exc.value.code == ErrorCode.CONCURRENT_MODIFICATION


def test_unfrozen_or_missing_evidence_and_withdrawn_new_root(b15_env):
    service, command, actor, *_ = b15_env
    result, _ = prepared(b15_env)
    consent = consent_command(b15_env, result.id)
    with pytest.raises(ResearchBaseError) as exc:
        service.record_author_consent(actor, replace(consent, evidence_artifact_version_id=uuid4()))
    assert exc.value.code == ErrorCode.FORBIDDEN
    service.withdraw_prepared_submission(
        actor, WithdrawPreparedSubmissionCommand(command.project_id, result.id, "end preparation")
    )
    with pytest.raises(ResearchBaseError) as exc:
        service.record_author_consent(actor, consent)
    assert exc.value.code == ErrorCode.INVALID_STATE_TRANSITION


def test_viewer_author_consent_and_replays_after_owner_loss(b15_env, b04_env):
    from researchbase.application.phase2_identity import AssignProjectRole, CloseProjectRole
    from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service

    service, command, actor, _, engine, *_ = b15_env
    result, query = prepared(b15_env)
    consent = consent_command(b15_env, result.id)
    identity, _, _ = identity_service(engine.url.render_as_string(hide_password=False))
    identity.assign_project_role(
        AssignProjectRole(
            actor, command.project_id, actor.actor_id, "VIEWER", "read entitlement", uuid4()
        )
    )
    with engine.connect() as conn:
        role = conn.execute(
            text(
                "SELECT id FROM project_role_assignments WHERE actor_id=:actor "
                "AND role='OWNER' AND effective_until IS NULL"
            ),
            {"actor": actor.actor_id},
        ).scalar_one()
    # The accepted fixture already retains another OWNER.
    identity.close_project_role(
        CloseProjectRole(actor, command.project_id, role, "writer loss", uuid4())
    )
    root = service.record_author_consent(actor, consent)
    assert root.actor_id == actor.actor_id
    assert service.prepare_submission(actor, command).id == result.id
    assert service.record_author_consent(actor, consent) == root
    with pytest.raises(ResearchBaseError) as exc:
        service.prepare_submission(actor, replace(command, id=uuid4()))
    assert exc.value.code == ErrorCode.FORBIDDEN
    with pytest.raises(ResearchBaseError) as exc:
        service.withdraw_prepared_submission(
            actor,
            WithdrawPreparedSubmissionCommand(command.project_id, result.id, "owner required"),
        )
    assert exc.value.code == ErrorCode.FORBIDDEN


def test_owner_nonauthor_cannot_consent_for_author(b15_env, b04_env):
    service, _, _, *_ = b15_env
    result, _ = prepared(b15_env)
    other_owner = b04_env[-1][4]
    with pytest.raises(ResearchBaseError) as exc:
        service.record_author_consent(other_owner, consent_command(b15_env, result.id))
    assert exc.value.code == ErrorCode.FORBIDDEN


def test_multiple_authors_select_roots_in_authored_order(b04_env):
    from tests.integration.phase2.b15_support import build_env

    other = b04_env[-1][4]
    first = b04_env[2]
    env = build_env(b04_env, (other.actor_id, first.actor_id))
    service, _, _, *_ = env
    package, query = prepared(env)
    first_command = consent_command(env, package.id)
    first_root = service.record_author_consent(first, first_command)
    preview = service.preview_prepared_submission(first, query)
    assert preview.missing_author_ids == (other.actor_id,)
    assert preview.candidate_manifest_hash is None
    other_root = service.record_author_consent(other, replace(first_command, id=uuid4()))
    saved = service.get_prepared_submission(first, query)
    assert tuple(c.actor_id for c in saved.consents) == (other.actor_id, first.actor_id)
    preview = service.preview_prepared_submission(first, query)
    assert [(i.id, i.ordinal) for i in preview.items] == [(other_root.id, 0), (first_root.id, 1)]
    assert preview.candidate_manifest_hash is not None
