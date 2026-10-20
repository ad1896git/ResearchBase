"""Offline candidate failure boundaries with committed-state observations."""

import json
from dataclasses import replace
from hashlib import sha256
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from researchbase.application.native_research_strategy import (
    NativeResearchStrategy,
    ResearchStrategyContext,
    ResearchStrategyRequest,
)
from researchbase.application.scientific_rag_provider import (
    FakeScientificRAGCapability,
    SourceLocator,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b02_support import b02_env as _b02_env
from tests.integration.phase2.b02_support import capture, hcommand, qcommand, restart
from tests.integration.phase2.b30_observations import (
    assert_first_share,
    assert_snapshot_read,
    sql_protocol,
)
from tests.integration.phase2.pr2_19_support import (
    CORPUS,
    StateDelta,
    counts,
)
from tests.integration.phase2.pr2_19_support import (
    m3 as _m3,
)
from tests.integration.phase2.pr2_19_support import (
    phase2_database_url as _phase2_database_url,
)
from tests.integration.phase2.pr2_19_support import (
    pr219_candidate_env as _pr219_candidate_env,
)
from tests.integration.phase2.pr2_19_support import (
    pr219_evidence_env as _pr219_evidence_env,
)
from tests.unit.phase2.test_pr2_07_scientific_rag_boundary import context, request, response
from tests.unit.phase2.test_pr2_08_native_strategy import ScriptedRAG

pytestmark = pytest.mark.integration


def test_native_strategy_is_candidate_only(pr219_candidate_env):
    env, sources = pr219_candidate_env
    before = counts(env[7])
    strategy = NativeResearchStrategy()
    req = ResearchStrategyRequest("Recall", sources)
    ctx = ResearchStrategyContext(req, lambda: False)
    result = strategy.execute(strategy.prepare_plan(req, ctx), ScriptedRAG(sources[0]), ctx)
    assert result.execution_metadata.query_count == 3
    assert "UNVERIFIED_CANDIDATE" in result.warnings
    assert result.hypothesis_candidates == ()
    assert all(item.source_version_id in sources for item in result.literature_evidence_candidates)
    assert counts(env[7]) == before


@pytest.mark.parametrize(
    "case", ["invented", "out_of_corpus", "absent_paragraph", "substituted_quotation", "valid"]
)
def test_candidate_exact_corpus_and_zero_scientific_delta(pr219_candidate_env, case):
    env, sources = pr219_candidate_env
    service, author, _, project, *_ = env
    before = counts(env[7])
    source = (
        uuid4() if case == "invented" else sources[1] if case == "out_of_corpus" else sources[0]
    )
    candidate = response(
        source,
        locator=SourceLocator(paragraph="99" if case == "absent_paragraph" else "1"),
        excerpt="Fabricated precision" if case == "substituted_quotation" else "improved recall",
    )
    fake = FakeScientificRAGCapability(candidate)
    if case in {"invented", "out_of_corpus"}:
        with pytest.raises(ValueError, match="source"):
            fake.answer(request((sources[0],)), context())
    else:
        result = fake.answer(request(sources), context())
        assert not any(hasattr(fake, name) for name in ("engine", "session", "_factory"))
        item = result.evidence_candidates[0]
        assert item.locator.paragraph is not None
        if case == "valid":
            assert item.excerpt.encode() in CORPUS[0].split(b"\n\n")[0]
        else:
            with pytest.raises(ResearchBaseError) as denied:
                service.create(
                    author,
                    project,
                    item.source_version_id,
                    item.excerpt,
                    uuid4(),
                    paragraph=int(item.locator.paragraph),
                )
            assert denied.value.code is ErrorCode.VALIDATION_ERROR
    assert counts(env[7]) == before
    assert before["literature_evidence"] == 0


# Register imported fixtures explicitly, matching the existing Phase 2 layout.
m3 = _m3
phase2_database_url = _phase2_database_url
pr219_candidate_env = _pr219_candidate_env
pr219_evidence_env = _pr219_evidence_env


b02_env = _b02_env

# Exact lexical inventory from S3 §12.2, independent of production's S constant.
G2_SHARE = (
    "LOCK TABLE "
    + ",".join(
        (
            "actor_subject_bindings",
            "actors",
            "artifact_versions",
            "artifacts",
            "hypotheses",
            "hypothesis_versions",
            "literature_source_project_links",
            "literature_sources",
            "project_membership_events",
            "project_memberships",
            "project_role_assignments",
            "projects",
            "research_question_versions",
            "research_questions",
            "source_versions",
            "strategy_candidate_captures",
            "strategy_candidate_sources",
            "strategy_hypothesis_admissions",
            "strategy_question_admissions",
        )
    )
    + " IN SHARE MODE"
)


@pytest.mark.parametrize("linked_question", [True, False])
def test_g2_saved_native_brief_question_and_researcher_adaptation_after_restart(
    b02_env,
    linked_question,
    monkeypatch,
):
    """B02 literals and DRAFT organizational parent, per director reconciliation."""
    from researchbase.application.strategy_candidate_promotion import ExactStrategyQuery

    e = b02_env
    service, principal, project = e["service"], e["principal"], e["project"]
    with e["factory"]() as uow:
        engine = uow._require_session().get_bind()
    active = set()

    def begin(conn):
        active.add(conn)

    def end(conn):
        active.discard(conn)

    answer, put = e["rag"].answer, e["store"].put_verified

    def checked_answer(*args, **kwargs):
        assert not active, "strategy compute holds a database transaction"
        return answer(*args, **kwargs)

    def checked_put(*args, **kwargs):
        assert not active, "CAS write holds a database transaction"
        return put(*args, **kwargs)

    monkeypatch.setattr(e["rag"], "answer", checked_answer)
    monkeypatch.setattr(e["store"], "put_verified", checked_put)
    for name, callback in (("begin", begin), ("commit", end), ("rollback", end)):
        event.listen(engine, name, callback)
    before = counts(e["engine"])
    try:
        with sql_protocol(engine) as sql:
            saved = capture(e)
        assert_first_share(sql, G2_SHARE)
        assert [
            (statement, params)
            for tx in sql.transactions
            for (statement, _, _), params in zip(tx.statements, tx.parameters, strict=True)
            if "advisory" in statement
        ] == [
            (
                "SELECT pg_advisory_xact_lock(hashtextextended(%(key)s,0))",
                {"key": f"b02:capture:{saved.id}"},
            )
        ]
        assert not active
    finally:
        for name, callback in (("begin", begin), ("commit", end), ("rollback", end)):
            event.remove(engine, name, callback)
    after = counts(e["engine"])
    changes = {
        "artifacts": 1,
        "artifact_versions": 1,
        "strategy_candidate_captures": 1,
        "strategy_candidate_sources": len(e["sources"]),
    }
    assert tuple(StateDelta(t, before[t], after[t]) for t in before) == tuple(
        StateDelta(t, n, n + changes.get(t, 0)) for t, n in before.items()
    )
    data = e["store"].open("sha256:" + saved.artifact_content_hash)
    assert sha256(data).hexdigest() == saved.artifact_content_hash
    payload = json.loads(data)
    assert payload["result"]["hypothesis_candidates"] == []
    assert payload["request"]["source_version_ids"] == [
        str(v) for v in sorted(e["sources"], key=str)
    ]
    # Exhaustive B02 §5.2 material; no production hash builder supplies the oracle.
    from researchbase.foundation.time import format_utc
    from tests.unit.phase2.test_b02_strategy_promotion_hashes import digest

    assert saved.content_hash == digest(
        dict(
            type="StrategyCandidateCapture",
            material_version=1,
            id=str(saved.id),
            project_id=str(project),
            artifact_version_id=str(saved.artifact_version_id),
            artifact_content_hash=saved.artifact_content_hash,
            topic=saved.topic,
            source_version_ids=[str(v) for v in sorted(e["sources"], key=str)],
            max_evidence_candidates=saved.max_evidence_candidates,
            strategy_id=saved.strategy_id,
            strategy_version=saved.strategy_version,
            captured_by=str(saved.captured_by),
            captured_at=format_utc(saved.captured_at),
        )
    )
    before = after
    with sql_protocol(engine) as sql:
        question = service.promote_strategy_question(e["other"], qcommand(e, saved))
    assert_first_share(sql, G2_SHARE)
    assert [
        (statement, params)
        for tx in sql.transactions
        for (statement, _, _), params in zip(tx.statements, tx.parameters, strict=True)
        if "advisory" in statement
    ] == [
        (
            "SELECT pg_advisory_xact_lock(hashtextextended(%(key)s,0))",
            {"key": f"b02:question:{question.id}"},
        )
    ]
    after = counts(e["engine"])
    changes = {
        "research_questions": 1,
        "research_question_versions": 1,
        "strategy_question_admissions": 1,
    }
    assert tuple(StateDelta(t, before[t], after[t]) for t in before) == tuple(
        StateDelta(t, n, n + changes.get(t, 0)) for t, n in before.items()
    )
    before = after
    cmd = hcommand(
        e, saved, research_question_id=(question.research_question_id if linked_question else None)
    )
    with sql_protocol(engine) as sql:
        adapted = service.promote_strategy_hypothesis(principal, cmd)
    assert_first_share(sql, G2_SHARE)
    assert [
        (statement, params)
        for tx in sql.transactions
        for (statement, _, _), params in zip(tx.statements, tx.parameters, strict=True)
        if "advisory" in statement
    ] == [
        (
            "SELECT pg_advisory_xact_lock(hashtextextended(%(key)s,0))",
            {"key": f"b02:hypothesis:{adapted.id}"},
        )
    ]
    after = counts(e["engine"])
    changes = {"hypotheses": 1, "hypothesis_versions": 1, "strategy_hypothesis_admissions": 1}
    assert tuple(StateDelta(t, before[t], after[t]) for t in before) == tuple(
        StateDelta(t, n, n + changes.get(t, 0)) for t, n in before.items()
    )
    assert question.admitted_by != saved.captured_by
    assert question.content_hash == digest(
        dict(
            type="StrategyQuestionAdmission",
            material_version=1,
            id=str(question.id),
            project_id=str(project),
            capture_id=str(saved.id),
            capture_content_hash=saved.content_hash,
            candidate_index=question.candidate_index,
            candidate_text=question.candidate_text,
            question_text=question.question_text,
            rationale=question.rationale,
            research_question_id=str(question.research_question_id),
            research_question_version_id=str(question.research_question_version_id),
            admitted_by=str(question.admitted_by),
            admitted_at=format_utc(question.admitted_at),
        )
    )
    assert adapted.content_hash == digest(
        dict(
            type="StrategyHypothesisAdmission",
            material_version=1,
            id=str(adapted.id),
            project_id=str(project),
            capture_id=str(saved.id),
            capture_content_hash=saved.content_hash,
            candidate_index=adapted.candidate_index,
            candidate_text=adapted.candidate_text,
            statement=adapted.statement,
            rationale=adapted.rationale,
            research_question_id=str(cmd.research_question_id) if linked_question else None,
            hypothesis_id=str(adapted.hypothesis_id),
            hypothesis_version_id=str(adapted.hypothesis_version_id),
            admitted_by=str(adapted.admitted_by),
            admitted_at=format_utc(adapted.admitted_at),
        )
    )
    assert adapted.research_question_id == cmd.research_question_id
    assert (
        adapted.candidate_text
        == payload["result"]["research_brief_candidate"]["sections"][0]["answer_candidate"]
    )
    fresh = restart(e)
    with fresh._factory() as uow:
        from researchbase.persistence.uow import SqlAlchemyUnitOfWork

        fresh_engine = cast(SqlAlchemyUnitOfWork, uow)._require_session().get_bind()
    for method, result in (
        (fresh.get_strategy_capture, saved),
        (fresh.get_strategy_question_promotion, question),
        (fresh.get_strategy_hypothesis_promotion, adapted),
    ):
        with sql_protocol(fresh_engine) as sql:
            assert method(principal, ExactStrategyQuery(result.id, project)) == result
        assert_snapshot_read(sql, snapshots=1)
    with e["engine"].connect() as conn:
        for table, version in (
            ("research_question_versions", question.research_question_version_id),
            ("hypothesis_versions", adapted.hypothesis_version_id),
        ):
            row = (
                conn.execute(text(f"SELECT * FROM {table} WHERE id=:id"), {"id": version})
                .mappings()
                .one()
            )
            assert row["status"] == "DRAFT" and row["version_number"] == 1
            assert row["content_hash"] is row["frozen_at"] is None
    with e["factory"]() as uow:
        from researchbase.domain.research import HypothesisVersionId, ResearchQuestionVersionId

        for version in (
            uow.research_questions.get_version(
                ResearchQuestionVersionId(question.research_question_version_id)
            ),
            uow.hypotheses.get_version(HypothesisVersionId(adapted.hypothesis_version_id)),
        ):
            assert version is not None
            assert version.content_hash is version.hash_scheme is version.frozen_at is None
    assert counts(e["engine"]) == after


@pytest.mark.parametrize("kind", ["question", "hypothesis"])
def test_g2_exact_replay_and_changed_payload_zero_delta(b02_env, kind):
    e = b02_env
    saved = capture(e)
    cmd = qcommand(e, saved) if kind == "question" else hcommand(e, saved)
    name = "promote_strategy_" + kind
    result = getattr(e["service"], name)(e["principal"], cmd)
    before = counts(e["engine"])
    fresh = restart(e)
    assert getattr(fresh, name)(e["principal"], cmd) == result
    with pytest.raises(ResearchBaseError) as exc:
        getattr(fresh, name)(e["principal"], replace(cmd, rationale="Changed request"))
    assert exc.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    for actor, changed, code in (
        (e["principal"], replace(cmd, id=uuid4()), ErrorCode.DUPLICATE_CONTENT),
        (e["other"], cmd, ErrorCode.FORBIDDEN),
    ):
        with pytest.raises(ResearchBaseError) as exc:
            getattr(fresh, name)(actor, changed)
        assert exc.value.code is code
    assert counts(e["engine"]) == before


@pytest.mark.parametrize("kind,index", [("question", 999), ("hypothesis", 999), ("hypothesis", 2)])
def test_g2_invalid_selector_or_unanswered_section_zero_delta(b02_env, kind, index):
    e = b02_env
    saved = capture(e)
    cmd = (qcommand if kind == "question" else hcommand)(e, saved, candidate_index=index)
    before = counts(e["engine"])
    with pytest.raises(ResearchBaseError) as exc:
        getattr(e["service"], "promote_strategy_" + kind)(e["principal"], cmd)
    assert exc.value.code is ErrorCode.VALIDATION_ERROR
    assert counts(e["engine"]) == before


@pytest.mark.parametrize("kind", ["question", "hypothesis"])
def test_g2_cas_corruption_denies_admission_and_exact_read(b02_env, kind, monkeypatch):
    from researchbase.application.strategy_candidate_promotion import ExactStrategyQuery

    e = b02_env
    saved = capture(e)
    before = counts(e["engine"])
    original = e["store"].open

    def corrupt(key):
        return b"{}" if key.endswith(saved.artifact_content_hash) else original(key)

    monkeypatch.setattr(e["store"], "open", corrupt)
    fresh = restart(e)
    cmd = (qcommand if kind == "question" else hcommand)(e, saved)
    for action in (
        lambda: getattr(fresh, "promote_strategy_" + kind)(e["principal"], cmd),
        lambda: fresh.get_strategy_capture(
            e["principal"], ExactStrategyQuery(saved.id, e["project"])
        ),
    ):
        with pytest.raises(ResearchBaseError) as exc:
            action()
        assert exc.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert counts(e["engine"]) == before


@pytest.mark.parametrize("kind", ["question", "hypothesis"])
def test_g2_fault_after_admission_insert_rolls_back_root_and_version(b02_env, kind, monkeypatch):
    from researchbase.persistence.strategy_candidate_promotion_repository import (
        SqlAlchemyStrategyCandidatePromotionRepository,
    )

    e = b02_env
    saved = capture(e)
    before = counts(e["engine"])
    original = SqlAlchemyStrategyCandidatePromotionRepository.insert

    def fail(self, table, *args, **kwargs):
        original(self, table, *args, **kwargs)
        if table == kind:
            raise RuntimeError("S3 after admission insert")

    monkeypatch.setattr(SqlAlchemyStrategyCandidatePromotionRepository, "insert", fail)
    with pytest.raises(RuntimeError, match="S3 after admission"):
        getattr(e["service"], "promote_strategy_" + kind)(
            e["principal"], (qcommand if kind == "question" else hcommand)(e, saved)
        )
    assert counts(e["engine"]) == before


@pytest.mark.parametrize("kind", ["question", "hypothesis"])
def test_g2_creation_guard_maps_failure_and_rolls_back(b02_env, monkeypatch, kind):
    from researchbase.persistence.repositories import (
        SqlAlchemyHypothesisRepository,
        SqlAlchemyResearchQuestionRepository,
    )

    e = b02_env
    saved = capture(e)
    cls = (
        SqlAlchemyResearchQuestionRepository
        if kind == "question"
        else SqlAlchemyHypothesisRepository
    )
    original = cls.add_version

    def wrong_material(self, version):
        # Fault the new scientific material through its repository write; never forge an admission.
        original(self, replace(version, rationale="Injected material mismatch"))

    monkeypatch.setattr(cls, "add_version", wrong_material)
    before = counts(e["engine"])
    with pytest.raises(ResearchBaseError) as exc:
        getattr(e["service"], "promote_strategy_" + kind)(
            e["principal"], (qcommand if kind == "question" else hcommand)(e, saved)
        )
    assert exc.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert counts(e["engine"]) == before


@pytest.mark.parametrize("kind", ["capture", "question", "hypothesis"])
def test_g2_admission_history_is_immutable(b02_env, kind):
    from sqlalchemy.exc import DBAPIError

    e = b02_env
    saved = capture(e)
    if kind != "capture":
        getattr(e["service"], "promote_strategy_" + kind)(
            e["principal"], (qcommand if kind == "question" else hcommand)(e, saved)
        )
    table = "strategy_candidate_captures" if kind == "capture" else f"strategy_{kind}_admissions"
    before = counts(e["engine"])
    with pytest.raises(DBAPIError) as exc:
        with e["engine"].begin() as conn:
            conn.execute(text(f"UPDATE {table} SET id=id"))
    assert getattr(exc.value.orig, "sqlstate", None) == "P22B1"
    assert counts(e["engine"]) == before


@pytest.mark.parametrize("kind", ["question", "hypothesis"])
def test_g2_credentials_revoked_during_observed_share_wait(b02_env, kind):
    from concurrent.futures import ThreadPoolExecutor

    from tests.integration.phase2.test_pr2_18_concurrency import _witness

    e = b02_env
    saved = capture(e)
    cmd = (qcommand if kind == "question" else hcommand)(e, saved)
    before = counts(e["engine"])
    with ThreadPoolExecutor(1) as pool:
        with e["engine"].connect() as blocker:
            tx = blocker.begin()
            blocker.execute(text("LOCK TABLE actors IN ROW EXCLUSIVE MODE"))
            pid = blocker.execute(text("SELECT pg_backend_pid()")).scalar_one()
            future = pool.submit(
                getattr(e["service"], "promote_strategy_" + kind), e["principal"], cmd
            )
            try:
                assert _witness(e["engine"], pid) != pid
                e["credentials"].enabled = False
            finally:
                tx.rollback()
        with pytest.raises(ResearchBaseError) as exc:
            future.result(timeout=15)
    assert exc.value.code is ErrorCode.FORBIDDEN
    assert counts(e["engine"]) == before


@pytest.mark.parametrize("kind", ["question", "hypothesis"])
@pytest.mark.parametrize("during_wait", [False, True])
def test_g2_historical_replay_after_application_closes_writer_roles(b02_env, kind, during_wait):
    from researchbase.application.phase2_identity import AssignProjectRole, CloseProjectRole
    from tests.integration.phase2.test_pr2_00_challenges import _service

    e = b02_env
    saved = capture(e)
    cmd = (qcommand if kind == "question" else hcommand)(e, saved)
    method = "promote_strategy_" + kind
    result = getattr(e["service"], method)(e["principal"], cmd)
    identity, _, _ = _service(
        e["engine"].url.render_as_string(hide_password=False), credential_verifier=e["credentials"]
    )
    # Identity owns each role transition; another OWNER preserves project coverage.
    identity.assign_project_role(
        AssignProjectRole(
            e["principal"],
            e["project"],
            e["principal"].actor_id,
            "VIEWER",
            "S3 saved read",
            uuid4(),
        )
    )
    with e["engine"].connect() as conn:
        writers = (
            conn.execute(
                text(
                    "SELECT id FROM project_role_assignments WHERE "
                    "actor_id=:actor AND project_id=:project AND effective_until IS NULL "
                    "AND role IN ('OWNER','RESEARCHER')"
                ),
                {"actor": e["principal"].actor_id, "project": e["project"]},
            )
            .scalars()
            .all()
        )
    assert writers

    def close_writers():
        for role in writers:
            identity.close_project_role(
                CloseProjectRole(e["principal"], e["project"], role, "S3 close writer", uuid4())
            )

    if during_wait:
        from concurrent.futures import ThreadPoolExecutor

        from tests.integration.phase2.test_pr2_18_concurrency import _witness

        before_wait = counts(e["engine"])
        with ThreadPoolExecutor(1) as pool:
            with e["engine"].connect() as blocker:
                tx = blocker.begin()
                blocker.execute(text("LOCK TABLE actors IN ROW EXCLUSIVE MODE"))
                pid = blocker.execute(text("SELECT pg_backend_pid()")).scalar_one()
                future = pool.submit(
                    getattr(restart(e), method), e["principal"], replace(cmd, id=uuid4())
                )
                try:
                    assert _witness(e["engine"], pid) != pid
                    close_writers()
                finally:
                    tx.rollback()
            with pytest.raises(ResearchBaseError) as exc:
                future.result(timeout=15)
        assert exc.value.code is ErrorCode.FORBIDDEN
        assert counts(e["engine"]) == before_wait
    else:
        close_writers()
    before = counts(e["engine"])
    assert getattr(restart(e), method)(e["principal"], cmd) == result
    with pytest.raises(ResearchBaseError) as exc:
        getattr(restart(e), method)(e["principal"], replace(cmd, id=uuid4()))
    assert exc.value.code is ErrorCode.FORBIDDEN
    assert counts(e["engine"]) == before


@pytest.mark.parametrize("kind", ["question", "hypothesis"])
def test_g2_duplicate_loser_with_backend_wait(b02_env, monkeypatch, kind):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from researchbase.persistence.strategy_candidate_promotion_repository import (
        SqlAlchemyStrategyCandidatePromotionRepository as Repository,
    )
    from tests.integration.phase2.test_pr2_18_concurrency import _witness

    e = b02_env
    saved = capture(e)
    cmd = (qcommand if kind == "question" else hcommand)(e, saved)
    before = counts(e["engine"])
    ready, release = Event(), Event()
    pids = []
    original = Repository.insert

    def hold(repo, table, *args, **kwargs):
        original(repo, table, *args, **kwargs)
        if table == kind:
            pids.append(repo._session.connection().connection.driver_connection.info.backend_pid)
            ready.set()
            assert release.wait(10)

    monkeypatch.setattr(Repository, "insert", hold)
    method = getattr(e["service"], "promote_strategy_" + kind)
    with ThreadPoolExecutor(2) as pool:
        winner = pool.submit(method, e["principal"], cmd)
        try:
            assert ready.wait(10)
            loser = pool.submit(method, e["principal"], replace(cmd, id=uuid4()))
            waiter = _witness(e["engine"], pids[0])
            assert waiter != pids[0]
            with e["engine"].connect() as observer:
                wait = observer.execute(
                    text("SELECT wait_event_type,wait_event FROM pg_stat_activity WHERE pid=:pid"),
                    {"pid": waiter},
                ).one()
            assert wait.wait_event_type == "Lock"
            print("G2_DUPLICATE_WAIT", kind, pids[0], waiter, tuple(wait))
        finally:
            release.set()
        result = winner.result(timeout=15)
        with pytest.raises(ResearchBaseError) as exc:
            loser.result(timeout=15)
    assert exc.value.code is ErrorCode.DUPLICATE_CONTENT
    assert result.capture_id == saved.id
    changes = {
        "strategy_" + kind + "_admissions": 1,
        "research_questions" if kind == "question" else "hypotheses": 1,
        "research_question_versions" if kind == "question" else "hypothesis_versions": 1,
    }
    assert counts(e["engine"]) == {t: n + changes.get(t, 0) for t, n in before.items()}


def test_g2_inaccessible_source_precedes_frozen_reference_gate(b02_env):
    from researchbase.application.strategy_candidate_promotion import CaptureNativeStrategyCommand

    e = b02_env
    # Owning Application created this project; it has no links to the existing sources.
    before = counts(e["engine"])
    with pytest.raises(ResearchBaseError) as exc:
        e["service"].capture_native_strategy(
            e["principal"],
            CaptureNativeStrategyCommand(uuid4(), e["other_project"], "Recall", e["sources"]),
        )
    assert exc.value.code is ErrorCode.FORBIDDEN
    assert counts(e["engine"]) == before
