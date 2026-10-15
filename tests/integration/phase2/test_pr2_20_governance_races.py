"""PR220 adds observation only; owning PR215 nodes retain exact witnessed lock protocols."""

import pytest

from tests.integration.phase2 import pr2_20_support as s
from tests.integration.phase2 import test_pr2_15_decision as owning

conclusion_env = s.conclusion_env
phase2_database_url = s.phase2_database_url
decision_env = s.decision_env
normal_sql_role = owning.normal_sql_role
pytestmark = pytest.mark.integration

# Exact owning nodes reused rather than introducing a parallel lock/retry protocol.
RACE_NODES = (
    "test_complete_basis_every_type_unfavorable_review_r2_and_restart",
    "test_stale_saved_replay_survives_but_unknown_uuid_denies",
    "test_uuid_conflict_new_uuid_and_concurrent_duplicates",
    "test_replay_current_read_authority_survives_write_role_loss",
    "test_credential_revoked_after_observed_target_wait_denies",
    "test_issue_first_observed_wait_refreshes_blockers",
    "test_zero_issue_review_first_observed_wait_includes_committed_review",
    "test_database_failure_mid_basis_rolls_back_then_same_uuid_recovers",
    "test_scheduled_write_role_expiry_during_observed_wait_denies",
    "test_different_independent_actor_cannot_replace_or_impersonate_replay",
)


@pytest.mark.parametrize("node", RACE_NODES)
def test_owning_witnessed_race_basis_rollback_and_authorized_replay(
    decision_env, normal_sql_role, node
):
    engine = decision_env[-1][8]
    before = s.manifest(engine, ("claim_versions", "scientific_conclusion_versions"))
    if "zero_issue_review_first" in node:
        getattr(owning, node)(decision_env, normal_sql_role)
    else:
        getattr(owning, node)(decision_env)
    assert s.manifest(engine, tuple(before)) == before
    s.save_observation(
        node,
        {
            "owning_node": f"{owning.__name__.replace('.', '/')}.py::{node}",
            "immutable_target_manifest": before,
        },
    )


@pytest.mark.parametrize("writer_kind", ["issue", "zero_issue_review"])
def test_decision_first_review_and_issue_wait_preserves_saved_basis(
    decision_env, normal_sql_role, writer_kind
):
    owning.test_decision_first_real_writer_wait_preserves_original_basis(
        decision_env, normal_sql_role, writer_kind
    )


def test_normal_role_issue_first_wait_refreshes_all_blockers(decision_env, normal_sql_role):
    owning.test_normal_role_issue_first_wait_refreshes_blockers(decision_env, normal_sql_role)


@pytest.mark.parametrize("first", ["governance", "decision"])
def test_post_lock_source_impact_both_commit_orders(decision_env, first):
    owning.test_upstream_impact_writer_and_decision_actual_table_wait_both_orders(
        decision_env, first
    )
