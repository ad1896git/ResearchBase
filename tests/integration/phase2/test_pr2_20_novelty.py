"""Bounded correctness/parity; observed phantom regressions remain authoritative."""

from dataclasses import replace

import pytest

from tests.integration.phase2 import b18_novelty_support as b
from tests.integration.phase2 import pr2_20_support as s
from tests.integration.phase2.b17_fixtures import (
    b04_env,
    b05_env,
    conclusion_env,
    decision_env,
    phase2_database_url,
    revision_env,
)

pytest_plugins = (
    "tests.integration.phase2.pr2_18_fixtures",
    "tests.integration.phase2.test_m3_evidence",
)
b18_env = b.b18_env


@pytest.mark.parametrize("kind", b.KINDS)
def test_bounded_first_write_replay_read_and_later_resolution(b18_env, kind):
    e = b18_env
    protected = b.protected_manifest(e)
    command = b.fresh_command(e, kind)
    first = b.invoke(e, kind, "first", command=command)
    after_first = s.manifest(e["engine"], b.NOVELTY_TABLES)
    for operation in ("replay", "read"):
        assert b.stable(b.invoke(e, kind, operation, command=command)) == b.stable(first)
    assert s.manifest(e["engine"], b.NOVELTY_TABLES) == after_first
    b.resolve_remaining(e)
    later = b.invoke(e, kind, "read", command=command)
    assert later.content_hash == first.content_hash
    if kind == "coverage":
        assert later.material_version == 2
        assert later.quality.captured_unresolved_result_count == 1
        assert later.quality.current_unresolved_result_count == 0
        assert b.stable(replace(later, quality=first.quality)) == b.stable(first)
    elif kind == "novelty":
        coverage = later.search_coverage
        assert coverage.material_version == 2
        assert coverage.quality.captured_unresolved_result_count == 1
        assert coverage.quality.current_unresolved_result_count == 0
        assert b.stable(replace(later, search_coverage=first.search_coverage)) == b.stable(first)
        assert coverage.content_hash == first.search_coverage.content_hash
        assert coverage.resolved_source_count == 1
    else:
        assert b.stable(later) == b.stable(first)
    assert s.manifest(e["engine"], b.NOVELTY_TABLES) == after_first
    assert b.protected_manifest(e) == protected
    assert len(b.PHANTOM_REFERENCES) == 2
    print("B18_PHANTOM_REFERENCES", b.PHANTOM_REFERENCES)


_H2_FIXTURES = (b04_env, b05_env, conclusion_env, decision_env, phase2_database_url, revision_env)


def _h2_novelty(env):
    from uuid import UUID, uuid4

    from researchbase.application.literature_evidence import LiteratureEvidenceService
    from researchbase.application.novelty import NoveltyService
    from researchbase.domain.organization import ProjectId
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock
    from tests.application_compat import LegacyApplicationService

    factory, credentials, store = env[4], env[9], env[7]
    author, project, version_id = env[2], env[1].project_id, env[10][7]
    service = LiteratureEvidenceService(factory, credentials, store)
    evidence = service.create(author, project, version_id, "improved recall", uuid4())
    evidence_id = UUID(evidence["id"])
    service.review(
        env[3], project, evidence_id, "VERIFIED", "Independent exact inspection", uuid4()
    )
    app = LegacyApplicationService(factory, SystemClock(), store)
    context = ExecutionContext(actor_id=author.actor_id, request_id=uuid4(), client_type="test")
    # A plan with no invoked query is a truthful selected zero-invocation scope.
    from researchbase.application.commands import (
        CreateResearchQuestionCommand,
        FreezeResearchQuestionCommand,
    )
    from researchbase.application.literature_search_plan import (
        CreateLiteratureSearchPlan,
        LiteratureSearchPlanService,
        TransitionLiteratureSearchPlanVersion,
    )
    from researchbase.domain.literature_search_plan import (
        FrozenResearchQuestionReference,
        LiteratureSearchPlanMaterial,
        LiteratureSearchStrategy,
        LiteratureSourceScope,
    )
    from researchbase.domain.research import ResearchQuestionId, ResearchQuestionVersionId

    question = app.create_research_question(
        CreateResearchQuestionCommand(
            ProjectId(project), "Bounded search question", None, None, context
        )
    )
    qv = app.freeze_research_question(
        FreezeResearchQuestionCommand(
            ResearchQuestionId(question.id),
            ResearchQuestionVersionId(question.current_version_id),
            context,
        )
    )
    plans = LiteratureSearchPlanService(factory, credentials)
    plan = plans.create(
        CreateLiteratureSearchPlan(
            author,
            project,
            LiteratureSearchPlanMaterial(
                uuid4(),
                (
                    FrozenResearchQuestionReference(
                        UUID(str(question.id)), UUID(str(qv.id)), str(qv.content_hash)
                    ),
                ),
                "Search prior work",
                LiteratureSourceScope.BIBLIOGRAPHIC,
                None,
                None,
                None,
                (),
                LiteratureSearchStrategy.KEYWORD,
                ("test",),
                None,
            ),
            uuid4(),
        )
    )
    plan_id = UUID(str(plan["plan_id"]))
    plan_version = UUID(str(plan["version_id"]))
    plans.freeze(
        TransitionLiteratureSearchPlanVersion(author, project, plan_id, plan_version, uuid4())
    )
    return b.build(
        dict(
            engine=env[5],
            factory=factory,
            credentials=credentials,
            author=author,
            reviewer=env[3],
            project=project,
            claim=env[8],
            source=version_id,
            store=store,
            literature=service,
            service=NoveltyService(factory, credentials, service),
            evidence=evidence_id,
            plan=plan_version,
        ),
        assessment=False,
    )


@pytest.mark.parametrize(
    "outcome", [None, "INCONCLUSIVE", "CLOSE_PRIOR_ART_FOUND", "NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE"]
)
@pytest.mark.parametrize(
    "control", [None, "ready_issue", "ready_invalid", "package_issue", "package_invalid", "consent"]
)
def test_novelty_outcomes_never_gate_approval_ready_or_package_freeze(b05_env, outcome, control):
    """H2 fallback: negative outcome remains rejected, never fabricated as history."""
    from uuid import uuid4

    from sqlalchemy import text

    from researchbase.application.internal_review import ReviewIssueRequest
    from researchbase.domain.novelty import (
        ClosenessCriteria,
        NoveltyOutcome,
        PriorArtBasisInput,
        PriorArtKind,
    )
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from tests.integration.phase2 import b17_fixtures
    from tests.integration.phase2.test_b05_manuscript_review import create
    from tests.integration.phase2.test_b11_readiness_decision import place_claim
    from tests.integration.phase2.test_b14_publication_ready import issued

    env = b05_env
    place_claim(env)
    e = _h2_novelty(env)
    if outcome is not None:
        command = e["commands"]["novelty"]
        if outcome == "CLOSE_PRIOR_ART_FOUND":
            relation = e["service"].record_prior_art_relation(
                e["author"],
                replace(e["commands"]["prior_art"], id=uuid4(), relation=PriorArtKind.IDENTICAL),
            )
            command = replace(
                command,
                id=uuid4(),
                assessment=NoveltyOutcome(outcome),
                prior_art_basis=(PriorArtBasisInput(relation.id, e["resolution"]["command"].id),),
                scope_statement="Inspected selected executions",
                closeness_criteria=ClosenessCriteria(("Same method", "Same result")),
            )
        else:
            command = replace(command, id=uuid4(), assessment=NoveltyOutcome(outcome))
        if outcome == "NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE":
            before = s.manifest(e["engine"], b.NOVELTY_TABLES)
            with pytest.raises(ResearchBaseError) as denied:
                e["service"].record_novelty_assessment(e["author"], command)
            assert denied.value.code == ErrorCode.INVALID_STATE_TRANSITION
            assert s.manifest(e["engine"], b.NOVELTY_TABLES) == before
        else:
            saved = e["service"].record_novelty_assessment(e["author"], command)
            assert saved.assessment == NoveltyOutcome(outcome)
    novelty = s.manifest(e["engine"], b.NOVELTY_TABLES)
    science = s.manifest(e["engine"], ("claim_versions", "evidence_relations", "source_versions"))

    def invalidate():
        from researchbase.application.governance import (
            CreateImpactAssessmentCommand,
            GovernanceService,
            ProposedImpactTarget,
        )
        from researchbase.foundation.execution_context import ExecutionContext
        from researchbase.foundation.time import SystemClock

        with s.read_snapshot(env[5]) as conn:
            document = conn.execute(
                text("SELECT document_artifact_version_id FROM manuscript_versions WHERE id=:id"),
                {"id": env[1].manuscript_version_id},
            ).scalar_one()
        GovernanceService(env[4], SystemClock()).create_impact_assessment(
            CreateImpactAssessmentCommand(
                env[1].project_id,
                None,
                {"test": "independent invalid fact"},
                "invalid",
                (ProposedImpactTarget("artifact_version", document, "invalid"),),
                ExecutionContext(actor_id=env[2].actor_id, request_id=uuid4(), client_type="test"),
            )
        )

    def issue():
        create(
            env,
            issues=(
                ReviewIssueRequest("BLOCKING", "NOVELTY", "Independent recorded review concern"),
            ),
        )

    if control in {"ready_issue", "ready_invalid"}:
        publication, ready, approval, _ = issued(env)
        grant = approval.get_grant(env[2], ready.project_id, ready.grant_id)
        decision = approval.get_decision(env[2], ready.project_id, grant.approval_decision_id)
        request = approval.get_request(env[2], ready.project_id, decision.approval_request_id)
        issue() if control == "ready_issue" else invalidate()
        before = s.manifest(
            env[5],
            (
                "publications",
                "approval_grants",
                "approval_grant_consumptions",
                "publication_lifecycle_events",
            ),
        )
        with pytest.raises(ResearchBaseError) as denied:
            publication.transition_publication_ready(env[2], ready)
        assert denied.value.code in {
            ErrorCode.APPROVAL_GATE_FAILED,
            ErrorCode.APPROVAL_TARGET_STALE,
        }
        assert s.manifest(env[5], tuple(before)) == before
        assert approval.get_grant(env[2], ready.project_id, ready.grant_id).status == "ACTIVE"
        from researchbase.application.approval import RequestApprovalCommand

        before_permission = s.manifest(
            env[5],
            (
                "approval_requests",
                "approval_request_events",
                "approval_grants",
                "approval_grant_consumptions",
            ),
        )
        with pytest.raises(ResearchBaseError) as denied:
            approval.request_approval(
                env[2],
                RequestApprovalCommand(
                    uuid4(),
                    request.project_id,
                    None,
                    request.basis_decision_id,
                    tuple(ref.id for ref in request.reviews),
                    approval_purpose="READY_FOR_SUBMISSION",
                    manuscript_version_id=request.manuscript_version_id,
                ),
            )
        assert denied.value.code in {
            ErrorCode.APPROVAL_GATE_FAILED,
            ErrorCode.APPROVAL_TARGET_STALE,
            ErrorCode.DECISION_BASIS_INVALID,
        }
        assert s.manifest(env[5], tuple(before_permission)) == before_permission

    else:
        f = b17_fixtures.build(env, consent=control != "consent")
        if control == "package_issue":
            issue()
        if control == "package_invalid":
            invalidate()
        before = b17_fixtures.counts(f)
        if control:
            with pytest.raises(ResearchBaseError) as denied:
                f.app.freeze_prepared_submission(f.actor, f.command)
            assert denied.value.code in {
                ErrorCode.APPROVAL_GATE_FAILED,
                ErrorCode.APPROVAL_TARGET_STALE,
            }
            assert b17_fixtures.counts(f) == before
            assert f.app.get_prepared_submission(f.actor, f.query).status == "PREPARED"
            assert (
                f.approval.get_grant(f.actor, f.command.project_id, f.command.grant_id).status
                == "ACTIVE"
            )
        else:
            receipt = f.app.freeze_prepared_submission(f.actor, f.command)
            package = f.app.get_prepared_submission(f.actor, f.query)
            assert (package.status, package.current_validity, package.row_version) == (
                "FROZEN",
                "VALID",
                2,
            )
            assert package.package_manifest_hash == f.command.expected_package_manifest_hash
            assert receipt.grant_id == f.command.grant_id
            assert not any("novelty" in item.category.lower() for item in package.items)
            with s.read_snapshot(env[5]) as conn:
                assert (
                    conn.execute(
                        text("SELECT count(*) FROM approval_grant_consumptions")
                    ).scalar_one()
                    == 2
                )
                assert (
                    conn.execute(
                        text("SELECT count(*) FROM review_issues WHERE severity='BLOCKING'")
                    ).scalar_one()
                    == 0
                )
    with s.read_snapshot(env[5]) as conn:
        novelty_ids = tuple(
            str(x) for x in conn.execute(text("SELECT id FROM novelty_assessments")).scalars()
        )
        for table in (
            "approval_requests",
            "approval_decisions",
            "approval_grants",
            "approval_grant_consumptions",
        ):
            rows = conn.execute(text(f"SELECT row_to_json(t)::text FROM {table} t")).scalars().all()
            assert all(
                "novelty" not in row.lower()
                and not any(identity in row for identity in novelty_ids)
                for row in rows
            )
        if control is None:
            normalized = (
                tuple(
                    conn.execute(
                        text("SELECT decision FROM approval_decisions ORDER BY decision")
                    ).scalars()
                ),
                tuple(conn.execute(text("SELECT lifecycle_status FROM publications")).scalars()),
                tuple(
                    conn.execute(
                        text("SELECT command FROM approval_grant_consumptions ORDER BY command")
                    ).scalars()
                ),
            )
            assert normalized == (
                ("APPROVE", "APPROVE_WITH_CONDITIONS"),
                ("READY",),
                ("FREEZE_PREPARED_SUBMISSION", "TRANSITION_PUBLICATION_READY"),
            )
    assert s.manifest(e["engine"], b.NOVELTY_TABLES) == novelty
    assert s.manifest(e["engine"], tuple(science)) == science


# Owning post-wait authority denial (pg_locks witness, FORBIDDEN, zero inserted rows):
# tests/integration/phase2/test_pr2_18_concurrency.py::test_expiry_across_required_database_wait[credential-request-coverage]  # noqa: E501
# tests/integration/phase2/test_pr2_18_concurrency.py::test_expiry_across_required_database_wait[role-foreign_key-prior_art]  # noqa: E501
# tests/integration/phase2/test_b19_close_prior_art_concurrency.py::test_post_claim_wait_credential_expiry  # noqa: E501
# These cover the shared B18/B19/B21/B22 novelty write authorization protocol.
@pytest.mark.parametrize("first", [False, True])
@pytest.mark.parametrize("scenario", ["capture", "positive-basis"])
def test_s3_novelty_both_commit_orders(request, monkeypatch, first, scenario):
    from tests.integration.phase2 import (
        test_b19_close_prior_art_concurrency as b19,
    )
    from tests.integration.phase2 import (
        test_b21_capture_concurrency as b21,
    )

    if scenario == "capture":
        b21.test_resolution_membership_both_lock_orders(
            request.getfixturevalue("b18_env"), monkeypatch, first
        )
    else:
        b19.test_b22_b19_both_claim_lock_orders(
            request.getfixturevalue("novelty_env"), monkeypatch, first
        )


def test_s3_prior_art_selection_empty_unique_ambiguous(novelty_env):
    from tests.integration.phase2.test_b22_prior_art_selection import (
        test_empty_unique_ambiguous_agreeing_roots,
    )

    test_empty_unique_ambiguous_agreeing_roots(novelty_env)


@pytest.mark.parametrize("stage", ["insert_child", "force_constraints"])
def test_s3_prior_art_correction_atomic_rollback(novelty_env, monkeypatch, stage):
    from tests.integration.phase2.test_b22_prior_art_correction import test_atomic_failure

    before = b.protected_manifest(novelty_env)
    test_atomic_failure(novelty_env, monkeypatch, stage)
    assert b.protected_manifest(novelty_env) == before


@pytest.mark.parametrize("workers", [1, 4])
def test_s3_prior_art_correction_workers_observed_wait_and_saved_history(novelty_env, workers):
    from uuid import uuid4

    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from tests.integration.phase2.test_b22_prior_art_correction import read, record, request
    from tests.integration.phase2.test_b22_prior_art_selection import select
    from tests.integration.phase2.test_pr2_20_governance_races import _s3_contend

    e = novelty_env
    root = record(e, request(e))
    commands = [request(e, supersedes_prior_art_relation_id=root.id) for _ in range(workers)]

    def invoke(command):
        try:
            return record(e, command)
        except ResearchBaseError as exc:
            return exc.code

    before = s.manifest(e["engine"], ("claim_versions", "source_versions"))
    saved, results = _s3_contend(
        e["engine"],
        lambda: invoke(commands[0]),
        [lambda command=command: invoke(command) for command in commands[1:]],
        "INSERT INTO prior_art_relations",
    )
    assert not isinstance(saved, ErrorCode)
    assert results == [ErrorCode.INVALID_STATE_TRANSITION] * (workers - 1)
    assert select(e).selected_prior_art_relation_id == saved.id
    assert read(e, root.id).content_hash == root.content_hash
    assert read(e, root.id).superseded_by_prior_art_relation_id == saved.id
    assert record(e, commands[0]).content_hash == saved.content_hash
    with pytest.raises(ResearchBaseError) as denied:
        record(e, replace(commands[0], id=uuid4()))
    assert denied.value.code == ErrorCode.INVALID_STATE_TRANSITION
    assert s.manifest(e["engine"], tuple(before)) == before


@pytest.mark.parametrize("workers", [1, 4])
@pytest.mark.parametrize("outcome", ["INCONCLUSIVE", "CLOSE_PRIOR_ART_FOUND"])
def test_s3_novelty_non_gating_workers(b05_env, workers, outcome):
    from concurrent.futures import ThreadPoolExecutor
    from uuid import uuid4

    from researchbase.domain.novelty import (
        ClosenessCriteria,
        NoveltyOutcome,
        PriorArtBasisInput,
        PriorArtKind,
    )
    from tests.integration.phase2.b17_fixtures import build
    from tests.integration.phase2.b30_observations import assert_snapshot_read, sql_protocol
    from tests.integration.phase2.test_b11_readiness_decision import place_claim

    place_claim(b05_env)
    e = _h2_novelty(b05_env)
    command = replace(e["commands"]["novelty"], id=uuid4())
    if outcome == "CLOSE_PRIOR_ART_FOUND":
        relation = e["service"].record_prior_art_relation(
            e["author"],
            replace(e["commands"]["prior_art"], id=uuid4(), relation=PriorArtKind.IDENTICAL),
        )
        command = replace(
            command,
            assessment=NoveltyOutcome(outcome),
            prior_art_basis=(PriorArtBasisInput(relation.id, e["resolution"]["command"].id),),
            scope_statement="Inspected selected executions",
            closeness_criteria=ClosenessCriteria(("Same method", "Same result")),
        )
    e["service"].record_novelty_assessment(e["author"], command)
    tables = (*b.NOVELTY_TABLES, "novelty_assessment_prior_art_inputs")
    before = s.manifest(e["engine"], tables)
    # Includes both READY and PREPARE_SUBMISSION approvals and READY consumption.
    f = build(b05_env)
    saved = f.app.freeze_prepared_submission(f.actor, f.command)
    effects = s.manifest(f.engine, ("approval_grant_consumptions", "prepared_submission_events"))
    with sql_protocol(f.engine) as observed, ThreadPoolExecutor(max_workers=workers) as pool:
        replay = list(
            pool.map(lambda _: f.app.freeze_prepared_submission(f.actor, f.command), range(workers))
        )
    assert_snapshot_read(observed, snapshots=workers)
    assert replay == [saved] * workers
    assert s.manifest(e["engine"], tables) == before
    assert s.manifest(f.engine, tuple(effects)) == effects
    assert effects["approval_grant_consumptions"]["count"] == 2
