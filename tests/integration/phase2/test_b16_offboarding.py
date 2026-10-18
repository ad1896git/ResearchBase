"""Narrow direct-self permission survives offboarding without project disclosure."""

from dataclasses import fields, replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.prepared_submission import GetOwnAuthorConsentQuery
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

b04_env = _b04_env
b15_env = _b15_env
conclusion_env = _conclusion_env


def offboard(env, *, membership=False):
    from researchbase.application.phase2_identity import CloseProjectRole, EndProjectMembership
    from tests.integration.phase2.test_pr2_00_challenges import _service

    _, command, actor, _, engine, *_ = env
    identity, _, _ = _service(engine.url.render_as_string(hide_password=False))
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT id,membership_id FROM project_role_assignments "
                "WHERE actor_id=:actor AND role='OWNER' AND effective_until IS NULL"
            ),
            {"actor": actor.actor_id},
        ).one()
    if membership:
        identity.end_project_membership(
            EndProjectMembership(actor, command.project_id, row.membership_id, "offboard", uuid4())
        )
    else:
        identity.close_project_role(
            CloseProjectRole(actor, command.project_id, row.id, "offboard", uuid4())
        )


@pytest.mark.parametrize("membership", [False, True])
def test_own_withdraw_read_after_offboarding_reuses_evidence_without_bytes(b15_env, membership):
    service, command, actor, _, _, store, _ = b15_env
    package, query, cmd, root = rooted(b15_env)
    offboard(b15_env, membership=membership)

    def unavailable(*args):
        raise AssertionError("narrow own path must not access ArtifactStore")

    store.open = unavailable
    withdrawn = service.record_author_consent(actor, successor(cmd, root))
    own = service.get_own_author_consent(
        actor, GetOwnAuthorConsentQuery(command.project_id, package.id, root.id)
    )
    assert own.consent == root and own.current_head == withdrawn
    assert {f.name for f in fields(own)} == {"consent", "current_head"}
    for read in (
        service.get_prepared_submission,
        service.preview_prepared_submission,
        service.get_prepared_submission_history,
    ):
        with pytest.raises(ResearchBaseError) as exc:
            read(actor, query)
        assert exc.value.code == ErrorCode.FORBIDDEN
    with pytest.raises(ResearchBaseError) as exc:
        service.record_author_consent(actor, successor(cmd, withdrawn, "GRANTED"))
    assert exc.value.code == ErrorCode.FORBIDDEN
    with pytest.raises(ResearchBaseError) as exc:
        service.record_author_consent(
            actor, replace(successor(cmd, withdrawn), evidence_artifact_version_id=uuid4())
        )
    assert exc.value.code == ErrorCode.INVALID_STATE_TRANSITION


@pytest.mark.parametrize("missing", ["project_id", "prepared_submission_version_id", "id"])
def test_absent_and_foreign_routing_sanitized(b15_env, b04_env, missing):
    service, command, actor, *_ = b15_env
    package, _, _, root = rooted(b15_env)
    query = GetOwnAuthorConsentQuery(command.project_id, package.id, root.id)
    with pytest.raises(ResearchBaseError) as exc:
        service.get_own_author_consent(actor, replace(query, **{missing: uuid4()}))
    assert (exc.value.code, exc.value.message) == (ErrorCode.FORBIDDEN, "own consent unavailable")
    with pytest.raises(ResearchBaseError) as exc:
        service.get_own_author_consent(b04_env[-1][4], query)
    assert (exc.value.code, exc.value.message) == (ErrorCode.FORBIDDEN, "own consent unavailable")


def test_missing_and_revoked_credentials(b15_env):
    service, command, actor, *_ = b15_env
    package, _, _, root = rooted(b15_env)
    query = GetOwnAuthorConsentQuery(command.project_id, package.id, root.id)
    with pytest.raises(ResearchBaseError) as exc:
        service.get_own_author_consent(None, query)
    assert exc.value.code == ErrorCode.AUTHENTICATION_REQUIRED

    class Revoked:
        def is_valid(self, principal, at):
            return False

    service._credentials = Revoked()
    with pytest.raises(ResearchBaseError) as exc:
        service.get_own_author_consent(actor, query)
    assert exc.value.code == ErrorCode.FORBIDDEN


def test_inactive_project_and_upstream_admission_do_not_block_revocation(b15_env, monkeypatch):
    service, command, actor, _, engine, *_ = b15_env
    package, _, cmd, root = rooted(b15_env)
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE projects SET lifecycle_status='ARCHIVED' WHERE id=:id"),
            {"id": command.project_id},
        )

    def no_scientific_admission(*args, **kwargs):
        raise AssertionError("withdrawal must not rerun scientific admission")

    monkeypatch.setattr(service, "_context", no_scientific_admission)
    monkeypatch.setattr(service, "_stage", no_scientific_admission)
    withdrawn = service.record_author_consent(actor, successor(cmd, root))
    own = service.get_own_author_consent(
        actor, GetOwnAuthorConsentQuery(command.project_id, package.id, root.id)
    )
    assert own.current_head == withdrawn


def test_new_evidence_requires_current_entitlement(b15_env):
    service, _, actor, *_ = b15_env
    _, _, cmd, root = rooted(b15_env)
    offboard(b15_env)
    with pytest.raises(ResearchBaseError) as exc:
        service.record_author_consent(
            actor, replace(successor(cmd, root), evidence_artifact_version_id=uuid4())
        )
    assert exc.value.code == ErrorCode.FORBIDDEN


@pytest.mark.parametrize("invalid_identity", ["retired", "revoked_binding", "wrong_actor"])
def test_live_direct_identity_is_required_even_for_retained_evidence(b15_env, invalid_identity):
    service, command, actor, _, engine, *_ = b15_env
    package, _, cmd, root = rooted(b15_env)
    if invalid_identity == "retired":
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE actors SET retired_at=clock_timestamp() WHERE id=:id"),
                {"id": actor.actor_id},
            )
    elif invalid_identity == "revoked_binding":
        from researchbase.application.phase2_identity import RevokeActorSubjectBinding
        from tests.integration.phase2.test_pr2_00_challenges import _service

        identity, operator, _ = _service(engine.url.render_as_string(hide_password=False))
        with engine.connect() as conn:
            binding = conn.execute(
                text(
                    "SELECT id,operator_credential_id FROM actor_subject_bindings "
                    "WHERE actor_id=:id AND subject_credential_id=:credential"
                ),
                {"id": actor.actor_id, "credential": actor.credential_id},
            ).one()
        operator = replace(operator, credential_id=binding.operator_credential_id)
        identity.revoke_actor_subject_binding(
            RevokeActorSubjectBinding(operator, binding.id, "revoke identity", uuid4())
        )
    else:
        actor = replace(actor, actor_id=uuid4())
    for operation in (
        lambda: service.record_author_consent(actor, successor(cmd, root)),
        lambda: service.get_own_author_consent(
            actor, GetOwnAuthorConsentQuery(command.project_id, package.id, root.id)
        ),
    ):
        with pytest.raises(ResearchBaseError) as exc:
            operation()
        assert exc.value.code == ErrorCode.FORBIDDEN
