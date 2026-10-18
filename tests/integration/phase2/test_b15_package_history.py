"""B15 accepted B04/S1 fixtures and exact PREPARED Application lifecycle."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.prepared_submission import (
    GetAuthorConsentQuery,
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


def test_missing_evidence_diagnostic_and_withdrawal(b15_env):
    service, command, actor, _, _, store, _ = b15_env
    result, query = prepared(b15_env)
    consent = consent_command(b15_env, result.id)
    root = service.record_author_consent(actor, consent)
    # Exercise storage unavailability without altering canonical metadata.
    original = store.open

    def unavailable(digest):
        if str(digest) == root.evidence_artifact.content_hash:
            raise FileNotFoundError()
        return original(digest)

    store.open = unavailable
    preview = service.preview_prepared_submission(actor, query)
    assert "DEPENDENCY_UNAVAILABLE" in preview.validity_reasons
    assert preview.candidate_manifest_hash is None
    with pytest.raises(ResearchBaseError) as exc:
        service.get_author_consent(actor, GetAuthorConsentQuery(command.project_id, root.id))
    assert exc.value.code == ErrorCode.FROZEN_REFERENCE_REQUIRED
    event = service.withdraw_prepared_submission(
        actor, WithdrawPreparedSubmissionCommand(command.project_id, result.id, "retain history")
    )
    assert event.new_status == "WITHDRAWN"


def test_byte_corruption_fails_closed(b15_env):
    service, command, actor, _, _, store, _ = b15_env
    result, query = prepared(b15_env)
    root = service.record_author_consent(actor, consent_command(b15_env, result.id))
    original = store.open

    def corrupt(digest):
        return b"changed" if digest == root.evidence_artifact.content_hash else original(digest)

    store.open = corrupt
    with pytest.raises(ResearchBaseError) as exc:
        service.preview_prepared_submission(actor, query)
    assert exc.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_authorized_absent_and_foreign_project_nondisclosure(b15_env):
    service, command, actor, *_ = b15_env
    result, query = prepared(b15_env)
    with pytest.raises(ResearchBaseError) as exc:
        service.get_prepared_submission(
            actor, replace(query, prepared_submission_version_id=uuid4())
        )
    assert exc.value.code == ErrorCode.NOT_FOUND
    with pytest.raises(ResearchBaseError) as exc:
        service.get_prepared_submission(actor, replace(query, project_id=uuid4()))
    assert exc.value.code == ErrorCode.FORBIDDEN


def test_missing_manuscript_bytes_diagnoses_without_repair(b15_env):
    service, command, actor, _, engine, store, _ = b15_env
    result, query = prepared(b15_env)
    with engine.connect() as conn:
        document = conn.execute(
            text(
                "SELECT a.content_hash FROM manuscript_versions m JOIN artifact_versions a "
                "ON a.id=m.document_artifact_version_id WHERE m.id=:id"
            ),
            {"id": result.manuscript_version_id},
        ).scalar_one()
    original = store.open

    def unavailable(identity):
        if identity.removeprefix("sha256:") == document:
            raise PermissionError("storage unavailable")
        return original(identity)

    store.open = unavailable
    read = service.get_prepared_submission(actor, query)
    assert "DEPENDENCY_UNAVAILABLE" in read.validity_reasons
    assert read.content_hash is None
    event = service.withdraw_prepared_submission(
        actor,
        WithdrawPreparedSubmissionCommand(command.project_id, result.id, "retain missing upstream"),
    )
    assert event.new_status == "WITHDRAWN"


@pytest.mark.parametrize("validity", ["stale", "invalid"])
def test_current_invalidity_is_diagnostic_and_withdrawal_remains_possible(b15_env, validity):
    from researchbase.application.governance import (
        CreateAuditFindingCommand,
        CreateImpactAssessmentCommand,
        GovernanceService,
        ProposedImpactTarget,
    )
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock

    service, command, actor, factory, engine, *_ = b15_env
    package, query = prepared(b15_env)
    with engine.connect() as conn:
        document = conn.execute(
            text("SELECT document_artifact_version_id FROM manuscript_versions WHERE id=:id"),
            {"id": package.manuscript_version_id},
        ).scalar_one()
    governance = GovernanceService(factory, SystemClock())
    context = ExecutionContext(actor_id=actor.actor_id, request_id=uuid4(), client_type="test")
    finding = governance.create_audit_finding(
        CreateAuditFindingCommand(
            command.project_id,
            "code_bug",
            "major",
            "Later document finding",
            "Recheck",
            "artifact_version",
            document,
            context,
        )
    )
    governance.create_impact_assessment(
        CreateImpactAssessmentCommand(
            command.project_id,
            finding.id,
            {"test": "upstream validity"},
            validity,
            (ProposedImpactTarget("artifact_version", document, validity),),
            context,
        )
    )
    saved = service.get_prepared_submission(actor, query)
    assert saved.current_validity == validity.upper()
    assert "UPSTREAM_" + validity.upper() in saved.validity_reasons
    assert service.prepare_submission(actor, command) == saved
    assert service.preview_prepared_submission(actor, query).candidate_manifest_hash is None
    with pytest.raises(ResearchBaseError) as exc:
        service.prepare_submission(actor, replace(command, id=uuid4()))
    assert exc.value.code == ErrorCode.INVALID_STATE_TRANSITION
    event = service.withdraw_prepared_submission(
        actor, WithdrawPreparedSubmissionCommand(command.project_id, package.id, "end eligibility")
    )
    assert event.new_status == "WITHDRAWN"


def test_missing_source_bytes_retains_metadata_diagnostic(b04_env):
    from researchbase.application.manuscript_placement import CitationPlacementService
    from tests.integration.phase2.b15_support import build_env

    _, q, actor, factory, engine, credentials, store, _, base = b04_env
    CitationPlacementService(factory, credentials).add(
        actor,
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        base[7],
        "INTRO",
        {"kind": "PARAGRAPH", "value": "source"},
        "BACKGROUND",
        0,
        uuid4(),
    )
    env = build_env(b04_env)
    service = env[0]
    package, query = prepared(env)
    with engine.connect() as conn:
        document = conn.execute(
            text(
                "SELECT a.content_hash FROM source_versions s JOIN artifact_versions a "
                "ON a.id=s.fulltext_artifact_version_id WHERE s.id=:id"
            ),
            {"id": base[7]},
        ).scalar_one()
    original = store.open

    def unavailable(identity):
        if identity.removeprefix("sha256:") == document:
            raise FileNotFoundError()
        return original(identity)

    store.open = unavailable
    result = service.get_prepared_submission(actor, query)
    assert result.items == package.items and "DEPENDENCY_UNAVAILABLE" in result.validity_reasons


def test_readback_utc_in_non_utc_database_session(b15_env):
    from datetime import timedelta

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from researchbase.application.prepared_submission import PreparedSubmissionService
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    service, command, actor, _, engine, store, credentials = b15_env
    package, query = prepared(b15_env)
    root = service.record_author_consent(actor, consent_command(b15_env, package.id))
    other = create_engine(engine.url, connect_args={"options": "-c timezone=America/New_York"})
    sf = sessionmaker(other, expire_on_commit=False, autoflush=False)
    reader = PreparedSubmissionService(lambda: SqlAlchemyUnitOfWork(sf), credentials, store)
    try:
        saved = reader.get_prepared_submission(actor, query)
        assert saved.created_at.utcoffset() == timedelta(0)
        assert saved.events[0].occurred_at.utcoffset() == timedelta(0)
        assert saved.consents[0].captured_at.utcoffset() == timedelta(0)
        assert saved.consents[0].id == root.id
    finally:
        other.dispose()
