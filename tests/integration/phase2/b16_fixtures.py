"""B16 disposable READY prerequisite and guarded Application grant builders."""

from dataclasses import replace
from typing import Any
from uuid import uuid4

from tests.integration.phase2.b15_support import (  # noqa: F401
    b04_env,
    b15_env,
    conclusion_env,
    consent_command,
    prepared,
)


def rooted(env):
    package, query = prepared(env)
    cmd = consent_command(env, package.id)
    root = env[0].record_author_consent(env[2], cmd)
    return package, query, cmd, root


def successor(command, prior, state="WITHDRAWN"):
    return replace(command, id=uuid4(), prior_consent_id=prior.id, consent_state=state)


def ready_prerequisite(env):
    """Owner-authorized disposable READY prerequisite, never a production transition.

    Keep every trigger enabled. Temporarily extend only the Publication guard for
    one exact presealed row, restore the function verbatim, and retain its original
    lifecycle CHECK as NOT VALID. All scientific/approval/grant guards stay intact.
    """
    from sqlalchemy import text

    _, command, _, _, engine, *_ = env
    with engine.begin() as conn:
        checks = conn.execute(
            text(
                "SELECT conname,pg_get_constraintdef(oid) AS definition FROM pg_constraint "
                "WHERE conrelid='publications'::regclass AND contype='c' "
                "AND pg_get_constraintdef(oid) LIKE '%lifecycle_status%'"
            )
        ).all()
        original = conn.execute(
            text("SELECT pg_get_functiondef('pr212_publication_guard()'::regprocedure)")
        ).scalar_one()
        extra = f"""BEGIN
        IF TG_OP='UPDATE' AND OLD.id='{command.publication_id}'::uuid
         AND OLD.lifecycle_status='DRAFTING' AND NEW.lifecycle_status='READY'
         AND (to_jsonb(NEW)-'lifecycle_status')=(to_jsonb(OLD)-'lifecycle_status')
         AND EXISTS(SELECT 1 FROM manuscript_versions WHERE id=NEW.current_manuscript_version_id
           AND publication_id=NEW.id AND status='FROZEN' AND frozen_at IS NOT NULL)
        THEN RETURN NEW; END IF;
        """
        for name, _ in checks:
            conn.exec_driver_sql(f'ALTER TABLE publications DROP CONSTRAINT "{name}"')
        conn.exec_driver_sql(original.replace("BEGIN", extra, 1))
        conn.execute(
            text("UPDATE publications SET lifecycle_status='READY' WHERE id=:id"),
            {"id": command.publication_id},
        )
        conn.exec_driver_sql(original)
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        for name, definition in checks:
            conn.exec_driver_sql(
                f'ALTER TABLE publications ADD CONSTRAINT "{name}" {definition} NOT VALID'
            )


def grant_context(env, reviewer) -> dict[str, Any]:
    from sqlalchemy import text

    from researchbase.application.approval import ApprovalService
    from researchbase.application.decision import (
        DecisionService,
        RecordPrepareSubmissionDecisionCommand,
    )
    from researchbase.application.internal_review import InternalReviewService
    from researchbase.application.literature_evidence import LiteratureEvidenceService
    from researchbase.application.phase2_identity import AssignProjectRole
    from tests.integration.phase2.test_pr2_00_challenges import _service
    from tests.integration.phase2.test_pr2_00_ownership import _add_owner

    service, command, author, factory, engine, store, credentials = env
    package, query, consent, root = rooted(env)
    literature = LiteratureEvidenceService(factory, credentials, store)
    review = InternalReviewService(factory, credentials, literature).create(
        reviewer,
        command.project_id,
        "MANUSCRIPT_VERSION",
        command.manuscript_version_id,
        "SCIENTIFIC",
        "ACCEPT",
        "Independent grant fixture review",
        (),
        uuid4(),
    )
    principals = []
    for _ in range(3):
        identity = uuid4()
        with engine.begin() as conn:
            at = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
            _add_owner(
                conn,
                actor_id=identity,
                project_id=command.project_id,
                now=at,
                event_kind="ACTIVATED",
                request_id=uuid4(),
            )
        principal = replace(
            author,
            actor_id=identity,
            deployment_id="test-deployment",
            subject_value=str(identity.int % 1_000_000),
            credential_id=f"uid:{identity.int}",
        )
        credentials.principals[identity] = principal
        principals.append(principal)
    decider, requester, approver = principals
    identity_service, _, _ = _service(engine.url.render_as_string(hide_password=False))
    identity_service.assign_project_role(
        AssignProjectRole(
            decider, command.project_id, approver.actor_id, "APPROVER", "B16 grant fixture", uuid4()
        )
    )
    ready_prerequisite(env)
    basis = DecisionService(
        factory, credentials, literature, store
    ).record_prepare_submission_decision(
        decider,
        RecordPrepareSubmissionDecisionCommand(
            uuid4(),
            command.project_id,
            command.manuscript_version_id,
            "Prepare?",
            "Independent preparation basis",
        ),
    )
    return dict(
        env=env,
        service=service,
        package=package,
        query=query,
        consent=consent,
        root=root,
        approval=ApprovalService(factory, credentials, literature),
        basis=basis,
        reviewer=reviewer,
        review=review,
        requester=requester,
        approver=approver,
    )


def grant_request(context):
    from researchbase.application.approval import RequestApprovalCommand

    command = context["env"][1]
    return RequestApprovalCommand(
        uuid4(),
        command.project_id,
        None,
        context["basis"].id,
        (context["review"].id,),
        approval_purpose="PREPARE_SUBMISSION",
        manuscript_version_id=command.manuscript_version_id,
    )


def issue_grant(context, request=None, *, valid_until=None):
    from datetime import timedelta

    from sqlalchemy import text

    from researchbase.application.approval import DecideApprovalCommand

    if valid_until is None:
        with context["env"][4].connect() as conn:
            valid_until = conn.execute(text("SELECT clock_timestamp()")).scalar_one() + timedelta(
                days=1
            )
    request = request or grant_request(context)
    context["approval"].request_approval(context["requester"], request)
    decision = context["approval"].decide_approval(
        context["approver"],
        DecideApprovalCommand(
            uuid4(),
            request.project_id,
            request.id,
            "APPROVE_WITH_CONDITIONS",
            "Direct fixture approval",
            valid_until=valid_until,
            requires_current_author_consent=True,
        ),
    )
    assert decision.grant is not None
    return decision.grant


def sql_withdrawal(conn, context):
    """Normal-role exact immutable consent insertion for adversarial final graphs."""
    from sqlalchemy import text

    from researchbase.domain.authorship import ExactReference
    from researchbase.domain.prepared_submission import consent_material
    from researchbase.foundation.hashing import sha256_canonical_json
    from tests.integration.phase2.test_pr2_17_authorship_schema import _insert

    root, actor = context["root"], context["env"][2]
    at = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
    identity = uuid4()
    _insert(
        conn,
        "author_consents",
        dict(
            id=identity,
            prepared_submission_version_id=context["package"].id,
            actor_id=actor.actor_id,
            consent_state="WITHDRAWN",
            consent_scope="PREPARED_PACKAGE",
            prior_consent_id=root.id,
            evidence_artifact_version_id=root.evidence_artifact.id,
            captured_at=at,
            created_at=at,
            created_by=actor.actor_id,
            hash_scheme="sha256-cjson-v1",
            content_hash=str(
                sha256_canonical_json(
                    consent_material(
                        context["package"].id,
                        actor.actor_id,
                        root.evidence_artifact,
                        "WITHDRAWN",
                        ExactReference("AuthorConsent", root.id, root.content_hash),
                    )
                )
            ),
        ),
    )
    return identity, at
