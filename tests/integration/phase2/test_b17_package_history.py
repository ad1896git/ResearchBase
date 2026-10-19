"""Exact frozen material survives supersession, OWNER and author withdrawal."""

# Literal SQL retains exact artifact selection.
# ruff: noqa: E501

from dataclasses import replace
from uuid import uuid4

import pytest

from researchbase.application.prepared_submission import (
    PreparedSubmissionService,
    RecordAuthorConsentCommand,
    WithdrawPreparedSubmissionCommand,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b17_fixtures import (
    b04_env,
    b05_env,
    b17_env,
    conclusion_env,
    decision_env,
    next_package,
    phase2_database_url,
    revision_env,
    withdraw_consent,
)

_FIXTURES = (
    b04_env,
    b05_env,
    b17_env,
    conclusion_env,
    decision_env,
    phase2_database_url,
    revision_env,
)
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


def test_exact_after_restart_and_later_author_withdrawal(b17_env):
    f = b17_env
    receipt = f.app.freeze_prepared_submission(f.actor, f.command)
    saved = f.app.get_prepared_submission(f.actor, f.query)
    withdrawn = withdraw_consent(f)
    restarted = PreparedSubmissionService(f.env[4], f.env[9], f.env[7])
    current = restarted.get_prepared_submission(f.actor, f.query)
    assert current.current_validity == "STALE" and "CONSENT_WITHDRAWN" in current.validity_reasons
    assert (
        current.items,
        current.content_hash,
        current.package_manifest_hash,
        current.frozen_at,
        current.events,
    ) == (
        saved.items,
        saved.content_hash,
        saved.package_manifest_hash,
        saved.frozen_at,
        saved.events,
    )
    preview = restarted.preview_prepared_submission(f.actor, f.query)
    assert (
        preview.items == saved.items
        and preview.candidate_manifest_hash == saved.package_manifest_hash
    )
    assert restarted.freeze_prepared_submission(f.actor, f.command) == receipt
    with pytest.raises(ResearchBaseError) as exc:
        restarted.record_author_consent(
            f.actor,
            RecordAuthorConsentCommand(
                uuid4(),
                f.command.project_id,
                f.command.result_id,
                "GRANTED",
                "PREPARED_PACKAGE",
                f.consent.evidence_artifact.id,
                withdrawn.id,
            ),
        )
    assert exc.value.code == ErrorCode.INVALID_STATE_TRANSITION


@pytest.mark.parametrize("sealed", [False, True])
def test_owner_withdrawal_retains_seal_and_exact_terminal_replay(b17_env, sealed):
    f = b17_env
    if sealed:
        f.app.freeze_prepared_submission(f.actor, f.command)
    saved = f.app.get_prepared_submission(f.actor, f.query)
    command = WithdrawPreparedSubmissionCommand(
        f.command.project_id, f.command.result_id, "Owner stops preparation"
    )
    event = f.app.withdraw_prepared_submission(f.env[3], command)
    assert event.prior_status == ("FROZEN" if sealed else "PREPARED")
    current = f.app.get_prepared_submission(f.actor, f.query)
    assert current.status == "WITHDRAWN" and current.current_validity == "STALE"
    assert current.content_hash == saved.content_hash and current.items == saved.items
    assert f.app.withdraw_prepared_submission(f.env[3], command) == event
    with pytest.raises(ResearchBaseError) as exc:
        f.app.freeze_prepared_submission(f.actor, replace(f.command, command_key=uuid4()))
    assert exc.value.code == (
        ErrorCode.GRANT_INVALID if sealed else ErrorCode.INVALID_STATE_TRANSITION
    )


def test_newer_freeze_supersedes_atomically_and_older_freeze_is_denied(b17_env):
    f = b17_env
    newer = next_package(f)
    f.app.freeze_prepared_submission(f.actor, f.command)
    original = f.app.get_prepared_submission(f.actor, f.query)
    newer.app.freeze_prepared_submission(newer.actor, newer.command)
    old = f.app.get_prepared_submission(f.actor, f.query)
    assert old.status == "SUPERSEDED" and old.current_validity == "VALID"
    assert (
        old.row_version == 3
        and old.content_hash == original.content_hash
        and old.items == original.items
    )
    assert old.events[-1].new_status == "SUPERSEDED"
    with pytest.raises(ResearchBaseError) as exc:
        f.app.withdraw_prepared_submission(
            f.env[3],
            WithdrawPreparedSubmissionCommand(
                f.command.project_id, f.command.result_id, "terminal"
            ),
        )
    assert exc.value.code == ErrorCode.INVALID_STATE_TRANSITION


def test_freezing_older_package_after_newer_is_denied(b17_env):
    f = b17_env
    newer = next_package(f)
    newer.app.freeze_prepared_submission(newer.actor, newer.command)
    with pytest.raises(ResearchBaseError) as exc:
        f.app.freeze_prepared_submission(f.actor, f.command)
    assert exc.value.code == ErrorCode.INVALID_STATE_TRANSITION
    assert f.app.get_prepared_submission(f.actor, f.query).status == "PREPARED"


@pytest.mark.parametrize("kind", ["document", "consent"])
def test_missing_retained_bytes_never_report_frozen_closure_valid(b17_env, kind):
    from sqlalchemy import text

    f = b17_env
    f.app.freeze_prepared_submission(f.actor, f.command)
    saved = f.app.get_prepared_submission(f.actor, f.query)
    if kind == "consent":
        digest = f.consent.evidence_artifact.content_hash
    else:
        with f.engine.connect() as conn:
            digest = conn.execute(
                text(
                    "SELECT a.content_hash FROM manuscript_versions m JOIN artifact_versions a ON a.id=m.document_artifact_version_id WHERE m.id=:id"
                ),
                {"id": f.package_command.manuscript_version_id},
            ).scalar_one()
    f.env[7]._path_for(digest).unlink()
    current = f.app.get_prepared_submission(f.actor, f.query)
    assert (
        current.current_validity == "STALE" and "DEPENDENCY_UNAVAILABLE" in current.validity_reasons
    )
    assert (current.content_hash, current.items, current.frozen_at) == (
        saved.content_hash,
        saved.items,
        saved.frozen_at,
    )
