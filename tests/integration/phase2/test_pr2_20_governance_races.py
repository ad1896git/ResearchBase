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


def test_h2_decision_passive_inventory_and_first_statement(decision_env):
    from sqlalchemy import create_engine, event

    from researchbase.persistence.approval_repository import B09_SHARE_SQL, B09_SNAPSHOT_TABLES
    from tests.integration.phase2.test_pr2_15_decision import _command, _review

    engine = decision_env[-1][8]
    observer = create_engine(engine.url)
    witnesses = []
    _review(decision_env)

    def observed(conn, cursor, sql, parameters, context, many):
        if sql == B09_SHARE_SQL:
            pid = conn.connection.driver_connection.info.backend_pid
            witnesses.append(s.passive_locks(observer, (pid,)))

    event.listen(engine, "after_cursor_execute", observed)
    try:
        with s.capture(engine) as captured:
            decision_env[0].record_decision(decision_env[2], _command(decision_env))
        writers = [tx for tx in captured.transactions if B09_SHARE_SQL in tx]
        assert len(writers) == 1 and writers[0][0] == B09_SHARE_SQL
        assert len(witnesses) == 1
        inventory = {
            row["relname"]
            for row in witnesses[0]["locks"]
            if row["mode"] == "ShareLock" and row["granted"]
        }
        assert inventory == set(B09_SNAPSHOT_TABLES)
        assert witnesses[0]["observer_isolation"] == "repeatable read"
        s.save_observation(
            "h2-decision-retained-inventory",
            dict(
                status="BLOCKED",
                reason="Retain unchanged inventories; reference-host measurement unavailable",
                first_sql=writers[0][0],
                witnesses=witnesses,
            ),
        )
    finally:
        event.remove(engine, "after_cursor_execute", observed)
        observer.dispose()


# Substitutions: owning B07 uses decision_revision_concerns (not decision_concern);
# B17's concrete effect is freeze_prepared_submission, never external submission.
from tests.integration.phase2.b17_fixtures import (  # noqa: E402
    b04_env,
    b05_env,
    b17_env,
    revision_env,
)
from tests.integration.phase2.test_approval import approval_env  # noqa: E402
from tests.integration.phase2.test_b10_reconsideration import reconsideration_env  # noqa: E402

_S3_FIXTURES = (b04_env, b05_env, b17_env, revision_env, approval_env, reconsideration_env)


@pytest.mark.parametrize("first", [False, True])
@pytest.mark.parametrize(
    "scenario",
    [
        "revision",
        "concern",
        "disposition",
        "approval",
        "consume",
        "ready",
        "freeze-consent",
        "freeze-withdraw",
    ],
)
def test_s3_owning_both_commit_orders(request, monkeypatch, scenario, first):
    """Reuse exact owning protocols, including their backend witnesses and denial checks."""
    from tests.integration.phase2 import (
        test_b06_revision_concurrency as b06,
    )
    from tests.integration.phase2 import (
        test_b07_concurrency as b07,
    )
    from tests.integration.phase2 import (
        test_b08_concurrency as b08,
    )
    from tests.integration.phase2 import (
        test_b09_approval_concurrency as b09,
    )
    from tests.integration.phase2 import (
        test_b13_grant_concurrency as b13,
    )
    from tests.integration.phase2 import (
        test_b14_ready_concurrency as b14,
    )
    from tests.integration.phase2 import (
        test_b17_freeze_concurrency as b17,
    )

    if scenario == "revision":
        b06.test_owning_source_and_evidence_writers_have_observed_commit_orders(
            request.getfixturevalue("revision_env"),
            "source",
            "action_first" if first else "writer_first",
        )
    elif scenario == "concern":
        b07.test_link_and_predecessor_correction_serialize_on_exact_action(
            request.getfixturevalue("revision_env"), "link_first" if first else "correction_first"
        )
    elif scenario == "disposition":
        b08.test_correction_and_disposition_both_commit_orders_without_action_lock_cycle(
            request.getfixturevalue("revision_env"), "disposition" if first else "correction"
        )
    elif scenario == "approval":
        b09.test_cross_target_rejection_request_both_commit_orders(
            request.getfixturevalue("approval_env"), "rejection" if first else "request"
        )
    elif scenario == "consume":
        b13.test_consume_and_maintenance_both_lock_orders(
            request.getfixturevalue("approval_env"), monkeypatch, "revoke", first
        )
    elif scenario == "ready":
        b14.test_zero_issue_review_insert_phantom_both_commit_orders(
            request.getfixturevalue("b05_env"), monkeypatch, first
        )
    else:
        b17.test_author_withdrawal_and_owner_withdrawal_observe_publication_exclusion(
            request.getfixturevalue("b17_env"),
            monkeypatch,
            ("freeze" if first else "withdraw")
            if scenario == "freeze-consent"
            else ("freeze_owner" if first else "owner"),
        )


@pytest.mark.parametrize(
    "scenario",
    ["revision", "concern", "disposition", "approval", "reconsideration", "ready", "freeze"],
)
def test_s3_post_wait_denial_is_atomic(request, monkeypatch, scenario):
    from tests.integration.phase2 import (
        test_b06_revision_concurrency as b06,
    )
    from tests.integration.phase2 import (
        test_b07_concurrency as b07,
    )
    from tests.integration.phase2 import (
        test_b08_concurrency as b08,
    )
    from tests.integration.phase2 import (
        test_b09_approval_concurrency as b09,
    )
    from tests.integration.phase2 import (
        test_b10_reconsideration_concurrency as b10,
    )
    from tests.integration.phase2 import (
        test_b14_ready_concurrency as b14,
    )
    from tests.integration.phase2 import (
        test_b17_freeze_concurrency as b17,
    )

    if scenario == "revision":
        env = request.getfixturevalue("revision_env")
        before = s.manifest(env[2][-1][8], ("revision_actions", "revision_action_re_reviews"))
        b06.test_first_inventory_wait_rechecks_expired_credentials_and_uses_bounded_profile(env)
        assert s.manifest(env[2][-1][8], tuple(before)) == before
    elif scenario == "concern":
        b07.test_mutable_inventory_writer_wait_has_backend_evidence_and_fresh_authority(
            request.getfixturevalue("revision_env"), "link", "project_role_assignments"
        )
    elif scenario == "disposition":
        b08.test_first_inventory_wait_bounds_and_rechecks_revoked_credential(
            request.getfixturevalue("revision_env"), "projects"
        )
    elif scenario == "approval":
        b09.test_scheduled_approver_expiry_after_real_grant_wait_rolls_back(
            request.getfixturevalue("approval_env")
        )
    elif scenario == "reconsideration":
        b10.test_credential_loss_across_first_inventory_wait_rolls_back(
            request.getfixturevalue("reconsideration_env"), "inventory"
        )
    elif scenario == "ready":
        b14.test_required_real_wait_crosses_grant_expiry(
            request.getfixturevalue("b05_env"), "table"
        )
    else:
        b17.test_actual_issuer_revocation_at_observed_wait_rolls_back(
            request.getfixturevalue("b17_env"), monkeypatch, "prefix"
        )


def _s3_contend(engine, first, followers, prefix):
    """Hold a real writer; require each contender to be observed waiting in PostgreSQL."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from time import monotonic

    from sqlalchemy import event, text

    entered, release = Event(), Event()
    holder = []

    def pause(conn, cursor, sql, parameters, context, many):
        if sql.startswith(prefix) and not entered.is_set():
            holder.append(conn.connection.driver_connection.info.backend_pid)
            entered.set()
            assert release.wait(20)

    event.listen(engine, "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=1 + len(followers)) as pool:
            leader = pool.submit(first)
            assert entered.wait(15)
            pending = [pool.submit(call) for call in followers]
            try:
                deadline = monotonic() + 15
                seen = set()
                while len(seen) < len(followers):
                    with s.read_snapshot(engine) as conn:
                        rows = (
                            conn.execute(
                                text(
                                    "WITH RECURSIVE blocked(pid) AS ("
                                    "SELECT pid FROM pg_stat_activity WHERE "
                                    ":holder=ANY(pg_blocking_pids(pid)) UNION "
                                    "SELECT a.pid FROM pg_stat_activity a JOIN blocked b "
                                    "ON b.pid=ANY(pg_blocking_pids(a.pid))) "
                                    "SELECT b.pid FROM blocked b WHERE EXISTS "
                                    "(SELECT 1 FROM pg_locks l WHERE l.pid=b.pid AND NOT l.granted)"
                                ),
                                {"holder": holder[0]},
                            )
                            .scalars()
                            .all()
                        )
                    seen.update(rows)
                    assert monotonic() < deadline, (seen, len(followers))
                    if len(seen) < len(followers):
                        Event().wait(0.01)
                assert holder[0] not in seen
                s.save_observation(
                    "s3-contention-" + prefix.split()[-1],
                    dict(holder=holder[0], waiter_pids=sorted(seen)),
                )
            finally:
                release.set()
            saved = leader.result(timeout=20)
            return saved, [future.result(timeout=20) for future in pending]
    finally:
        release.set()
        event.remove(engine, "after_cursor_execute", pause)


@pytest.mark.parametrize("workers", [1, 4])
@pytest.mark.parametrize("same_key", [False, True])
def test_s3_package_freeze_workers_wait_and_single_effect(b17_env, workers, same_key):
    from dataclasses import replace
    from uuid import uuid4

    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from tests.integration.phase2.b17_fixtures import counts

    f = b17_env
    before = counts(f)

    def call(command):
        try:
            return f.app.freeze_prepared_submission(f.actor, command)
        except ResearchBaseError as exc:
            return exc.code

    commands = [
        f.command if same_key else replace(f.command, command_key=uuid4())
        for _ in range(workers - 1)
    ]
    followers = [lambda command=command: call(command) for command in commands]
    saved, results = _s3_contend(
        f.engine, lambda: call(f.command), followers, "INSERT INTO approval_grant_consumptions"
    )
    assert not isinstance(saved, ErrorCode)
    for result in results:
        # Owning contract: test_b17_package_freeze.py::
        # test_consumed_grant_cannot_freeze_a_fresh_package.
        assert result == saved if same_key else result == ErrorCode.GRANT_INVALID
    after = counts(f)
    assert after[3] == before[3] + 1
    assert after[2] == before[2] + 1
    assert f.app.freeze_prepared_submission(f.actor, f.command) == saved


@pytest.mark.parametrize("first", [False, True])
def test_s3_superseded_manuscript_freeze_trace_race(b05_env, first):
    from uuid import uuid4

    from researchbase.application.manuscript_placement import ClaimPlacementService
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from researchbase.persistence.manuscript_freeze_repository import M1_EDIT_SQL
    from tests.integration.phase2.b30_observations import assert_snapshot_read, sql_protocol
    from tests.integration.phase2.pr2_20_scaled import HISTORY_TABLES, superseded_manuscript_history

    env = b05_env
    f = superseded_manuscript_history(env, freeze_successor=False, placements=2)
    before = s.manifest(env[5], HISTORY_TABLES)
    app = ClaimPlacementService(env[4], env[9], env[7])
    query = f["next_query"]
    placement_args = (
        env[2],
        query.project_id,
        query.publication_id,
        query.manuscript_version_id,
        env[8],
        None,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "race"},
        "DESCRIPTIVE",
        1,
        uuid4(),
    )

    def trace():
        assert f["trace"].trace(*f["common"]) == f["expected"]
        assert f["manuscripts"].get_manuscript_version(env[2], env[1]) == f["v1"]

    def freeze():
        return f["manuscripts"].freeze_manuscript_version(env[2], f["freeze_command"])

    def place():
        return app.add(*placement_args)

    # The leader holds M1's editing inventory while the exact historical read completes.
    # _s3_contend requires pg_stat_activity/pg_locks evidence for the losing writer.
    def leader():
        return (freeze if first else place)()

    def follower():
        trace()
        try:
            return (place if first else freeze)()
        except ResearchBaseError as exc:
            return exc.code

    saved, denied = _s3_contend(env[5], leader, [follower], M1_EDIT_SQL)
    assert denied == [
        ErrorCode.INVALID_STATE_TRANSITION if first else ErrorCode.CONCURRENT_MODIFICATION
    ]
    with sql_protocol(env[5]) as observed:
        trace()
    assert_snapshot_read(observed, snapshots=2)
    # Account for the winning placement while comparing every other complete row/edge.
    after = s.manifest(env[5], HISTORY_TABLES)
    if not first:
        expected = {**before, "manuscript_claim_placements": after["manuscript_claim_placements"]}
        assert after == expected
        placement_rows = "manuscript_claim_placements"
        assert after[placement_rows]["count"] == before[placement_rows]["count"] + 1
        old_ids = {row["id"] for row in before[placement_rows]["ids_hashes_edges"]}
        new_ids = {row["id"] for row in after[placement_rows]["ids_hashes_edges"]}
        assert new_ids - old_ids == {str(saved.id)}
    # No losing placement, partial seal, or pointer movement survives the wait/denial.
    current = f["manuscripts"].get_manuscript_version(env[2], query)
    assert current.status == ("FROZEN" if first else "DRAFT")
    assert len(
        app.trace(env[2], query.project_id, query.publication_id, query.manuscript_version_id)
    ) == (1 if first else 2)
    from sqlalchemy import text

    with env[5].connect() as conn:
        assert conn.execute(
            text("SELECT current_manuscript_version_id FROM publications WHERE id=:id"),
            {"id": query.publication_id},
        ).scalar_one() == (query.manuscript_version_id if first else env[1].manuscript_version_id)
    # A fresh preview can seal after the committed placement; a saved seal replays exactly.
    from dataclasses import replace

    from tests.integration.phase2.test_b04_manuscript_freeze import freeze as seal

    completed = (
        f["manuscripts"].get_manuscript_version(env[2], query)
        if first
        else seal(f["manuscripts"], env[2], query)
    )
    if first:
        assert completed == saved
    assert completed.version_number == 2
    replay = replace(
        f["freeze_command"],
        expected_placement_set_hash=completed.placement_set_hash,
        expected_content_hash=completed.content_hash,
    )
    assert f["manuscripts"].freeze_manuscript_version(env[2], replay) == completed


def test_s3_superseded_manuscript_post_wait_denial_is_atomic(b05_env, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event, current_thread
    from uuid import uuid4

    from sqlalchemy import event

    from researchbase.application.manuscript_placement import ClaimPlacementService
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from tests.integration.phase2.pr2_20_scaled import HISTORY_TABLES, superseded_manuscript_history
    from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

    env = b05_env
    f = superseded_manuscript_history(env, freeze_successor=False, placements=2)
    before = s.manifest(env[5], HISTORY_TABLES)
    credentials = env[9]
    original = credentials.is_valid
    revoked = Event()
    entered, release = Event(), Event()
    holder_pids = []
    monkeypatch.setattr(
        credentials, "is_valid", lambda p, at: not revoked.is_set() and original(p, at)
    )

    def before_commit(conn):
        # The competing Application placement has passed its final authorization.
        # Pause before DB commit, retaining its real M1 inventory and row writes.
        if current_thread().name.startswith("s3-placement-holder"):
            holder_pids.append(conn.connection.driver_connection.info.backend_pid)
            entered.set()
            assert release.wait(20)

    query = f["next_query"]
    app = ClaimPlacementService(env[4], credentials, env[7])
    event.listen(env[5], "commit", before_commit)
    try:
        with (
            ThreadPoolExecutor(max_workers=1, thread_name_prefix="s3-placement-holder") as leader,
            ThreadPoolExecutor(max_workers=1) as follower,
        ):
            winner = leader.submit(
                app.add,
                env[2],
                query.project_id,
                query.publication_id,
                query.manuscript_version_id,
                env[8],
                None,
                "RESULTS",
                {"kind": "PARAGRAPH", "value": "credential-race"},
                "DESCRIPTIVE",
                1,
                uuid4(),
            )
            try:
                assert entered.wait(15)
                pending = follower.submit(
                    f["manuscripts"].freeze_manuscript_version, env[2], f["freeze_command"]
                )
                witness = _wait_for_pg_blocker(env[5], holder_pids[0], "relation")
                assert witness["mode"] == "ExclusiveLock"
                revoked.set()
                s.save_observation(
                    "s3-history-post-wait-denial",
                    {
                        key: witness[key]
                        for key in (
                            "pid",
                            "state",
                            "wait_event_type",
                            "locktype",
                            "mode",
                            "relation",
                            "blocking_pids",
                        )
                    },
                )
            finally:
                release.set()
            saved = winner.result(timeout=15)
            with pytest.raises(ResearchBaseError) as caught:
                pending.result(timeout=15)
            assert caught.value.code == ErrorCode.FORBIDDEN
    finally:
        release.set()
        event.remove(env[5], "commit", before_commit)
    # Only the successful placement is allowed to change; denied freeze is wholly atomic.
    after = s.manifest(env[5], HISTORY_TABLES)
    assert after == {**before, "manuscript_claim_placements": after["manuscript_claim_placements"]}
    placement_rows = "manuscript_claim_placements"
    assert after[placement_rows]["count"] == before[placement_rows]["count"] + 1
    old_ids = {row["id"] for row in before[placement_rows]["ids_hashes_edges"]}
    new_ids = {row["id"] for row in after[placement_rows]["ids_hashes_edges"]}
    assert new_ids - old_ids == {str(saved.id)}
    revoked.clear()
    assert f["trace"].trace(*f["common"]) == f["expected"]
    from tests.integration.phase2.test_b04_manuscript_freeze import freeze

    assert freeze(f["manuscripts"], env[2], query).version_number == 2


def test_s3_superseded_manuscript_mid_seal_failure_is_atomic(b05_env):
    from sqlalchemy import event

    from tests.integration.phase2.pr2_20_scaled import HISTORY_TABLES, superseded_manuscript_history

    env = b05_env
    f = superseded_manuscript_history(env, freeze_successor=False, placements=2)
    before = s.manifest(env[5], HISTORY_TABLES)

    def fail(conn, cursor, sql, parameters, context, many):
        if sql.startswith("UPDATE publications SET current_manuscript_version_id"):
            raise RuntimeError("S3 injected after successor pointer update")

    event.listen(env[5], "after_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="S3 injected"):
            f["manuscripts"].freeze_manuscript_version(env[2], f["freeze_command"])
    finally:
        event.remove(env[5], "after_cursor_execute", fail)
    assert s.manifest(env[5], HISTORY_TABLES) == before
    assert f["trace"].trace(*f["common"]) == f["expected"]
    assert (
        f["manuscripts"].freeze_manuscript_version(env[2], f["freeze_command"]).version_number == 2
    )


@pytest.mark.parametrize("workers", [1, 4])
@pytest.mark.parametrize("freeze_first", [False, True])
def test_s3_freeze_consent_withdrawal_and_replay_workers(b17_env, workers, freeze_first):
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from tests.integration.phase2.b17_fixtures import counts, withdraw_consent

    f = b17_env
    before = counts(f)

    def freeze():
        try:
            return f.app.freeze_prepared_submission(f.actor, f.command)
        except ResearchBaseError as exc:
            return exc.code

    def withdraw():
        return withdraw_consent(f)

    if workers == 1:
        (freeze if freeze_first else withdraw)()
        result = (withdraw if freeze_first else freeze)()
        if not freeze_first:
            assert result == ErrorCode.GRANT_STALE
    else:
        first = freeze if freeze_first else withdraw
        followers = [withdraw, freeze, freeze] if freeze_first else [freeze] * 3
        _, results = _s3_contend(
            f.engine,
            first,
            followers,
            "INSERT INTO approval_grant_consumptions"
            if freeze_first
            else "INSERT INTO author_consents",
        )
        if not freeze_first:
            assert results == [ErrorCode.GRANT_STALE] * 3
        else:
            assert results[1] == results[2]
            assert results[1] == f.app.freeze_prepared_submission(f.actor, f.command)
    after = counts(f)
    assert after[3] == before[3] + int(freeze_first)
    assert after[2] == before[2] + int(freeze_first)
    assert after[1] == before[1] + int(freeze_first)  # one consent manifest item
    assert after[5] == before[5] + 1
    package = f.app.get_prepared_submission(f.actor, f.query)
    assert package.status == ("FROZEN" if freeze_first else "PREPARED")


@pytest.mark.parametrize("workers", [1, 4])
@pytest.mark.parametrize("same_key", [False, True])
def test_s3_disposition_workers_wait_and_one_terminal_event(revision_env, workers, same_key):
    from dataclasses import replace
    from uuid import uuid4

    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from tests.integration.phase2.b08_support import disposition_case

    app, actor, command, base, _ = disposition_case(revision_env)
    before = s.manifest(base[8], ("revision_actions", "decision_records"))

    def invoke(command):
        try:
            return app.record_issue_disposition(actor, command)
        except ResearchBaseError as exc:
            return exc.code

    commands = [command if same_key else replace(command, id=uuid4()) for _ in range(workers - 1)]
    saved, results = _s3_contend(
        base[8],
        lambda: invoke(command),
        [lambda command=command: invoke(command) for command in commands],
        "INSERT INTO review_issue_events",
    )
    for result in results:
        assert result == saved if same_key else result == ErrorCode.INVALID_STATE_TRANSITION
    history = app.get_issue_history(actor, base[5], command.review_issue_id)
    assert len(history.events) == 2 and history.disposition == saved
    assert s.manifest(base[8], tuple(before)) == before


@pytest.mark.parametrize("kind", ["decision", "action", "link", "disposition"])
def test_s3_revision_midwrite_failure_rolls_back_complete_graph(revision_env, kind):
    from sqlalchemy import event

    from tests.integration.phase2.b08_support import disposition_case
    from tests.integration.phase2.test_b07_concurrency import prepared

    engine = revision_env[2][-1][8]
    if kind == "disposition":
        app, actor, command, _, _ = disposition_case(revision_env)

        def write():
            return app.record_issue_disposition(actor, command)
    else:
        write, _ = prepared(revision_env, kind)
    tables = (
        "decision_records",
        "decision_basis_reviews",
        "decision_revision_concerns",
        "decision_basis_claims",
        "decision_basis_conclusions",
        "revision_actions",
        "revision_action_re_reviews",
        "review_issue_events",
        "review_issues",
    )
    before = s.manifest(engine, tables)
    target = {
        "decision": "decision_records",
        "action": "revision_actions",
        "link": "revision_action_re_reviews",
        "disposition": "review_issue_events",
    }[kind]

    def fail(conn, cursor, sql, parameters, context, many):
        if sql.startswith("INSERT INTO " + target):
            raise RuntimeError("S3 injected after parent/edge insertion")

    event.listen(engine, "after_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="S3 injected"):
            write()
    finally:
        event.remove(engine, "after_cursor_execute", fail)
    assert s.manifest(engine, tables) == before
    assert write()


@pytest.mark.parametrize("workers", [1, 4])
@pytest.mark.parametrize("kind", ["decision", "action", "link"])
def test_s3_revision_workers_observed_wait_and_exact_replay(revision_env, workers, kind):
    from tests.integration.phase2.test_b07_concurrency import prepared

    write, read = prepared(revision_env, kind)
    engine = revision_env[2][-1][8]
    table = {
        "decision": "decision_records",
        "action": "revision_actions",
        "link": "revision_action_re_reviews",
    }[kind]
    before = s.manifest(engine, ("claim_versions", "scientific_conclusion_versions"))
    saved, results = _s3_contend(engine, write, [write] * (workers - 1), "INSERT INTO " + table)
    assert results == [saved] * (workers - 1)
    assert write() == saved
    assert read()
    assert s.manifest(engine, tuple(before)) == before


@pytest.mark.parametrize("workers", [1, 4])
@pytest.mark.parametrize("same_key", [False, True])
@pytest.mark.parametrize("kind", ["request", "consume", "ready"])
def test_s3_approval_and_consumption_workers_single_effect(request, workers, same_key, kind):
    from dataclasses import replace
    from uuid import uuid4

    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from tests.integration.phase2.test_b13_grant_consumption import issued as release_issued
    from tests.integration.phase2.test_b14_publication_ready import issued as ready_issued

    if kind == "request":
        app, actor, _, command, env = request.getfixturevalue("approval_env")
        engine = env[-1][8]
        operation = app.request_approval
        changed_field = "id"
        table = "approval_requests"
        code = ErrorCode.IDEMPOTENCY_CONFLICT
    elif kind == "consume":
        env = request.getfixturevalue("approval_env")
        app, actor, command, _ = release_issued(env)
        engine = env[-1][-1][8]
        operation = app.record_internal_scientific_release
        changed_field = "command_key"
        table = "approval_grant_consumptions"
        code = ErrorCode.GRANT_INVALID
    else:
        env = request.getfixturevalue("b05_env")
        app, command, _, _ = ready_issued(env)
        actor, engine = env[2], env[5]
        operation = app.transition_publication_ready
        changed_field = "command_key"
        table = "approval_grant_consumptions"
        code = ErrorCode.GRANT_INVALID
    before = s.manifest(engine, (table,))

    def invoke(command):
        try:
            return operation(actor, command)
        except ResearchBaseError as exc:
            return exc.code

    commands = [
        command if same_key else replace(command, **{changed_field: uuid4()})
        for _ in range(workers - 1)
    ]
    saved, results = _s3_contend(
        engine,
        lambda: invoke(command),
        [lambda command=command: invoke(command) for command in commands],
        "INSERT INTO " + table,
    )
    assert not isinstance(saved, ErrorCode)
    for result in results:
        assert result == saved if same_key else result == code
    assert s.manifest(engine, (table,))[table]["count"] == before[table]["count"] + 1
    assert invoke(command) == saved
