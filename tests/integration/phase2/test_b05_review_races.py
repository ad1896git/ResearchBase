"""Observed PostgreSQL blocking and lock-free exact review snapshots."""

# ruff: noqa: E501
from concurrent.futures import ThreadPoolExecutor
from threading import Event, current_thread
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.internal_review_repository import SqlAlchemyInternalReviewRepository
from tests.integration.phase2.test_b04_manuscript_migration import (
    normal_sql_role as _normal_sql_role,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    b04_env as _b04_env,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    b05_env as _b05_env,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    collect,
    create,
    seal,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    conclusion_env as _conclusion_env,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    phase2_database_url as _phase2_database_url,
)
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

b04_env = _b04_env
b05_env = _b05_env
conclusion_env = _conclusion_env
phase2_database_url = _phase2_database_url
normal_sql_role = _normal_sql_role

pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


def insert_sql(conn, kind, template):
    if kind == "issue":
        conn.execute(
            text("""INSERT INTO review_issues(id,review_record_id,severity,issue_type,description,status,created_at,ordinal)
            VALUES (:id,:review,'BLOCKING','OTHER','Later blocker','OPEN',clock_timestamp(),0)"""),
            {"id": uuid4(), "review": template.id},
        )
    else:
        conn.execute(
            text("""INSERT INTO internal_review_records
          SELECT :id,project_id,manuscript_version_id,claim_version_id,scientific_conclusion_version_id,artifact_version_id,
            target_content_hash,reviewer_actor_id,review_type,recommendation,summary,clock_timestamp(),content_hash,hash_scheme
          FROM internal_review_records WHERE id=:review"""),
            {"id": uuid4(), "review": template.id},
        )


@pytest.mark.parametrize("kind", ["review", "issue", "application"])
@pytest.mark.parametrize("first", ["basis", "writer"])
def test_review_and_issue_phantoms_serialized(b05_env, normal_sql_role, kind, first):
    env = b05_env
    seal(env)
    template = create(env)
    engine = env[5]
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="b05-writer") as pool:
        if first == "basis":
            with env[4]() as holder:
                holder.internal_review.prepare_write()
                old = env[0].collect_manuscript_review_basis(
                    holder, env[1].project_id, env[1].manuscript_version_id
                )
                pid = holder._session.execute(text("SELECT pg_backend_pid()")).scalar_one()

                def write():
                    if kind == "application":
                        return create(env)
                    with engine.begin() as conn:
                        conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
                        insert_sql(conn, kind, template)

                future = pool.submit(write)
                _wait_for_pg_blocker(engine, pid, "transactionid")
                assert len(old.reviews) == 1 and old.gate_satisfied
                holder.commit()
            future.result(timeout=15)
        else:
            # Normal SQL writers do not acquire the Application table inventory.
            with engine.connect() as conn:
                tx = conn.begin()
                conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
                insert_sql(conn, "review" if kind == "application" else kind, template)
                pid = conn.execute(text("SELECT pg_backend_pid()")).scalar_one()
                future = pool.submit(collect, env)
                _wait_for_pg_blocker(engine, pid, "transactionid")
                tx.commit()
                new = future.result(timeout=15)
                assert len(new.reviews) == (1 if kind == "issue" else 2)
                assert new.gate_satisfied == (kind != "issue")
    latest = collect(env)
    assert len(latest.reviews) == (1 if kind == "issue" else 2)
    assert latest.gate_satisfied == (kind != "issue")


def test_concurrent_identical_requests(b05_env):
    seal(b05_env)
    request = uuid4()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: create(b05_env, request=request), range(2)))
    assert results[0] == results[1]
    assert len(collect(b05_env).reviews) == 1


@pytest.mark.parametrize("target_kind", ["MANUSCRIPT_VERSION", "CLAIM_VERSION"])
def test_exact_read_snapshot_does_not_block_insert(b05_env, monkeypatch, target_kind):
    env = b05_env
    seal(env)
    if target_kind == "MANUSCRIPT_VERSION":
        result = create(env)
    else:
        result = env[0].create(
            env[3],
            env[1].project_id,
            target_kind,
            env[8],
            "SCIENTIFIC",
            "ACCEPT",
            "Claim review",
            (),
            uuid4(),
        )
    entered, release = Event(), Event()
    original = SqlAlchemyInternalReviewRepository.authority
    phantom = uuid4()

    def authority(self, *args):
        rows = original(self, *args)
        if current_thread().name.startswith("b05-reader") and not entered.is_set():
            assert (
                self._session.execute(text("SHOW transaction_isolation")).scalar_one()
                == "repeatable read"
            )
            assert self._session.execute(text("SHOW transaction_read_only")).scalar_one() == "on"
            assert (
                self._session.execute(
                    text(
                        "SELECT mode FROM pg_locks WHERE pid=pg_backend_pid() AND (locktype='advisory' OR mode IN ('ShareLock','RowShareLock','RowExclusiveLock'))"
                    )
                ).all()
                == []
            )
            entered.set()
            assert release.wait(15)
            assert (
                self._session.execute(
                    text("SELECT count(*) FROM actors WHERE id=:id"), {"id": phantom}
                ).scalar_one()
                == 0
            )
        return rows

    monkeypatch.setattr(SqlAlchemyInternalReviewRepository, "authority", authority)
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="b05-reader") as pool:
        future = pool.submit(env[0].read, env[3], env[1].project_id, result.id)
        try:
            assert entered.wait(10)
            with env[5].begin() as conn:
                conn.execute(text("SET LOCAL lock_timeout='2s'"))
                conn.execute(
                    text(
                        "INSERT INTO actors(id,actor_type,display_name,created_at,row_version) VALUES (:id,'HUMAN','Snapshot witness',clock_timestamp(),1)"
                    ),
                    {"id": phantom},
                )
        finally:
            release.set()
        assert future.result(timeout=15) == result


@pytest.mark.parametrize("expire", [False, True])
def test_first_share_timeout_and_post_wait_credentials(b05_env, monkeypatch, expire):
    env = b05_env
    seal(env)
    valid = [True]
    original = env[9].is_valid
    monkeypatch.setattr(
        env[9], "is_valid", lambda principal, at: valid[0] and original(principal, at)
    )
    with env[5].connect() as conn:
        tx = conn.begin()
        conn.execute(text("LOCK TABLE actors IN ROW EXCLUSIVE MODE"))
        pid = conn.execute(text("SELECT pg_backend_pid()")).scalar_one()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(create, env)
            _wait_for_pg_blocker(env[5], pid, "relation")
            if expire:
                valid[0] = False
                tx.commit()
            with pytest.raises(ResearchBaseError) as exc:
                future.result(timeout=15)
            assert exc.value.code == (
                ErrorCode.FORBIDDEN if expire else ErrorCode.CONCURRENT_MODIFICATION
            )
        if tx.is_active:
            tx.rollback()
    with env[5].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM internal_review_records")).scalar_one() == 0


@pytest.mark.parametrize("protocol", ["b04", "decision", "novelty_coverage", "novelty_claim"])
def test_mixed_existing_protocols_with_protected_verifier(b05_env, monkeypatch, protocol):
    from researchbase.application.manuscript_freeze import FreezeManuscriptCommand
    from researchbase.application.scientific_conclusion import ClaimInputRequest
    from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE

    env = b05_env
    # An exact Conclusion for the preexisting Decision repository protocol.
    base = env[10]
    conclusion = base[0].create(
        env[2],
        env[1].project_id,
        "Mixed protocol",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(env[8], "SUPPORTS"),),
        (),
        uuid4(),
    )
    base[0].freeze(
        env[2], env[1].project_id, conclusion.conclusion_id, conclusion.version_id, uuid4()
    )
    sealed = seal(env)
    entered, release = Event(), Event()
    original = env[7].verify
    holder_pid = []
    authority = SqlAlchemyInternalReviewRepository.authority

    def checked_authority(self, *args):
        rows = authority(self, *args)
        if current_thread().name.startswith("b05-mixed"):
            holder_pid.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
        return rows

    def verify(identity):
        if current_thread().name.startswith("b05-mixed") and not entered.is_set():
            entered.set()
            assert release.wait(10)
        return original(identity)

    monkeypatch.setattr(SqlAlchemyInternalReviewRepository, "authority", checked_authority)
    monkeypatch.setattr(env[7], "verify", verify)

    def owner_probe():
        if protocol == "b04":
            return env[6].freeze_manuscript_version(
                env[2],
                FreezeManuscriptCommand(
                    env[1].project_id,
                    env[1].publication_id,
                    env[1].manuscript_version_id,
                    sealed.placement_set_hash,
                    sealed.content_hash,
                ),
            )
        with env[4]() as uow:
            if protocol == "decision":
                uow.decision.lock_request(uuid4())
                assert uow.decision.target(conclusion.version_id, env[1].project_id)
                uow.decision.lock_snapshot()
            else:
                uow.novelty.prepare(
                    "coverage" if protocol == "novelty_coverage" else "assessment",
                    uuid4(),
                    env[8] if protocol == "novelty_claim" else None,
                )
            uow.literature_search_plan.lock_project(env[1].project_id)
            uow.commit()

    with (
        ThreadPoolExecutor(max_workers=1, thread_name_prefix="b05-mixed") as reviewing,
        ThreadPoolExecutor(max_workers=1) as owning,
    ):
        review = reviewing.submit(create, env)
        try:
            assert entered.wait(10) and holder_pid
            owner = owning.submit(owner_probe)
            _wait_for_pg_blocker(env[5], holder_pid[0], "advisory")
        finally:
            release.set()
        result = review.result(timeout=15)
        owner.result(timeout=15)
    assert env[0].read(env[3], env[1].project_id, result.id) == result


@pytest.mark.parametrize("owner", ["impact", "finding", "source_retraction", "evidence_dispute"])
def test_mutable_closure_and_insert_phantoms(b05_env, owner):
    from dataclasses import replace
    from time import monotonic
    from uuid import UUID

    from researchbase.application.governance import (
        CreateAuditFindingCommand,
        CreateImpactAssessmentCommand,
        GovernanceService,
        ProposedImpactTarget,
    )
    from researchbase.application.manuscript_placement import (
        CitationPlacementService,
        ClaimPlacementService,
    )
    from researchbase.application.scientific_conclusion import LiteratureInputRequest
    from researchbase.application.source_version import (
        CreateSourceVersion,
        SourceVersionService,
        TransitionSourceVersion,
        _material_from_row,
    )
    from researchbase.domain.source_version import FrozenSourceReference, SourceVersionKind
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock
    from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE

    env = b05_env
    q = env[1]
    base = env[10]
    ClaimPlacementService(env[4], env[9]).add(
        env[2],
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        env[8],
        None,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "p1"},
        "SUPPORTED",
        0,
        uuid4(),
    )
    CitationPlacementService(env[4], env[9]).add(
        env[2],
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        base[7],
        "INTRO",
        {"kind": "PARAGRAPH", "value": "p1"},
        "BACKGROUND",
        0,
        uuid4(),
    )
    evidence = None
    if owner == "evidence_dispute":
        evidence = UUID(
            base[2].create(env[2], q.project_id, base[7], "improved recall", uuid4())["id"]
        )
        base[2].review(env[3], q.project_id, evidence, "VERIFIED", "Independent", uuid4())
        conclusion = base[0].create(
            env[2],
            q.project_id,
            "Reviewed conclusion",
            SCOPE,
            "MODERATE",
            None,
            (),
            (LiteratureInputRequest(evidence, "SUPPORTS"),),
            uuid4(),
        )
        base[0].freeze(
            env[2], q.project_id, conclusion.conclusion_id, conclusion.version_id, uuid4()
        )
        ClaimPlacementService(env[4], env[9]).add(
            env[2],
            q.project_id,
            q.publication_id,
            q.manuscript_version_id,
            None,
            conclusion.version_id,
            "DISCUSSION",
            {"kind": "PARAGRAPH", "value": "p1"},
            "SUPPORTED",
            0,
            uuid4(),
        )
    seal(env)
    saved = create(env)

    def writer():
        context = ExecutionContext(actor_id=env[2].actor_id, request_id=uuid4(), client_type="test")
        governance = GovernanceService(env[4], SystemClock())
        if owner == "impact":
            return governance.create_impact_assessment(
                CreateImpactAssessmentCommand(
                    q.project_id,
                    None,
                    {"test": "invalid"},
                    "invalid",
                    (ProposedImpactTarget("claim_version", env[8], "invalid"),),
                    context,
                )
            )
        if owner == "finding":
            return governance.create_audit_finding(
                CreateAuditFindingCommand(
                    q.project_id,
                    "test",
                    "major",
                    "Test finding",
                    "Phantom finding",
                    "claim_version",
                    env[8],
                    context,
                )
            )
        if owner == "evidence_dispute":
            return base[2].review(
                env[3], q.project_id, evidence, "DISPUTED", "Later dispute", uuid4()
            )
        with env[4]() as uow:
            row = uow.source_version.version(base[7])
            material = _material_from_row(uow.source_version, row)
        material = replace(
            material,
            version_kind=SourceVersionKind.RETRACTED,
            predecessor_source_version=FrozenSourceReference(base[7], row["content_hash"]),
            correction_basis_artifact=material.fulltext_artifact,
        )
        versions = SourceVersionService(env[4], env[9])
        created = versions.create(CreateSourceVersion(env[2], q.project_id, material, uuid4()))
        return versions.freeze(
            TransitionSourceVersion(
                env[2], q.project_id, UUID(str(created["source_version_id"])), uuid4()
            )
        )

    with env[4]() as holder, ThreadPoolExecutor(max_workers=1) as pool:
        holder.internal_review.prepare_write()
        old = env[0].collect_manuscript_review_basis(holder, q.project_id, q.manuscript_version_id)
        pid = holder._session.execute(text("SELECT pg_backend_pid()")).scalar_one()
        writing = pool.submit(writer)
        try:
            deadline = monotonic() + 5
            witnessed = False
            while monotonic() < deadline:
                if writing.done():
                    writing.result()
                with env[5].connect() as conn:
                    witnessed = bool(
                        conn.execute(
                            text(
                                "SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE :pid=ANY(pg_blocking_pids(pid)))"
                            ),
                            {"pid": pid},
                        ).scalar_one()
                    )
                if witnessed:
                    break
            assert witnessed and old.gate_satisfied
        finally:
            holder.commit()
        writing.result(timeout=15)
    assert env[0].read(env[3], q.project_id, saved.id) == saved
    if owner == "finding":
        assert collect(env).gate_satisfied
    else:
        with pytest.raises(ResearchBaseError) as exc:
            collect(env)
        assert exc.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_real_deadlock_aborts_attempt_and_preserves_one_review(b05_env, monkeypatch):
    from sqlalchemy.exc import DBAPIError

    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    env = b05_env
    seal(env)
    states = []
    original = SqlAlchemyUnitOfWork._command_database_error

    def normalize(self, exc):
        state = getattr(exc.orig, "sqlstate", None)
        if state == "40P01":
            states.append(state)
        return original(self, exc)

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "_command_database_error", normalize)
    with env[5].connect() as owner, ThreadPoolExecutor(max_workers=1) as pool:
        transaction = owner.begin()
        owner.execute(text("SET LOCAL deadlock_timeout='100ms'"))
        owner.execute(text("SET LOCAL lock_timeout='5s'"))
        owner.execute(
            text("SELECT id FROM manuscript_versions WHERE id=:id FOR UPDATE"),
            {"id": env[1].manuscript_version_id},
        )
        pid = owner.execute(text("SELECT pg_backend_pid()")).scalar_one()
        future = pool.submit(create, env)
        _wait_for_pg_blocker(env[5], pid, "transactionid")
        # Opposing owner order forms a real cycle with B05's SHARE-first order.
        try:
            owner.execute(text("LOCK TABLE source_versions IN ROW EXCLUSIVE MODE"))
            transaction.commit()
        except DBAPIError as exc:
            assert getattr(exc.orig, "sqlstate", None) == "40P01"
            states.append("40P01")
            transaction.rollback()
        result = future.result(timeout=15)
    assert states and len(collect(env).reviews) == 1
    assert env[0].read(env[3], env[1].project_id, result.id) == result
