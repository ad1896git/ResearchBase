"""Current consent heads, retained context and exact empty-scope resolution."""

import pytest
from sqlalchemy import text

from researchbase.application.prepared_submission import WithdrawPreparedSubmissionCommand
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


def test_alternating_heads_preview_and_no_package_mutation(b15_env):
    service, command, actor, _, engine, *_ = b15_env
    package, query, cmd, root = rooted(b15_env)
    withdrawal = service.record_author_consent(actor, successor(cmd, root))
    assert withdrawal.prior_consent.id == root.id
    preview = service.preview_prepared_submission(actor, query)
    assert preview.missing_author_ids == (actor.actor_id,)
    assert preview.candidate_manifest_hash is None
    regrant = service.record_author_consent(actor, successor(cmd, withdrawal, "GRANTED"))
    preview = service.preview_prepared_submission(actor, query)
    assert preview.candidate_manifest_hash and preview.missing_author_ids == ()
    assert [i.target.id for i in preview.items if i.category == "AUTHOR_CONSENT"] == [regrant.id]
    result = service.get_prepared_submission(actor, query)
    assert [c.id for c in result.consents] == [root.id, withdrawal.id, regrant.id]
    assert (result.status, result.row_version, result.events) == (
        package.status,
        package.row_version,
        package.events,
    )
    assert result.content_hash is result.package_manifest_hash is result.frozen_at is None
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM approval_grant_events")).scalar_one() == 0
    with b15_env[3]() as uow:
        uow.begin_formal_read()
        assert uow.prepared_submission.related_grants(package.id, command.project_id) == ()


def test_author_can_withdraw_owner_withdrawn_package_but_cannot_regrant(b15_env):
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    service, command, actor, *_ = b15_env
    package, _, cmd, root = rooted(b15_env)
    service.withdraw_prepared_submission(
        actor, WithdrawPreparedSubmissionCommand(command.project_id, package.id, "owner end")
    )
    withdrawn = service.record_author_consent(actor, successor(cmd, root))
    with pytest.raises(ResearchBaseError) as exc:
        service.record_author_consent(actor, successor(cmd, withdrawn, "GRANTED"))
    assert exc.value.code == ErrorCode.INVALID_STATE_TRANSITION


@pytest.mark.parametrize(
    "case",
    [
        "exact_expired_active_staling_and_exclusions",
        "active_receipt_corruption",
        "same_manuscript_packages",
    ],
)
def test_real_prepare_grant_resolution(b15_env, b04_env, monkeypatch, case):
    from dataclasses import replace
    from datetime import timedelta
    from uuid import uuid4

    from researchbase.application.approval import EvaluateApprovalGrantCommand
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from researchbase.persistence.prepared_submission_repository import (
        SqlAlchemyPreparedSubmissionRepository,
    )
    from tests.integration.phase2.b15_support import consent_command
    from tests.integration.phase2.b16_fixtures import grant_context, issue_grant

    ctx = grant_context(b15_env, b04_env[-1][4])
    service, command, author, _, engine, *_ = b15_env
    if case == "active_receipt_corruption":
        grant = issue_grant(ctx)
        original = SqlAlchemyPreparedSubmissionRepository.related_grants

        def contradictory(self, package, project, *, contradiction=False):
            if contradiction:
                return (grant.id,)
            return original(self, package, project)

        monkeypatch.setattr(SqlAlchemyPreparedSubmissionRepository, "related_grants", contradictory)
        with pytest.raises(ResearchBaseError) as exc:
            service.record_author_consent(author, successor(ctx["consent"], ctx["root"]))
        assert exc.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
        with engine.connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM author_consents")).scalar_one() == 1
            assert (
                conn.execute(
                    text("SELECT status FROM approval_grants WHERE id=:id"), {"id": grant.id}
                ).scalar_one()
                == "ACTIVE"
            )
        return
    if case == "same_manuscript_packages":
        grant = issue_grant(ctx)
        second = service.prepare_submission(author, replace(command, id=uuid4()))
        cmd = consent_command(b15_env, second.id)
        root = service.record_author_consent(author, cmd)
        service.record_author_consent(author, successor(cmd, root))
        assert service.preview_prepared_submission(author, ctx["query"]).candidate_manifest_hash
        with engine.connect() as conn:
            assert (
                conn.execute(
                    text("SELECT status FROM approval_grants WHERE id=:id"), {"id": grant.id}
                ).scalar_one()
                == "STALE"
            )
        return
    with engine.connect() as conn:
        until = conn.execute(text("SELECT clock_timestamp()")).scalar_one() + timedelta(seconds=10)
    terminal = issue_grant(ctx, valid_until=until)
    expired = issue_grant(ctx, valid_until=until)
    active = issue_grant(ctx)
    with engine.connect() as conn:
        conn.execute(
            text(
                "SELECT pg_sleep(greatest(0,extract(epoch FROM (:until-clock_timestamp())))+0.02)"
            ),
            {"until": until},
        )
    ctx["approval"].evaluate_approval_grant(
        author, EvaluateApprovalGrantCommand(command.project_id, terminal.id)
    )
    withdrawn = service.record_author_consent(author, successor(ctx["consent"], ctx["root"]))
    with engine.connect() as conn:
        states = dict(conn.execute(text("SELECT id,status FROM approval_grants")).all())
        assert states == {terminal.id: "EXPIRED", expired.id: "STALE", active.id: "STALE"}
        events = conn.execute(
            text(
                "SELECT actor_id,occurred_at,reason FROM approval_grant_events "
                "WHERE new_status='STALE'"
            )
        ).all()
        assert len(events) == 2
        assert all(
            tuple(e)
            == (author.actor_id, withdrawn.captured_at, f"author consent withdrawn:{withdrawn.id}")
            for e in events
        )


def test_same_manuscript_packages_keep_independent_consent_heads(b15_env):
    from dataclasses import replace
    from uuid import uuid4

    from researchbase.application.prepared_submission import GetPreparedSubmissionQuery
    from tests.integration.phase2.b15_support import consent_command

    service, command, actor, *_ = b15_env
    first, first_query, first_cmd, first_root = rooted(b15_env)
    second = service.prepare_submission(actor, replace(command, id=uuid4()))
    second_root = service.record_author_consent(actor, consent_command(b15_env, second.id))
    service.record_author_consent(actor, successor(first_cmd, first_root))
    assert service.preview_prepared_submission(actor, first_query).missing_author_ids == (
        actor.actor_id,
    )
    query = GetPreparedSubmissionQuery(command.project_id, second.id)
    preview = service.preview_prepared_submission(actor, query)
    assert preview.missing_author_ids == () and preview.candidate_manifest_hash
    assert [i.target.id for i in preview.items if i.category == "AUTHOR_CONSENT"] == [
        second_root.id
    ]
    assert first.manuscript_version_id == second.manuscript_version_id


def test_real_prepare_grant_stales(b15_env, b04_env):
    from tests.integration.phase2.b16_fixtures import grant_context, issue_grant

    ctx = grant_context(b15_env, b04_env[-1][4])
    grant = issue_grant(ctx)
    assert grant.status == "ACTIVE"
    withdrawn = b15_env[0].record_author_consent(b15_env[2], successor(ctx["consent"], ctx["root"]))
    with b15_env[4].connect() as conn:
        assert (
            conn.execute(
                text("SELECT status FROM approval_grants WHERE id=:id"), {"id": grant.id}
            ).scalar_one()
            == "STALE"
        )
        assert (
            conn.execute(
                text(
                    "SELECT reason FROM approval_grant_events WHERE grant_id=:id "
                    "AND prior_status='ACTIVE'"
                ),
                {"id": grant.id},
            ).scalar_one()
            == f"author consent withdrawn:{withdrawn.id}"
        )
