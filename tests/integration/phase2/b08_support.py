"""Shared B08 builders over the accepted disposable PostgreSQL fixture chain."""

from dataclasses import replace
from uuid import uuid4

from researchbase.application.decision import RecordRevisionDecisionCommand
from researchbase.application.internal_review import RecordIssueDispositionCommand
from researchbase.application.revision_action import (
    RecordConcernReReviewCommand,
    RecordRevisionActionCommand,
)
from tests.integration.phase2.test_approval import approval_env as approval_env
from tests.integration.phase2.test_revision_action import (
    conclusion_env,
    decision_env,
    phase2_database_url,
    revision_env,
)

_FIXTURES = (conclusion_env, decision_env, phase2_database_url, revision_env)


def disposition_case(revision_env, *, dismiss=False, recommendation="ACCEPT", issues=()):
    revisions, action, env, old_review, revised = revision_env
    base = env[-1]
    actor = env[2]
    decision = env[0].record_revision_decision(
        actor,
        RecordRevisionDecisionCommand(
            uuid4(),
            base[5],
            action.review_issue_id,
            "Respond?",
            "Exact issue basis",
            "ACCEPT_NO_CHANGE" if dismiss else "REQUIRE_CHANGE",
        ),
    )
    if dismiss:
        action = RecordRevisionActionCommand(
            uuid4(), base[5], "NO_CHANGE", decision_record_id=decision.id
        )
    else:
        action = replace(action, decision_record_id=decision.id)
    saved = revisions.record_revision_action(base[3], action)
    review = env[1].create(
        actor,
        base[5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        env[3].version_id if dismiss else revised.version_id,
        "SCIENTIFIC",
        recommendation,
        "Independent exact re-review",
        issues,
        uuid4(),
    )
    revisions.record_concern_re_review(
        actor, RecordConcernReReviewCommand(base[5], saved.id, review.id)
    )
    command = RecordIssueDispositionCommand(
        uuid4(),
        base[5],
        old_review.issues[0].id,
        "DISMISSED" if dismiss else "ADDRESSED",
        saved.id,
        review.id,
        "I attest this exact response resolves this concern",
        decision.id,
    )
    return env[1], actor, command, base, action


def changed_case(revision_env, kind):
    """All five exact result shapes share this preparation, with independent review."""
    from uuid import UUID

    from sqlalchemy import text

    from researchbase.application.commands import RecordMeasurementCommand
    from tests.integration.phase2.revision_support import _claim_with_result
    from tests.integration.phase2.test_b06_revision_action import (
        _analysis,
        _app,
        _claim_successor,
        _context,
        _measurement,
        _review_issue,
        _run,
        _source_response,
    )

    revisions, original, env, _, revised = revision_env
    base = env[-1]
    if kind == "CONCLUSION_CHANGE":
        return disposition_case(revision_env)
    issue = _review_issue(env, "claim")
    if kind == "CLAIM_CHANGE":
        target = _claim_successor(base)
        action = RecordRevisionActionCommand(
            uuid4(), base[5], kind, issue, result_claim_version_id=target
        )
    elif kind == "NEW_EXPERIMENT":
        spec, run = _run(base)
        with base[8].connect() as conn:
            metric = conn.execute(
                text("SELECT metric_definition_version_id FROM measurements WHERE id=:id"),
                {"id": _measurement(base)},
            ).scalar_one()
        measurement = (
            _app(base)
            .record_measurement(
                RecordMeasurementCommand(run, metric, 0.8, None, None, None, _context(base))
            )
            .id
        )
        target = _claim_with_result(base, measurement=measurement)
        action = RecordRevisionActionCommand(
            uuid4(), base[5], kind, issue, result_experiment_spec_version_id=spec, result_run_id=run
        )
    elif kind == "ANALYSIS_CHANGE":
        statistic = _analysis(base)
        target = _claim_with_result(base, statistic=statistic)
        action = RecordRevisionActionCommand(
            uuid4(), base[5], kind, issue, result_statistical_result_id=statistic
        )
    else:
        action = _source_response(env, "claim", "CORRECTED")
        issue = action.review_issue_id
        from researchbase.application.source_version import (
            CreateSourceVersion,
            SourceVersionService,
            TransitionSourceVersion,
            _material_from_row,
        )
        from researchbase.domain.source_version import FrozenSourceReference

        with base[1]() as uow:
            previous = uow.source_version.version(action.result_source_version_id)
            source = _material_from_row(uow.source_version, uow.source_version.version(base[7]))
            material = replace(
                _material_from_row(uow.source_version, previous),
                predecessor_source_version=FrozenSourceReference(
                    previous["id"], previous["content_hash"]
                ),
                fulltext_artifact=source.fulltext_artifact,
            )
        sources = SourceVersionService(base[1], base[-1])
        created = sources.create(CreateSourceVersion(base[3], base[5], material, uuid4()))
        exact = UUID(str(created["source_version_id"]))
        sources.freeze(TransitionSourceVersion(base[3], base[5], exact, uuid4()))
        action = replace(action, result_source_version_id=exact)
        target = _claim_successor(base)
        evidence = base[2].create(base[3], base[5], exact, "improved recall", uuid4())
        base[2].review(base[4], base[5], UUID(evidence["id"]), "VERIFIED", "Independent", uuid4())
        base[2].snapshot(
            base[3],
            base[5],
            "ClaimVersion",
            target,
            [
                {
                    "evidence_id": evidence["id"],
                    "relation_type": "SUPPORTS",
                    "qualification": "Exact response",
                }
            ],
            uuid4(),
        )
    saved = revisions.record_revision_action(base[3], action)
    review = env[1].create(
        env[2],
        base[5],
        "CLAIM_VERSION",
        target,
        "SCIENTIFIC",
        "MINOR_REVISION",
        "Exact response",
        (),
        uuid4(),
    )
    revisions.record_concern_re_review(
        env[2], RecordConcernReReviewCommand(base[5], saved.id, review.id)
    )
    assert issue is not None
    cmd = RecordIssueDispositionCommand(
        uuid4(),
        base[5],
        issue,
        "ADDRESSED",
        saved.id,
        review.id,
        "I attest exact completed response",
    )
    return env[1], env[2], cmd, base, action


def current_disposition_case(revision_env, **options):
    """Use the current frozen result as the concern target, for release gates."""
    from researchbase.application.internal_review import ReviewIssueRequest

    revisions, action, env, _, revised = revision_env
    base = env[-1]
    old = env[1].create(
        env[2],
        base[5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        revised.version_id,
        "SCIENTIFIC",
        "REJECT",
        "Exact current concern",
        (ReviewIssueRequest("BLOCKING", "OTHER", "Current blocker"),),
        uuid4(),
    )
    current_env = (*env[:3], revised, base)
    prepared = (
        revisions,
        replace(action, review_issue_id=old.issues[0].id),
        current_env,
        old,
        revised,
    )
    return disposition_case(prepared, **options)
