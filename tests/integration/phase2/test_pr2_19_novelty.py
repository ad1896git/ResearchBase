"""G7 novelty branch only; package/readiness/consent remain separate blockers."""

from dataclasses import replace
from uuid import UUID, uuid4

import pytest

from researchbase.application.novelty import NoveltyService
from researchbase.domain.novelty import NoveltyOutcome
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2 import b18_novelty_support as b
from tests.integration.phase2 import pr2_19_support as g
from tests.integration.phase2 import pr2_20_support as s

pytest_plugins = ("tests.integration.phase2.pr2_18_fixtures",)
b18_env = b.b18_env


def test_g7_novelty_restart_denials_and_later_resolution(b18_env):
    e = b18_env
    protected = b.protected_manifest(e)
    saved_manifest = s.manifest(e["engine"], b.NOVELTY_TABLES)
    fresh = NoveltyService(e["factory"], e["credentials"], e["literature"])
    e["engine"].dispose()  # Fresh connections and service, retained database and CAS.
    restarted = {}
    for kind in b.KINDS:
        saved = e["saved"][kind]
        restarted[kind] = b.invoke(e, kind, "read", service=fresh)
        assert b.stable(restarted[kind]) == b.stable(saved)
        assert b.stable(b.invoke(e, kind, "replay", service=fresh)) == b.stable(saved)
        assert saved.created_by == e["author"].actor_id
        if kind != "coverage":
            assert saved.assessed_by == e["author"].actor_id
        assert saved.created_at == restarted[kind].created_at
    raw = e["literature"].create(
        e["author"], e["project"], e["source"], "Limitations remain.", uuid4()
    )
    denied = (
        (
            "coverage",
            replace(e["commands"]["coverage"], coverage_limitations="Changed scope"),
            ErrorCode.IDEMPOTENCY_CONFLICT,
        ),
        (
            "prior_art",
            replace(e["commands"]["prior_art"], rationale="Changed comparison"),
            ErrorCode.IDEMPOTENCY_CONFLICT,
        ),
        (
            "novelty",
            replace(e["commands"]["novelty"], limitations="Changed limits"),
            ErrorCode.IDEMPOTENCY_CONFLICT,
        ),
        (
            "coverage",
            replace(e["commands"]["coverage"], id=uuid4(), project_id=e["other_project"]),
            ErrorCode.FORBIDDEN,
        ),
        (
            "prior_art",
            replace(
                e["commands"]["prior_art"], id=uuid4(), literature_evidence_ids=(UUID(raw["id"]),)
            ),
            ErrorCode.INVALID_STATE_TRANSITION,
        ),
        (
            "novelty",
            replace(
                e["commands"]["novelty"],
                id=uuid4(),
                assessment=NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE,
            ),
            ErrorCode.INVALID_STATE_TRANSITION,
        ),
    )
    with pytest.raises(ResearchBaseError) as missing_basis:
        replace(
            e["commands"]["novelty"],
            id=uuid4(),
            assessment=NoveltyOutcome.CLOSE_PRIOR_ART_FOUND,
        )
    assert missing_basis.value.code is ErrorCode.VALIDATION_ERROR
    assert s.manifest(e["engine"], b.NOVELTY_TABLES) == saved_manifest
    for kind, command, code in denied:
        with pytest.raises(ResearchBaseError) as error:
            b.invoke(e, kind, "first", command=command, service=fresh)
        assert error.value.code is code
        assert s.manifest(e["engine"], b.NOVELTY_TABLES) == saved_manifest
    b.resolve_remaining(e)
    later = b.invoke(e, "coverage", "read", service=fresh)
    saved = e["saved"]["coverage"]
    assert (later.query_count, later.result_count, later.resolved_source_count) == (1, 2, 1)
    assert saved.quality.current_unresolved_result_count == 1
    assert later.quality.current_unresolved_result_count == 0
    assert later.quality.captured_unresolved_result_count == 1
    assert b.stable(replace(later, quality=saved.quality)) == b.stable(saved)
    for kind in b.KINDS:
        assert (
            b.invoke(e, kind, "read", service=fresh).content_hash == e["saved"][kind].content_hash
        )
    assert s.manifest(e["engine"], b.NOVELTY_TABLES) == saved_manifest
    assert b.protected_manifest(e) == protected
    g.emit_observation(
        g.ScenarioObservation(
            "G7",
            0,
            "NoveltyService.record_novelty_assessment",
            tuple(e["saved"][k].id for k in b.KINDS),
            None,
            tuple(g.StateDelta(t, protected[t]["count"], protected[t]["count"]) for t in protected),
            tuple(
                g.VerifiedHash(
                    e["saved"][k].id,
                    "content_hash",
                    e["saved"][k].content_hash,
                    restarted[k].content_hash,
                )
                for k in b.KINDS
            ),
            (),
            (),
            (),
        )
    )
    print(
        "B18_G7_SCOPE",
        {
            "novelty_branch": "PASS",
            "combined_G7": "BLOCKED",
            "postgres_version": s.require_pg18(e["engine"]),
            "cardinalities": b.CARDINALITIES,
            "denials": len(denied),
        },
    )


@pytest.mark.parametrize(
    "relation",
    ["IDENTICAL", "HIGHLY_SIMILAR", "PARTIAL_OVERLAP", "RELATED", "CONTRASTING", "UNCLEAR"],
)
def test_g7_six_comparisons_have_exact_history_without_issue_or_gate_effect(b18_env, relation):
    from researchbase.application.novelty import ExactReadQuery
    from researchbase.domain.novelty import PriorArtKind
    from researchbase.persistence.novelty_repository import N
    from tests.integration.phase2.b30_observations import (
        assert_first_share,
        assert_snapshot_read,
        sql_protocol,
    )

    e = b18_env
    protected = b.protected_manifest(e)
    issues = s.manifest(e["engine"], ("review_issues", "review_issue_events"))
    command = replace(e["commands"]["prior_art"], id=uuid4(), relation=PriorArtKind(relation))
    with sql_protocol(e["engine"]) as observed:
        saved = b.invoke(e, "prior_art", "first", command=command)
    assert_first_share(observed, "LOCK TABLE " + ",".join(N) + " IN SHARE MODE")
    assert saved.relation.value == relation
    fresh = NoveltyService(e["factory"], e["credentials"], e["literature"])
    with sql_protocol(e["engine"]) as observed:
        exact = fresh.read_prior_art_relation(e["author"], ExactReadQuery(e["project"], saved.id))
    assert_snapshot_read(observed, snapshots=1)
    # Reviewer-authorized bounded scope pending the owner's §7 replay decision:
    # exact GET is lock-free; command replay equality is still regression-tested.
    # Do not assert lock-free command replay until its owner protocol is resolved.
    replay = fresh.record_prior_art_relation(e["author"], command)
    assert b.stable(exact) == b.stable(saved) == b.stable(replay)
    assert b.protected_manifest(e) == protected
    assert s.manifest(e["engine"], ("review_issues", "review_issue_events")) == issues


def test_g7_selected_failed_and_zero_scope_is_disclosed(b18_env):
    from researchbase.application.novelty import ExactReadQuery
    from researchbase.domain.novelty import QualityWarning
    from tests.integration.phase2.b30_observations import assert_snapshot_read, sql_protocol

    e = b18_env
    command = replace(
        e["commands"]["coverage"],
        id=uuid4(),
        search_execution_ids=e["all_executions"],
        coverage_limitations="Failed and unknown attempts retained; no screening",
    )
    saved = e["service"].record_search_coverage(e["author"], command)
    assert {QualityWarning.FAILED_ATTEMPT, QualityWarning.UNKNOWN_ATTEMPT} <= set(
        saved.quality.warnings
    )
    # The owner fixture's second execution was cancelled before any provider call.
    from sqlalchemy import text

    with e["engine"].connect() as conn:
        zero_id = (
            conn.execute(
                text(
                    "SELECT id FROM literature_search_executions "
                    "WHERE status='CANCELLED' ORDER BY id"
                )
            )
            .scalars()
            .first()
        )
    assert zero_id is not None
    zero_command = replace(command, id=uuid4(), search_execution_ids=(zero_id,))
    zero = e["service"].record_search_coverage(e["author"], zero_command)
    assert zero.query_count == zero.result_count == zero.resolved_source_count == 0
    assert QualityWarning.NO_INVOKED_QUERIES in zero.quality.warnings
    fresh = NoveltyService(e["factory"], e["credentials"], e["literature"])
    with sql_protocol(e["engine"]) as observed:
        exact = fresh.read_search_coverage(e["author"], ExactReadQuery(e["project"], zero.id))
    assert_snapshot_read(observed)
    assert b.stable(exact) == b.stable(zero)
