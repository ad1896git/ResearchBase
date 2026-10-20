"""Attributable exact re-review, replay and historical carry-forward."""

from dataclasses import replace
from uuid import uuid4

import pytest

from researchbase.application.revision_action import (
    RecordConcernReReviewCommand,
    RecordRevisionActionCommand,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.revision_support import _claim_with_result
from tests.integration.phase2.test_b07_revision_decisions import decision_command
from tests.integration.phase2.test_revision_action import (
    conclusion_env,
    decision_env,
    phase2_database_url,
    revision_env,
)

pytestmark = pytest.mark.integration
_FIXTURES = (conclusion_env, decision_env, phase2_database_url, revision_env)


@pytest.mark.parametrize("no_change", [False, True])
@pytest.mark.parametrize("recommendation", ["ACCEPT", "REJECT", "UNCERTAIN"])
def test_explicit_attestation_never_inherits_other_action_links(
    revision_env, no_change, recommendation
):
    service, action, env, old_review, revised = revision_env
    base = env[-1]
    if no_change:
        d = env[0].record_revision_decision(
            env[2], decision_command(env, action.review_issue_id, "ACCEPT_NO_CHANGE")
        )
        action = RecordRevisionActionCommand(uuid4(), base[5], "NO_CHANGE", decision_record_id=d.id)
    first = service.record_revision_action(base[3], action)
    second = service.record_revision_action(base[3], replace(action, id=uuid4()))
    target = env[3].version_id if no_change else revised.version_id
    review = env[1].create(
        env[2],
        base[5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        target,
        "SCIENTIFIC",
        recommendation,
        "Independent re-review",
        (),
        uuid4(),
    )
    concern = service.get_concern_carry_forward(env[2], base[5], old_review.issues[0].id)
    assert all(x.mapping_state == "PENDING_RE_REVIEW" for x in concern.actions)
    cmd = RecordConcernReReviewCommand(base[5], first.id, review.id)
    link = service.record_concern_re_review(env[2], cmd)
    assert link.internal_review_record_id == review.id
    assert service.record_concern_re_review(env[2], cmd) == link
    concern = service.get_concern_carry_forward(env[2], base[5], old_review.issues[0].id)
    assert [x.mapping_state for x in concern.actions] == ["RE_REVIEW_LINKED", "PENDING_RE_REVIEW"]
    assert concern.actions[1].action.id == second.id
    correction = service.record_revision_action(
        base[3], replace(action, id=uuid4(), supersedes_revision_action_id=first.id)
    )
    assert correction.supersedes_revision_action_id == first.id
    historical = service.record_concern_re_review(env[2], cmd)
    assert historical.has_superseding_action
    with pytest.raises(ResearchBaseError) as caught:
        service.record_concern_re_review(env[2], replace(cmd, revision_action_id=correction.id))
    assert (
        caught.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    )  # re-review predates correction


def test_wrong_target_and_wrong_writer_deny_without_partial_link(revision_env):
    service, action, env, _, _ = revision_env
    base = env[-1]
    result = service.record_revision_action(base[3], action)
    review = env[1].create(
        env[2],
        base[5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        env[3].version_id,
        "SCIENTIFIC",
        "REJECT",
        "Old target is not the result",
        (),
        uuid4(),
    )
    cmd = RecordConcernReReviewCommand(base[5], result.id, review.id)
    with pytest.raises(ResearchBaseError) as caught:
        service.record_concern_re_review(base[3], cmd)
    assert caught.value.code == ErrorCode.FORBIDDEN
    with pytest.raises(ResearchBaseError) as caught:
        service.record_concern_re_review(env[2], cmd)
    assert caught.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    concern = service.get_concern_carry_forward(env[2], base[5], action.review_issue_id)
    assert concern.actions[0].re_reviews == ()


@pytest.mark.parametrize(
    "kind,state",
    [
        ("CLAIM_CHANGE", "valid"),
        ("NEW_EXPERIMENT", "valid"),
        ("ANALYSIS_CHANGE", "valid"),
        ("SOURCE_CHANGE", "valid"),
        ("SOURCE_CHANGE", "retracted"),
        ("SOURCE_CHANGE", "disputed"),
        ("SOURCE_CHANGE", "author"),
        ("SOURCE_CHANGE", "later_valid"),
    ],
)
def test_each_changed_result_has_exact_independent_scientific_re_review(revision_env, kind, state):
    from uuid import UUID

    from sqlalchemy import text

    from researchbase.application.commands import RecordMeasurementCommand
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

    service, original, env, _, _ = revision_env
    base = env[-1]
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
        from researchbase.application.source_version import (
            CreateSourceVersion,
            SourceVersionService,
            TransitionSourceVersion,
            _material_from_row,
        )
        from researchbase.domain.source_version import FrozenSourceReference

        with base[1]() as uow:
            previous = uow.source_version.version(action.result_source_version_id)
            original_source = _material_from_row(
                uow.source_version, uow.source_version.version(base[7])
            )
            material = replace(
                _material_from_row(uow.source_version, previous),
                predecessor_source_version=FrozenSourceReference(
                    previous["id"], previous["content_hash"]
                ),
                fulltext_artifact=original_source.fulltext_artifact,
            )
        sources = SourceVersionService(base[1], base[-1])
        created = sources.create(
            CreateSourceVersion(
                env[2] if state == "author" else base[3], base[5], material, uuid4()
            )
        )
        exact = UUID(str(created["source_version_id"]))
        sources.freeze(
            TransitionSourceVersion(
                env[2] if state == "author" else base[3], base[5], exact, uuid4()
            )
        )
        action = replace(action, result_source_version_id=exact)
        target = _claim_successor(base)
        evidence = base[2].create(
            base[3], base[5], action.result_source_version_id, "improved recall", uuid4()
        )
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
                    "qualification": "Exact source correction relevance",
                }
            ],
            uuid4(),
        )
    result = service.record_revision_action(base[3], action)
    review = env[1].create(
        env[2],
        base[5],
        "CLAIM_VERSION",
        target,
        "SCIENTIFIC",
        "UNCERTAIN",
        "Exact witness",
        (),
        uuid4(),
    )
    if state == "retracted":
        from researchbase.domain.source_version import SourceVersionKind

        retraction = replace(
            material,
            version_kind=SourceVersionKind.RETRACTED,
            predecessor_source_version=FrozenSourceReference(exact, "0" * 64),
        )
        with base[1]() as uow:
            exact_row = uow.source_version.version(exact)
        retraction = replace(
            retraction,
            predecessor_source_version=FrozenSourceReference(exact, exact_row["content_hash"]),
        )
        created = sources.create(CreateSourceVersion(base[3], base[5], retraction, uuid4()))
        sources.freeze(
            TransitionSourceVersion(
                base[3], base[5], UUID(str(created["source_version_id"])), uuid4()
            )
        )
    elif state == "disputed":
        base[2].review(base[4], base[5], UUID(evidence["id"]), "DISPUTED", "New concern", uuid4())
    if state == "later_valid":
        base[2].review(
            base[4], base[5], UUID(evidence["id"]), "DISPUTED", "Earlier witness disputed", uuid4()
        )
        later = base[2].create(
            base[3], base[5], action.result_source_version_id, "improved recall", uuid4()
        )
        base[2].review(base[4], base[5], UUID(later["id"]), "VERIFIED", "Independent", uuid4())
        base[2].snapshot(
            base[3],
            base[5],
            "ClaimVersion",
            target,
            [
                {
                    "evidence_id": later["id"],
                    "relation_type": "SUPPORTS",
                    "qualification": "Exact correction",
                }
            ],
            uuid4(),
        )
    if state not in {"valid", "later_valid"}:
        from sqlalchemy.exc import DBAPIError

        with pytest.raises(ResearchBaseError) as caught:
            service.record_concern_re_review(
                env[2], RecordConcernReReviewCommand(base[5], result.id, review.id)
            )
        assert caught.value.code == (
            ErrorCode.CONFLICT_OF_INTEREST
            if state == "author"
            else ErrorCode.PROVENANCE_CLOSURE_VIOLATION
        )
        with pytest.raises(DBAPIError) as caught_sql, base[8].begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO revision_action_re_reviews "
                    "VALUES (:action,:review,:actor,clock_timestamp())"
                ),
                {"action": result.id, "review": review.id, "actor": env[2].actor_id},
            )
        assert getattr(caught_sql.value.orig, "sqlstate", None) == "P17F2"
        return
    link = service.record_concern_re_review(
        env[2], RecordConcernReReviewCommand(base[5], result.id, review.id)
    )
    assert link.claim_version_id == target and link.target_validity == "VALID"
    carry = service.get_concern_carry_forward(env[2], base[5], result.effective_review_issue_id)
    assert carry.actions[0].mapping_state == "RE_REVIEW_LINKED"

    if kind == "SOURCE_CHANGE" and state == "valid":
        base[2].review(base[4], base[5], UUID(evidence["id"]), "DISPUTED", "Later concern", uuid4())
        historical = service.record_concern_re_review(
            env[2], RecordConcernReReviewCommand(base[5], result.id, review.id)
        )
        assert historical.internal_review_record_id == link.internal_review_record_id
        assert historical.action_content_hash == link.action_content_hash
        assert historical.target_validity == "STALE"
        assert service.get_concern_carry_forward(
            env[2], base[5], result.effective_review_issue_id
        ).actions[0].re_reviews == (historical,)


@pytest.mark.parametrize("invalid_target", ["claim_version", "metric_definition_version"])
def test_stale_re_review_target_denies_application_and_direct_sql(revision_env, invalid_target):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    from tests.integration.phase2.test_pr2_15_decision import _stale

    service, action, env, _, revised = revision_env
    base = env[-1]
    result = service.record_revision_action(base[3], action)
    review = env[1].create(
        env[2],
        base[5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        revised.version_id,
        "SCIENTIFIC",
        "REJECT",
        "Independent",
        (),
        uuid4(),
    )
    if invalid_target == "claim_version":
        _stale(env)
    else:
        from researchbase.application.governance import (
            CreateAuditFindingCommand,
            CreateImpactAssessmentCommand,
            GovernanceService,
            ProposedImpactTarget,
        )
        from researchbase.foundation.time import SystemClock
        from tests.integration.phase2.test_b06_revision_action import _context, _measurement

        with base[8].connect() as conn:
            metric = conn.execute(
                text("SELECT metric_definition_version_id FROM measurements WHERE id=:id"),
                {"id": _measurement(base)},
            ).scalar_one()
        governance = GovernanceService(base[1], SystemClock())
        finding = governance.create_audit_finding(
            CreateAuditFindingCommand(
                base[5],
                "code_bug",
                "major",
                "Invalid exact metric",
                "Recheck",
                invalid_target,
                metric,
                _context(base),
            )
        )
        governance.create_impact_assessment(
            CreateImpactAssessmentCommand(
                base[5],
                finding.id,
                {"basis": "Exact metric"},
                "invalid",
                (ProposedImpactTarget(invalid_target, metric, "invalid"),),
                _context(base),
            )
        )
    with pytest.raises(ResearchBaseError) as caught:
        service.record_concern_re_review(
            env[2], RecordConcernReReviewCommand(base[5], result.id, review.id)
        )
    assert caught.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    with pytest.raises(DBAPIError) as database_error, base[8].begin() as conn:
        conn.execute(
            text(
                "INSERT INTO revision_action_re_reviews "
                "VALUES (:action,:review,:actor,clock_timestamp())"
            ),
            {"action": result.id, "review": review.id, "actor": env[2].actor_id},
        )
    assert getattr(database_error.value.orig, "sqlstate", None) == "P17F2"


def test_composite_replay_survives_write_role_loss_but_not_read_loss(revision_env):
    from sqlalchemy import text

    from researchbase.application.phase2_identity import AssignProjectRole, CloseProjectRole
    from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service

    service, action, env, _, revised = revision_env
    base = env[-1]
    actor = env[2]
    saved = service.record_revision_action(base[3], action)
    review = env[1].create(
        actor,
        base[5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        revised.version_id,
        "SCIENTIFIC",
        "REJECT",
        "Independent",
        (),
        uuid4(),
    )
    cmd = RecordConcernReReviewCommand(base[5], saved.id, review.id)
    link = service.record_concern_re_review(actor, cmd)
    identity, _, _ = identity_service(str(base[8].url))
    identity.assign_project_role(
        AssignProjectRole(actor, base[5], actor.actor_id, "VIEWER", "Read history", uuid4())
    )
    with base[8].connect() as conn:
        role = conn.execute(
            text(
                "SELECT id FROM project_role_assignments WHERE actor_id=:actor AND "
                "project_id=:project AND role='OWNER' AND effective_until IS NULL"
            ),
            {"actor": actor.actor_id, "project": base[5]},
        ).scalar_one()
    identity.close_project_role(CloseProjectRole(base[3], base[5], role, "Write loss", uuid4()))
    assert service.record_concern_re_review(actor, cmd) == link
    assert service.get_concern_carry_forward(actor, base[5], action.review_issue_id).actions[
        0
    ].re_reviews == (link,)
    with base[8].connect() as conn:
        role = conn.execute(
            text(
                "SELECT id FROM project_role_assignments WHERE actor_id=:actor AND "
                "project_id=:project AND role='VIEWER' AND effective_until IS NULL"
            ),
            {"actor": actor.actor_id, "project": base[5]},
        ).scalar_one()
    identity.close_project_role(CloseProjectRole(base[3], base[5], role, "Read loss", uuid4()))
    with pytest.raises(ResearchBaseError) as caught:
        service.record_concern_re_review(actor, cmd)
    assert caught.value.code == ErrorCode.FORBIDDEN
