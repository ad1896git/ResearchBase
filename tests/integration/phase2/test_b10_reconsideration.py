"""B10 real committed evidence and immutable successor acceptance."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.decision import RecordRejectionReconsiderationCommand
from researchbase.application.phase2_identity import AssignProjectRole
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2 import test_approval as fixtures
from tests.integration.phase2.test_approval import _actor, _decide
from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service

approval_env = fixtures.approval_env
conclusion_env = fixtures.conclusion_env
decision_env = fixtures.decision_env
phase2_database_url = fixtures.phase2_database_url
pytestmark = pytest.mark.integration


def approver_actor(env):
    actor = _actor(env)
    base = env[-1]
    identity, _, _ = identity_service(str(base[8].url))
    identity.assign_project_role(
        AssignProjectRole(env[2], base[5], actor.actor_id, "APPROVER", "TEST ONLY B10", uuid4())
    )
    return actor


@pytest.fixture
def reconsideration_env(approval_env):
    service, requester, rejector, request, env = approval_env
    service.request_approval(requester, request)
    rejection = service.decide_approval(rejector, _decide(request, "REJECT"))
    fresh_actor = _actor(env)
    fresh = env[1].create(
        fresh_actor,
        request.project_id,
        "SCIENTIFIC_CONCLUSION_VERSION",
        request.scientific_conclusion_version_id,
        "SCIENTIFIC",
        "ACCEPT",
        (
            f"TEST ONLY correction of review {request.review_ids[0]}: "
            "the earlier assessment confused the measured population with the study population; "
            "the frozen evidence supports the original statement."
        ),
        (),
        uuid4(),
    )
    actor = approver_actor(env)
    command = RecordRejectionReconsiderationCommand(
        uuid4(),
        request.project_id,
        request.scientific_conclusion_version_id,
        "INTERNAL_SCIENTIFIC_RELEASE",
        "CORRECTED_REVIEW",
        (rejection.id,),
        (fresh.id,),
        (
            f"TEST ONLY rejection {rejection.id} relied on review {request.review_ids[0]}; "
            "the independent correction explains the population error against frozen evidence."
        ),
        corrected_review_ids=request.review_ids,
    )
    return env[0], command, actor, approval_env


def test_correction_same_material_successor_and_replay(reconsideration_env):
    decisions, command, actor, approval = reconsideration_env
    service, requester, _, old, env = approval
    result = decisions.record_rejection_reconsideration(command, actor)
    assert result.decision == "CORRECTED_REVIEW"
    assert result.current_coverage_complete and result.successor_request_id is None
    assert result.cited_rejected_request_ids == (old.id,)
    assert decisions.record_rejection_reconsideration(command, actor) == result
    successor = replace(
        old, id=uuid4(), prior_rejected_request_id=old.id, reconsideration_decision_id=result.id
    )
    saved = service.request_approval(requester, successor)
    assert saved.reconsideration_decision_id == result.id
    assert service.request_approval(requester, successor) == saved
    updated = decisions.get_rejection_reconsideration(command.project_id, result.id, actor)
    assert updated.successor_request_id == successor.id
    assert updated.content_hash == result.content_hash
    approver = approver_actor(env)
    decision = service.decide_approval(approver, _decide(successor))
    assert decision.grant and decision.grant.usable
    with env[-1][8].connect() as conn:
        assert (
            conn.execute(
                text("SELECT status FROM approval_requests WHERE id=:id"), {"id": old.id}
            ).scalar_one()
            == "DECIDED"
        )
        assert conn.execute(text("SELECT count(*) FROM approval_grants")).scalar_one() == 1


@pytest.mark.parametrize(
    "change,code",
    [
        ({"rationale": "Changed replay"}, ErrorCode.IDEMPOTENCY_CONFLICT),
        ({"scientific_conclusion_version_id": uuid4()}, ErrorCode.IDEMPOTENCY_CONFLICT),
    ],
)
def test_changed_replay_conflicts(reconsideration_env, change, code):
    service, command, actor, _ = reconsideration_env
    service.record_rejection_reconsideration(command, actor)
    with pytest.raises(ResearchBaseError) as denied:
        service.record_rejection_reconsideration(replace(command, **change), actor)
    assert denied.value.code is code


@pytest.mark.parametrize(
    "change",
    [
        {"rationale": "Opinion changed without an explanation of the rejection"},
        {"fresh_review_ids": (uuid4(),)},
        {"corrected_review_ids": (uuid4(),)},
        {"rejected_approval_decision_ids": (uuid4(),)},
    ],
)
def test_missing_evidence_denies_atomically(reconsideration_env, change):
    service, command, actor, approval = reconsideration_env
    before = fixtures._counts(approval)
    with pytest.raises(ResearchBaseError):
        service.record_rejection_reconsideration(replace(command, **change), actor)
    assert fixtures._counts(approval) == before


def test_owner_alone_denied(reconsideration_env):
    service, command, _, approval = reconsideration_env
    owner = _actor(approval[-1])
    with pytest.raises(ResearchBaseError) as denied:
        service.record_rejection_reconsideration(command, owner)
    assert denied.value.code is ErrorCode.FORBIDDEN


def test_rejector_cannot_reconsider(reconsideration_env):
    service, command, _, approval = reconsideration_env
    with pytest.raises(ResearchBaseError) as denied:
        service.record_rejection_reconsideration(command, approval[2])
    assert denied.value.code is ErrorCode.CONFLICT_OF_INTEREST


@pytest.fixture
def revised_env(approval_env):
    from researchbase.application.internal_review import ReviewIssueRequest
    from researchbase.application.revision_action import (
        RecordRevisionActionCommand,
        RevisionActionService,
    )
    from researchbase.application.scientific_conclusion import ClaimInputRequest
    from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE

    service, requester, rejector, request, env = approval_env
    service.request_approval(requester, request)
    rejected = service.decide_approval(rejector, _decide(request, "REJECT"))
    base = env[-1]
    old_review = env[1].create(
        env[2],
        request.project_id,
        "SCIENTIFIC_CONCLUSION_VERSION",
        request.scientific_conclusion_version_id,
        "SCIENTIFIC",
        "MAJOR_REVISION",
        "TEST ONLY narrow the stated population",
        (ReviewIssueRequest("MAJOR", "OVERCLAIM", "TEST ONLY broad population"),),
        uuid4(),
    )
    scientific = base[0]
    target = scientific.revise(
        base[3],
        base[5],
        env[3].conclusion_id,
        "TEST ONLY refined conclusion for the measured population",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(base[6], "SUPPORTS"),),
        (),
        uuid4(),
    )
    scientific.freeze(base[3], base[5], target.conclusion_id, target.version_id, uuid4())
    revision = RevisionActionService(base[1], base[9], base[2]).record_revision_action(
        base[3],
        RecordRevisionActionCommand(
            uuid4(),
            base[5],
            "CONCLUSION_CHANGE",
            old_review.issues[0].id,
            result_scientific_conclusion_version_id=target.version_id,
        ),
    )
    fresh_actor = _actor(env)
    fresh = env[1].create(
        fresh_actor,
        base[5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        target.version_id,
        "SCIENTIFIC",
        "ACCEPT",
        f"TEST ONLY the restricted population addresses rejection {rejected.id}.",
        (),
        uuid4(),
    )
    actor = approver_actor(env)
    command = RecordRejectionReconsiderationCommand(
        uuid4(),
        base[5],
        target.version_id,
        "INTERNAL_SCIENTIFIC_RELEASE",
        "REVISED_TARGET",
        (rejected.id,),
        (fresh.id,),
        (
            f"TEST ONLY addresses rejection {rejected.id} through a restricted population, "
            "independently reviewed."
        ),
        revision_action_ids=(revision.id,),
    )
    return env[0], command, actor, approval_env


def test_revised_target_and_exact_revision_hash(revised_env):
    service, command, actor, _ = revised_env
    saved = service.record_rejection_reconsideration(command, actor)
    assert saved.decision == "REVISED_TARGET"
    assert {r.id for r in saved.basis if r.type == "RevisionAction"} == set(
        command.revision_action_ids
    )
    assert service.record_rejection_reconsideration(command, actor) == saved


def test_new_review_requires_complete_eligible_set(reconsideration_env):
    service, command, actor, approval = reconsideration_env
    env = approval[-1]
    env[1].create(
        _actor(env),
        command.project_id,
        "SCIENTIFIC_CONCLUSION_VERSION",
        command.scientific_conclusion_version_id,
        "SCIENTIFIC",
        "UNCERTAIN",
        "TEST ONLY independent additional assessment",
        (),
        uuid4(),
    )
    with pytest.raises(ResearchBaseError) as denied:
        service.record_rejection_reconsideration(command, actor)
    assert denied.value.code is ErrorCode.DECISION_BASIS_INVALID


def test_evidence_roles_are_part_of_replay(reconsideration_env):
    service, command, actor, _ = reconsideration_env
    service.record_rejection_reconsideration(command, actor)
    with pytest.raises(ResearchBaseError) as denied:
        service.record_rejection_reconsideration(
            replace(
                command,
                fresh_review_ids=command.corrected_review_ids,
                corrected_review_ids=command.fresh_review_ids,
            ),
            actor,
        )
    assert denied.value.code is ErrorCode.IDEMPOTENCY_CONFLICT


def test_reconsideration_cannot_replace_affirmative_basis(reconsideration_env):
    service, command, actor, approval = reconsideration_env
    saved = service.record_rejection_reconsideration(command, actor)
    approvals, requester, _, old, _ = approval
    with pytest.raises(ResearchBaseError):
        approvals.request_approval(
            requester,
            replace(
                old,
                id=uuid4(),
                basis_decision_id=saved.id,
                prior_rejected_request_id=old.id,
                reconsideration_decision_id=saved.id,
            ),
        )


def test_historical_read_and_replay_after_write_role_loss(reconsideration_env):
    from researchbase.application.phase2_identity import CloseProjectRole

    service, command, actor, approval = reconsideration_env
    saved = service.record_rejection_reconsideration(command, actor)
    env = approval[-1]
    with env[-1][8].connect() as conn:
        role = conn.execute(
            text(
                "SELECT id FROM project_role_assignments WHERE actor_id=:actor AND role='APPROVER'"
            ),
            {"actor": actor.actor_id},
        ).scalar_one()
    identity, _, _ = identity_service(str(env[-1][8].url))
    identity.close_project_role(
        CloseProjectRole(env[2], command.project_id, role, "TEST ONLY close writer", uuid4())
    )
    assert service.record_rejection_reconsideration(command, actor) == saved
    assert service.get_rejection_reconsideration(command.project_id, saved.id, actor) == saved
    env[-1][9].principals.pop(actor.actor_id)
    with pytest.raises(ResearchBaseError) as denied:
        service.get_rejection_reconsideration(command.project_id, saved.id, actor)
    assert denied.value.code is ErrorCode.FORBIDDEN


def test_later_rejection_invalidates_unused_coverage_but_not_history(reconsideration_env):
    service, command, actor, approval = reconsideration_env
    approvals, requester, _, old, env = approval
    saved = service.record_rejection_reconsideration(command, actor)
    unused_command = replace(command, id=uuid4())
    unused = service.record_rejection_reconsideration(unused_command, actor)
    successor = replace(
        old, id=uuid4(), prior_rejected_request_id=old.id, reconsideration_decision_id=saved.id
    )
    approvals.request_approval(requester, successor)
    approvals.decide_approval(approver_actor(env), _decide(successor, "REJECT"))
    historical = service.get_rejection_reconsideration(command.project_id, unused.id, actor)
    assert not historical.current_coverage_complete
    assert historical.successor_request_id is None
    assert service.record_rejection_reconsideration(unused_command, actor) == historical
    with pytest.raises(ResearchBaseError) as denied:
        approvals.request_approval(
            requester, replace(successor, id=uuid4(), reconsideration_decision_id=unused.id)
        )
    assert denied.value.code is ErrorCode.REJECTION_RECONSIDERATION_REQUIRED


@pytest.mark.parametrize("kind", ["reconsiderer", "fresh_reviewer"])
def test_successor_requester_independence(reconsideration_env, kind):
    service, command, actor, approval = reconsideration_env
    saved = service.record_rejection_reconsideration(command, actor)
    approvals, _, _, old, env = approval
    requester = actor
    if kind == "fresh_reviewer":
        with env[-1][8].connect() as conn:
            reviewer = conn.execute(
                text("SELECT reviewer_actor_id FROM internal_review_records WHERE id=:id"),
                {"id": command.fresh_review_ids[0]},
            ).scalar_one()
        requester = env[-1][9].principals[reviewer]
    with pytest.raises(ResearchBaseError) as denied:
        approvals.request_approval(
            requester,
            replace(
                old,
                id=uuid4(),
                prior_rejected_request_id=old.id,
                reconsideration_decision_id=saved.id,
            ),
        )
    assert denied.value.code is ErrorCode.CONFLICT_OF_INTEREST


@pytest.mark.parametrize("stage", range(1, 6))
def test_rollback_after_each_staged_insert(reconsideration_env, monkeypatch, stage):
    from researchbase.persistence.decision_repository import SqlAlchemyDecisionRepository

    service, command, actor, approval = reconsideration_env
    original = SqlAlchemyDecisionRepository._insert
    calls = []

    def fail_after(self, table, row):
        original(self, table, row)
        calls.append(table)
        if len(calls) == stage:
            raise RuntimeError("TEST ONLY staged failure")

    monkeypatch.setattr(SqlAlchemyDecisionRepository, "_insert", fail_after)
    with pytest.raises(RuntimeError):
        service.record_rejection_reconsideration(command, actor)
    with approval[-1][-1][8].connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM decision_records WHERE id=:id"), {"id": command.id}
            ).scalar_one()
            == 0
        )
        for table in (
            "decision_basis_conclusions",
            "decision_basis_reviews",
            "decision_basis_approval_decisions",
        ):
            assert (
                conn.execute(
                    text(f"SELECT count(*) FROM {table} WHERE decision_id=:id"), {"id": command.id}
                ).scalar_one()
                == 0
            )


def test_completed_revision_predecessor_history_is_verified(revised_env):
    from researchbase.application.revision_action import (
        RecordRevisionActionCommand,
        RevisionActionService,
    )

    service, command, actor, approval = revised_env
    env = approval[-1]
    base = env[-1]
    with base[8].connect() as conn:
        issue = conn.execute(
            text("SELECT review_issue_id FROM revision_actions WHERE id=:id"),
            {"id": command.revision_action_ids[0]},
        ).scalar_one()
    next_action = RevisionActionService(base[1], base[9], base[2]).record_revision_action(
        base[3],
        RecordRevisionActionCommand(
            uuid4(),
            command.project_id,
            "CONCLUSION_CHANGE",
            issue,
            result_scientific_conclusion_version_id=command.scientific_conclusion_version_id,
            supersedes_revision_action_id=command.revision_action_ids[0],
        ),
    )
    saved = service.record_rejection_reconsideration(
        replace(command, revision_action_ids=(next_action.id,)), actor
    )
    assert {r.id for r in saved.basis if r.type == "RevisionAction"} == {next_action.id}


@pytest.mark.parametrize("kind", ["reconsiderer", "fresh_reviewer"])
def test_successor_approver_independence(reconsideration_env, kind):
    service, command, actor, approval = reconsideration_env
    saved = service.record_rejection_reconsideration(command, actor)
    approvals, requester, _, old, env = approval
    successor = replace(
        old, id=uuid4(), prior_rejected_request_id=old.id, reconsideration_decision_id=saved.id
    )
    approvals.request_approval(requester, successor)
    approver = actor
    if kind == "fresh_reviewer":
        with env[-1][8].connect() as conn:
            reviewer = conn.execute(
                text("SELECT reviewer_actor_id FROM internal_review_records WHERE id=:id"),
                {"id": command.fresh_review_ids[0]},
            ).scalar_one()
        approver = env[-1][9].principals[reviewer]
        identity, _, _ = identity_service(str(env[-1][8].url))
        identity.assign_project_role(
            AssignProjectRole(
                env[2],
                command.project_id,
                reviewer,
                "APPROVER",
                "TEST ONLY fresh reviewer approver",
                uuid4(),
            )
        )
    with pytest.raises(ResearchBaseError) as denied:
        approvals.decide_approval(approver, _decide(successor))
    assert denied.value.code is ErrorCode.CONFLICT_OF_INTEREST


def test_shared_decision_uuid_namespace_maps_reconsideration_conflict(reconsideration_env):
    service, command, actor, approval = reconsideration_env
    ordinary = approval[3].basis_decision_id
    # Disclosure first: the existing submission actor owns ordinary Decision history.
    original_actor = approval[-1][2]
    with pytest.raises(ResearchBaseError) as denied:
        service.record_rejection_reconsideration(replace(command, id=ordinary), original_actor)
    assert denied.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    with pytest.raises(ResearchBaseError) as missing:
        service.get_rejection_reconsideration(command.project_id, ordinary, actor)
    assert missing.value.code is ErrorCode.NOT_FOUND


def test_review_future_timestamp_cannot_fake_freshness(approval_env):
    from researchbase.domain.internal_review import review_material
    from researchbase.foundation.hashing import sha256_canonical_json
    from tests.integration.phase2.test_b10_reconsideration_schema import normal_role

    approvals, requester, rejector, request, env = approval_env
    reviewer = _actor(env)
    identity = uuid4()
    summary = (
        f"TEST ONLY correction of {request.review_ids[0]}: "
        "earlier assessment confused the measured and study populations; "
        "frozen evidence supports the stated population."
    )
    with env[-1][8].begin() as conn:
        normal_role(conn)
        target_hash = conn.execute(
            text("SELECT content_hash FROM scientific_conclusion_versions WHERE id=:id"),
            {"id": request.scientific_conclusion_version_id},
        ).scalar_one()
        digest = str(
            sha256_canonical_json(
                review_material(
                    request.project_id,
                    "ScientificConclusionVersion",
                    request.scientific_conclusion_version_id,
                    target_hash,
                    reviewer.actor_id,
                    "SCIENTIFIC",
                    "ACCEPT",
                    summary,
                )
            )
        )
        actual = conn.execute(
            text("""INSERT INTO internal_review_records
         (id,project_id,scientific_conclusion_version_id,target_content_hash,reviewer_actor_id,
          review_type,recommendation,summary,created_at,content_hash,hash_scheme)
         VALUES (:id,:project,:target,:target_hash,:actor,'SCIENTIFIC','ACCEPT',:summary,
          clock_timestamp()+interval '365 days',:hash,'sha256-cjson-v1') RETURNING created_at"""),
            {
                "id": identity,
                "project": request.project_id,
                "target": request.scientific_conclusion_version_id,
                "target_hash": target_hash,
                "actor": reviewer.actor_id,
                "summary": summary,
                "hash": digest,
            },
        ).scalar_one()
        assert actual <= conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        role = conn.execute(text("SELECT current_user")).scalar_one()
        conn.execute(text("RESET ROLE"))
        conn.execute(text(f"DROP OWNED BY {role}"))
        conn.execute(text(f"DROP ROLE {role}"))
    approvals.request_approval(requester, request)
    rejected = approvals.decide_approval(rejector, _decide(request, "REJECT"))
    command = RecordRejectionReconsiderationCommand(
        uuid4(),
        request.project_id,
        request.scientific_conclusion_version_id,
        "INTERNAL_SCIENTIFIC_RELEASE",
        "CORRECTED_REVIEW",
        (rejected.id,),
        (identity,),
        (
            f"TEST ONLY rejection {rejected.id} relied on review {request.review_ids[0]}; "
            "the review corrects its population error."
        ),
        corrected_review_ids=request.review_ids,
    )
    with pytest.raises(ResearchBaseError) as denied:
        env[0].record_rejection_reconsideration(command, approver_actor(env))
    assert denied.value.code is ErrorCode.DECISION_BASIS_INVALID


def test_missing_revision_maps_basis_error_and_rolls_back(revised_env):
    service, command, actor, approval = revised_env
    before = fixtures._counts(approval)
    with pytest.raises(ResearchBaseError) as denied:
        service.record_rejection_reconsideration(
            replace(command, revision_action_ids=(uuid4(),)), actor
        )
    assert denied.value.code is ErrorCode.DECISION_BASIS_INVALID
    assert fixtures._counts(approval) == before
    with approval[-1][-1][8].connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM decision_records WHERE id=:id"), {"id": command.id}
            ).scalar_one()
            == 0
        )


def test_invalidated_target_maps_stale_error_and_rolls_back(reconsideration_env):
    service, command, actor, approval = reconsideration_env
    fixtures._stale(approval[-1])
    before = fixtures._counts(approval)
    with pytest.raises(ResearchBaseError) as denied:
        service.record_rejection_reconsideration(command, actor)
    assert denied.value.code is ErrorCode.APPROVAL_TARGET_STALE
    assert fixtures._counts(approval) == before
    with approval[-1][-1][8].connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM decision_records WHERE id=:id"), {"id": command.id}
            ).scalar_one()
            == 0
        )
