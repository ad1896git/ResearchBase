"""B17 complete graph through owning Application commands; no forged READY state."""

from dataclasses import dataclass
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.approval import (
    ApprovalService,
    DecideApprovalCommand,
    RequestApprovalCommand,
)
from researchbase.application.authorship import (
    AuthorshipService,
    CreateAuthorshipSnapshotCommand,
    RecordContributionCommand,
)
from researchbase.application.prepared_submission import (
    FreezePreparedSubmissionCommand,
    GetPreparedSubmissionQuery,
    PreparedSubmissionService,
    PrepareSubmissionCommand,
    RecordAuthorConsentCommand,
)
from tests.integration.phase2.test_b11_readiness_decision import service as decision_service
from tests.integration.phase2.test_b12_prepare_approval import prepare_command
from tests.integration.phase2.test_b14_publication_ready import issued
from tests.integration.phase2.test_b14r_ready_approval import (
    b04_env,
    b05_env,
    conclusion_env,
    decision_env,
    phase2_database_url,
    revision_env,
)
from tests.integration.phase2.test_pr2_10_binding_contract import _artifact

_FIXTURES = (b04_env, b05_env, conclusion_env, decision_env, phase2_database_url, revision_env)


@dataclass
class FreezeFixture:
    env: tuple
    app: PreparedSubmissionService
    command: FreezePreparedSubmissionCommand
    query: GetPreparedSubmissionQuery
    consent: object
    approval: ApprovalService
    approver: object
    ready_command: object
    package_command: PrepareSubmissionCommand

    @property
    def actor(self):
        return self.env[2]

    @property
    def engine(self):
        return self.env[5]


def build(env, *, consent=True, condition=True, lifetime=3600, extra_reviews=0, coauthors=()):
    publication, ready, approval, approver = issued(env)
    publication.transition_publication_ready(env[2], ready)
    from tests.integration.phase2.test_b05_manuscript_review import create

    for index in range(extra_reviews):
        create(env, summary=f"Additional sealed review {index}")
    basis = decision_service(env).record_prepare_submission_decision(env[3], prepare_command(env))
    reviews = tuple(r.id for r in basis.basis if r.type == "InternalReviewRecord")
    request = RequestApprovalCommand(
        uuid4(),
        env[1].project_id,
        None,
        basis.id,
        reviews,
        approval_purpose="PREPARE_SUBMISSION",
        manuscript_version_id=env[1].manuscript_version_id,
    )
    approval.request_approval(env[2], request)
    with env[5].connect() as conn:
        expiry = conn.execute(
            text("SELECT clock_timestamp()+(:seconds * interval '1 second')"), {"seconds": lifetime}
        ).scalar_one()
    grant = approval.decide_approval(
        approver,
        DecideApprovalCommand(
            uuid4(),
            request.project_id,
            request.id,
            "APPROVE_WITH_CONDITIONS" if condition else "APPROVE",
            "Independent package authorization",
            valid_until=expiry if condition else None,
            requires_current_author_consent=condition,
        ),
    ).grant
    assert grant is not None
    authorship = AuthorshipService(env[4], env[9])
    author = env[2]
    authors = (author, *coauthors)
    contributions = tuple(
        authorship.record_contribution(
            author,
            RecordContributionCommand(
                uuid4(),
                request.project_id,
                env[1].publication_id,
                principal.actor_id,
                "WRITING",
                "Direct authorship",
            ),
        )
        for principal in authors
    )
    snapshot = authorship.create_authorship_snapshot(
        author,
        CreateAuthorshipSnapshotCommand(
            uuid4(),
            request.project_id,
            env[1].publication_id,
            tuple(principal.actor_id for principal in authors),
            (author.actor_id,),
            (),
            tuple(contribution.id for contribution in contributions),
        ),
    )
    app = PreparedSubmissionService(env[4], env[9], env[7])
    package_command = PrepareSubmissionCommand(
        uuid4(),
        request.project_id,
        env[1].publication_id,
        env[1].manuscript_version_id,
        snapshot.id,
    )
    package = app.prepare_submission(author, package_command)
    query = GetPreparedSubmissionQuery(request.project_id, package.id)
    saved = None
    if consent:
        for principal in authors:
            evidence = _artifact(
                env[4], env[7], author, request.project_id, b"B17 direct author consent"
            )
            captured = app.record_author_consent(
                principal,
                RecordAuthorConsentCommand(
                    uuid4(),
                    request.project_id,
                    package.id,
                    "GRANTED",
                    "PREPARED_PACKAGE",
                    evidence,
                    None,
                ),
            )
            if principal == author:
                saved = captured
    preview = app.preview_prepared_submission(author, query)
    command = FreezePreparedSubmissionCommand(
        uuid4(),
        request.project_id,
        grant.id,
        package.id,
        preview.candidate_manifest_hash or "0" * 64,
        reviews,
    )
    return FreezeFixture(
        env, app, command, query, saved, approval, approver, ready, package_command
    )


@pytest.fixture
def b17_env(b05_env):
    return build(b05_env)


def counts(fixture):
    with fixture.engine.connect() as conn:
        return tuple(
            conn.execute(text("SELECT count(*) FROM " + table)).scalar_one()
            for table in (
                "prepared_submission_versions",
                "prepared_submission_manifest_items",
                "prepared_submission_events",
                "approval_grant_consumptions",
                "approval_grant_events",
                "author_consents",
            )
        )


def next_package(f):
    """Fresh package/consent/grant outside any timed or consuming transaction."""
    from dataclasses import replace

    grant = f.approval.get_grant(f.actor, f.command.project_id, f.command.grant_id)
    decision = f.approval.get_decision(f.actor, f.command.project_id, grant.approval_decision_id)
    previous = f.approval.get_request(f.actor, f.command.project_id, decision.approval_request_id)
    request = RequestApprovalCommand(
        uuid4(),
        f.command.project_id,
        None,
        previous.basis_decision_id,
        f.command.checked_review_ids,
        approval_purpose="PREPARE_SUBMISSION",
        manuscript_version_id=f.package_command.manuscript_version_id,
    )
    f.approval.request_approval(f.actor, request)
    with f.engine.connect() as conn:
        expiry = conn.execute(text("SELECT clock_timestamp()+interval '1 hour'")).scalar_one()
    issued = f.approval.decide_approval(
        f.approver,
        DecideApprovalCommand(
            uuid4(),
            request.project_id,
            request.id,
            "APPROVE_WITH_CONDITIONS",
            "Fresh package authorization",
            valid_until=expiry,
            requires_current_author_consent=True,
        ),
    ).grant
    assert issued is not None
    package_command = replace(f.package_command, id=uuid4())
    package = f.app.prepare_submission(f.actor, package_command)
    consent = f.app.record_author_consent(
        f.actor,
        RecordAuthorConsentCommand(
            uuid4(),
            request.project_id,
            package.id,
            "GRANTED",
            "PREPARED_PACKAGE",
            f.consent.evidence_artifact.id,
            None,
        ),
    )
    query = GetPreparedSubmissionQuery(request.project_id, package.id)
    candidate = f.app.preview_prepared_submission(f.actor, query)
    command = FreezePreparedSubmissionCommand(
        uuid4(),
        request.project_id,
        issued.id,
        package.id,
        candidate.candidate_manifest_hash,
        request.review_ids,
    )
    return replace(
        f, command=command, query=query, consent=consent, package_command=package_command
    )


def withdraw_consent(f):
    return f.app.record_author_consent(
        f.actor,
        RecordAuthorConsentCommand(
            uuid4(),
            f.command.project_id,
            f.command.result_id,
            "WITHDRAWN",
            "PREPARED_PACKAGE",
            f.consent.evidence_artifact.id,
            f.consent.id,
        ),
    )
