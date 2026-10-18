"""B16 real READY prerequisite and guarded Application grant builders."""

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


def ready_prerequisite(env, decider, requester, approver, review, *, consume=True):
    """Real B14a/B14r/B14 prerequisite, preserving all production guards."""
    from sqlalchemy import text

    from researchbase.application.approval import (
        ApprovalService,
        DecideApprovalCommand,
        RequestApprovalCommand,
    )
    from researchbase.application.decision import (
        DecisionService,
        RecordReadyForSubmissionDecisionCommand,
    )
    from researchbase.application.literature_evidence import LiteratureEvidenceService
    from researchbase.application.publication import (
        PublicationService,
        TransitionPublicationInternalReviewCommand,
        TransitionPublicationReadyCommand,
    )

    _, command, author, factory, engine, store, credentials = env

    # Consumption refreshes verification time; the test provider validates the
    # retained credential identity independently of that fresh timestamp.
    def credential_live(principal, at):
        saved = credentials.principals.get(principal.actor_id)
        return (
            credentials.enabled
            and saved is not None
            and saved.verified_at <= at
            and replace(principal, verified_at=saved.verified_at) == saved
        )

    credentials.is_valid = credential_live
    literature = LiteratureEvidenceService(factory, credentials, store)
    publication = PublicationService(factory, credentials, store)
    with engine.connect() as conn:
        digest = conn.execute(
            text("SELECT content_hash FROM manuscript_versions WHERE id=:id"),
            {"id": command.manuscript_version_id},
        ).scalar_one()
    publication.transition_publication_internal_review(
        author,
        TransitionPublicationInternalReviewCommand(
            uuid4(),
            command.project_id,
            command.publication_id,
            command.manuscript_version_id,
            digest,
        ),
    )
    basis = DecisionService(
        factory, credentials, literature, store
    ).record_ready_for_submission_decision(
        decider,
        RecordReadyForSubmissionDecisionCommand(
            uuid4(),
            command.project_id,
            command.manuscript_version_id,
            "Ready?",
            "Independent readiness basis",
        ),
    )
    approval = ApprovalService(factory, credentials, literature)
    request = RequestApprovalCommand(
        uuid4(),
        command.project_id,
        None,
        basis.id,
        (review.id,),
        approval_purpose="READY_FOR_SUBMISSION",
        manuscript_version_id=command.manuscript_version_id,
    )
    approval.request_approval(requester, request)
    grant = approval.decide_approval(
        approver,
        DecideApprovalCommand(
            uuid4(), command.project_id, request.id, "APPROVE", "Independent readiness permission"
        ),
    ).grant
    assert grant is not None
    transition = TransitionPublicationReadyCommand(
        uuid4(), command.project_id, grant.id, command.publication_id, (review.id,)
    )
    if consume:
        publication.transition_publication_ready(author, transition)
    return publication, transition, request


def grant_context(env, reviewer, *, consume_ready=True) -> dict[str, Any]:
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
    ready_app, ready_command, ready_request = ready_prerequisite(
        env, decider, requester, approver, review, consume=consume_ready
    )
    basis = (
        None
        if not consume_ready
        else DecisionService(
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
    )
    return dict(
        env=env,
        ready_app=ready_app,
        ready_command=ready_command,
        ready_request=ready_request,
        decider=decider,
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
