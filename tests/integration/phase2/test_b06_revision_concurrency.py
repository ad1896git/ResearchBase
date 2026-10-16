"""Observed B06 write-first locks and lock-free exact-ID snapshot reads."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.revision_action_repository import REVISION_SNAPSHOT_TABLES
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker
from tests.integration.phase2.test_revision_action import (
    conclusion_env,
    decision_env,
    phase2_database_url,
    revision_env,
)

pytestmark = pytest.mark.integration
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
_FIXTURES = (conclusion_env, decision_env, phase2_database_url, revision_env)

# Independently pinned inventory; no owning writer or immutable target locks added.
INVENTORY = tuple(
    sorted(
        {
            "actors",
            "actor_subject_bindings",
            "project_memberships",
            "project_membership_events",
            "project_role_assignments",
            "projects",
            "audit_findings",
            "impact_assessments",
            "impact_targets",
            "correction_records",
            "literature_evidence",
            "literature_evidence_review_events",
            "source_versions",
            "literature_sources",
            "literature_source_project_links",
            "scientific_conclusions",
            "claims",
            "artifacts",
            "artifact_versions",
            "datasets",
            "metric_definitions",
            "metric_definition_versions",
            "experiment_specs",
            "experiment_spec_versions",
            "runs",
            "internal_review_records",
        }
    )
)


def test_write_and_uuid_replay_first_statement_exact_inventory_and_no_scientific_row_lock(
    revision_env,
):
    service, cmd, env, _, _ = revision_env
    base = env[-1]
    statements = []

    def capture(conn, cursor, statement, parameters, context, many):
        statements.append(statement)

    assert REVISION_SNAPSHOT_TABLES == INVENTORY
    event.listen(base[8], "before_cursor_execute", capture)
    try:
        saved = service.record_revision_action(base[3], cmd)
        first = "LOCK TABLE " + ",".join(INVENTORY) + " IN SHARE MODE"
        assert statements[0] == first
        assert all("FOR UPDATE" not in sql for sql in statements)
        assert any("review_issues" in sql and "FOR SHARE" in sql for sql in statements)
        statements.clear()
        assert service.record_revision_action(base[3], cmd) == saved
        assert statements[0] == first
        assert all("FOR UPDATE" not in sql or "revision_actions" in sql for sql in statements)
    finally:
        event.remove(base[8], "before_cursor_execute", capture)


def test_exact_read_does_not_block_unrelated_insert_and_keeps_one_readonly_snapshot(revision_env):
    service, cmd, env, _, _ = revision_env
    base = env[-1]
    saved = service.record_revision_action(base[3], cmd)
    entered, release = Event(), Event()
    inserted = uuid4()
    observation = {}
    statements = []

    def pause(conn, cursor, statement, parameters, context, many):
        # Capture only reader; unrelated writer uses another connection.
        if "SELECT a.* FROM revision_actions" in statement:
            observation["isolation"] = conn.execute(text("SHOW transaction_isolation")).scalar_one()
            observation["readonly"] = conn.execute(text("SHOW transaction_read_only")).scalar_one()
            observation["pid"] = conn.execute(text("SELECT pg_backend_pid()")).scalar_one()
            entered.set()
            assert release.wait(10)
            observation["visible"] = conn.execute(
                text("SELECT count(*) FROM actors WHERE id=:id"), {"id": inserted}
            ).scalar_one()
        if conn.info.get("b06_read_test"):
            statements.append(statement)

    def mark(conn, cursor, statement, parameters, context, many):
        if not entered.is_set():
            conn.info["b06_read_test"] = True

    event.listen(base[8], "before_cursor_execute", mark)
    event.listen(base[8], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(service.read_revision_action, base[3], base[5], cmd.id)
            assert entered.wait(10)
            with base[8].begin() as writer:
                writer.info.pop("b06_read_test", None)
                writer.execute(
                    text(
                        "INSERT INTO actors (id,actor_type,display_name,created_at) "
                        "VALUES (:id,'HUMAN','TEST ONLY unrelated',clock_timestamp())"
                    ),
                    {"id": inserted},
                )
            assert not pending.done()
            release.set()
            assert pending.result(timeout=10) == saved
        assert observation["isolation"] == "repeatable read" and observation["readonly"] == "on"
        assert observation["visible"] == 0
        assert not any(
            "LOCK TABLE" in sql or "FOR UPDATE" in sql or "FOR SHARE" in sql or "pg_advisory" in sql
            for sql in statements
        )
        with base[8].connect() as conn:
            assert (
                conn.execute(
                    text("SELECT count(*) FROM actors WHERE id=:id"), {"id": inserted}
                ).scalar_one()
                == 1
            )
    finally:
        release.set()
        event.remove(base[8], "before_cursor_execute", mark)
        event.remove(base[8], "after_cursor_execute", pause)


def test_first_inventory_wait_rechecks_expired_credentials_and_uses_bounded_profile(revision_env):
    service, cmd, env, _, _ = revision_env
    base = env[-1]
    with ThreadPoolExecutor(max_workers=1) as pool:
        with base[8].begin() as holder:
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            holder.execute(text("LOCK TABLE projects IN ROW EXCLUSIVE MODE"))
            pending = pool.submit(service.record_revision_action, base[3], cmd)
            witness = _wait_for_pg_blocker(base[8], pid, "relation")
            assert witness["query"].startswith("LOCK TABLE ")
            base[-1].enabled = False
        with pytest.raises(ResearchBaseError) as caught:
            pending.result(timeout=10)
        assert caught.value.code == ErrorCode.FORBIDDEN
    # Original pooled settings are restored for subsequent owning commands.
    with base[8].connect() as conn:
        assert conn.execute(text("SHOW lock_timeout")).scalar_one() == "0"
        assert conn.execute(text("SHOW statement_timeout")).scalar_one() == "0"


def test_claim_source_witness_commits_during_inventory(
    revision_env,
):
    """A positive immutable witness linearizes after append; B needs no extra table."""
    from dataclasses import replace
    from uuid import UUID

    from researchbase.application.internal_review import ReviewIssueRequest
    from tests.integration.phase2.test_b06_revision_action import _claim_successor, _source_response

    service, _, env, _, _ = revision_env
    base = env[-1]
    source_request = _source_response(env, "claim", "CORRECTED")
    claim = _claim_successor(base)
    review = env[1].create(
        base[4],
        base[5],
        "CLAIM_VERSION",
        claim,
        "SCIENTIFIC",
        "MAJOR_REVISION",
        "TEST ONLY review before sidecar",
        (ReviewIssueRequest("MAJOR", "OTHER", "TEST ONLY"),),
        uuid4(),
    )
    request = replace(source_request, id=uuid4(), review_issue_id=review.issues[0].id)
    with base[8].connect() as conn:
        evidence = conn.execute(
            text("SELECT id FROM literature_evidence WHERE source_version_id=:id"), {"id": base[7]}
        ).scalar_one()
    entered, release = Event(), Event()

    def pause(conn, cursor, statement, parameters, context, many):
        if statement.startswith("LOCK TABLE "):
            entered.set()
            assert release.wait(10)

    event.listen(base[8], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(service.record_revision_action, base[3], request)
            assert entered.wait(10)
            snapshot = base[2].snapshot(
                base[3],
                base[5],
                "ClaimVersion",
                claim,
                [
                    {
                        "evidence_id": str(evidence),
                        "relation_type": "QUALIFIES",
                        "qualification": "TEST ONLY exact source",
                    }
                ],
                uuid4(),
            )
            assert UUID(snapshot["id"])
            assert not pending.done()
            release.set()
            saved = pending.result(timeout=10)
        assert saved.result_source_version_id == request.result_source_version_id
        assert service.read_revision_action(base[3], base[5], saved.id) == saved
    finally:
        release.set()
        event.remove(base[8], "after_cursor_execute", pause)


@pytest.mark.parametrize("writer_kind", ["source", "evidence"])
@pytest.mark.parametrize("order", ["action_first", "writer_first"])
def test_owning_source_and_evidence_writers_have_observed_commit_orders(
    revision_env, writer_kind, order
):
    from uuid import UUID

    from researchbase.application.source_version import (
        CreateSourceVersion,
        SourceVersionService,
        TransitionSourceVersion,
    )
    from researchbase.domain.source_version import (
        FrozenSourceReference,
        SourceVersionKind,
        SourceVersionMaterial,
    )
    from tests.integration.phase2.test_b06_revision_action import _source_response

    service, _, env, _, _ = revision_env
    base = env[-1]
    request = _source_response(env, "conclusion", "CORRECTED")
    with base[1]() as uow:
        source = uow.source_version.version(request.result_source_version_id)
    with base[8].connect() as conn:
        evidence = conn.execute(
            text("SELECT id FROM literature_evidence WHERE source_version_id=:id"), {"id": base[7]}
        ).scalar_one()
    sources = SourceVersionService(base[1], base[-1])
    material = SourceVersionMaterial(
        source["literature_source_id"],
        SourceVersionKind.CORRECTED,
        FrozenSourceReference(source["id"], source["content_hash"]),
        FrozenSourceReference(
            source["correction_basis_artifact_version_id"],
            str(base[2]._store.put_verified(b"TEST ONLY source correction")).removeprefix(
                "sha256:"
            ),
        ),
        "TEST ONLY later correction",
        None,
        (),
        None,
        None,
        None,
        None,
        None,
    )
    draft = (
        sources.create(CreateSourceVersion(base[3], base[5], material, uuid4()))
        if writer_kind == "source"
        else None
    )

    def owning_writer():
        if writer_kind == "source":
            assert draft is not None
            return sources.freeze(
                TransitionSourceVersion(
                    base[3], base[5], UUID(str(draft["source_version_id"])), uuid4()
                )
            )
        return base[2].review(
            base[4], base[5], evidence, "DISPUTED", "TEST ONLY later dispute", uuid4()
        )

    entered, release = Event(), Event()
    holder_pid = []

    def pause(conn, cursor, statement, parameters, context, many):
        normalized = statement.strip().upper()
        match = (
            normalized.startswith("INSERT INTO REVISION_ACTIONS")
            if order == "action_first"
            else (
                normalized.startswith("UPDATE SOURCE_VERSIONS SET STATUS='SUPERSEDED'")
                if writer_kind == "source"
                else normalized.startswith("INSERT INTO LITERATURE_EVIDENCE_REVIEW_EVENTS")
            )
        )
        if match:
            holder_pid.append(conn.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(10)

    event.listen(base[8], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = (
                pool.submit(service.record_revision_action, base[3], request)
                if order == "action_first"
                else pool.submit(owning_writer)
            )
            assert entered.wait(10)
            second = (
                pool.submit(owning_writer)
                if order == "action_first"
                else pool.submit(service.record_revision_action, base[3], request)
            )
            # Concrete result FKs hold PostgreSQL's implicit KEY SHARE. The
            # source owner requests UPDATE on that row; no explicit B06 row lock.
            lock_kind = (
                "transactionid"
                if writer_kind == "source" and order == "action_first"
                else "relation"
            )
            witness = _wait_for_pg_blocker(base[8], holder_pid[0], lock_kind)
            assert witness["pid"] != holder_pid[0]
            release.set()
            first.result(timeout=10)
            if writer_kind == "source" and order == "writer_first":
                with pytest.raises(ResearchBaseError) as caught:
                    second.result(timeout=10)
                assert caught.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
            else:
                second.result(timeout=10)
    finally:
        release.set()
        event.remove(base[8], "after_cursor_execute", pause)


def test_scheduled_role_expiry_during_first_inventory_wait(revision_env):
    service, cmd, env, _, _ = revision_env
    base = env[-1]
    actor = env[2]
    with base[8].begin() as conn:
        role, until = conn.execute(
            text("""UPDATE project_role_assignments SET
          effective_until=clock_timestamp()+interval '3 seconds',row_version=row_version+1
          WHERE actor_id=:actor AND project_id=:project AND role='OWNER' AND effective_until IS NULL
          RETURNING id,effective_until"""),
            {"actor": actor.actor_id, "project": base[5]},
        ).one()
        conn.execute(
            text("""INSERT INTO project_role_events
          (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id)
          VALUES (:id,:role,:actor,'CLOSED',:until,'TEST ONLY expiry',:request)"""),
            {
                "id": uuid4(),
                "role": role,
                "actor": actor.actor_id,
                "until": until,
                "request": uuid4(),
            },
        )
    with ThreadPoolExecutor(max_workers=1) as pool:
        with base[8].begin() as holder:
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            holder.execute(text("LOCK TABLE projects IN ROW EXCLUSIVE MODE"))
            pending = pool.submit(service.record_revision_action, actor, cmd)
            before = _wait_for_pg_blocker(base[8], pid, "relation")
            assert before["observed_at"] < until and before["query"].startswith("LOCK TABLE ")
            holder.execute(
                text(
                    "SELECT pg_sleep(GREATEST(0,"
                    "EXTRACT(EPOCH FROM (:until-clock_timestamp()))+0.1))"
                ),
                {"until": until},
            )
            after = _wait_for_pg_blocker(base[8], pid, "relation")
            assert after["pid"] == before["pid"] and after["observed_at"] >= until
        with pytest.raises(ResearchBaseError) as caught:
            pending.result(timeout=10)
        assert caught.value.code == ErrorCode.FORBIDDEN
