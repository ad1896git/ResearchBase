"""Exact UUID recovery, current entitlement, and immutable saved requests."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.novelty import (
    NoveltyService,
    RecordNoveltyAssessmentCommand,
    RecordPriorArtRelationCommand,
    RecordSearchCoverageCommand,
)
from researchbase.domain.novelty import NoveltyOutcome, PriorArtKind
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

pytest_plugins = ("tests.integration.phase2.pr2_18_fixtures",)


def test_replay_restart_and_conflict_all_commands(novelty_env):
    e = novelty_env
    service = e["service"]
    cov_c = RecordSearchCoverageCommand(
        uuid4(), e["project"], e["plan"], e["executions"], "Selected execution scope."
    )
    cov = service.record_search_coverage(e["author"], cov_c)
    prior_c = RecordPriorArtRelationCommand(
        uuid4(),
        e["project"],
        e["claim"],
        e["source"],
        PriorArtKind.RELATED,
        "Comparison only.",
        (e["evidence"],),
    )
    novel_c = RecordNoveltyAssessmentCommand(
        uuid4(),
        e["project"],
        e["claim"],
        cov.id,
        NoveltyOutcome.INCONCLUSIVE,
        "Insufficient coverage.",
    )
    restarted = NoveltyService(e["factory"], e["credentials"], e["literature"])
    for method, c, field in [
        ("record_search_coverage", cov_c, "coverage_limitations"),
        ("record_prior_art_relation", prior_c, "rationale"),
        ("record_novelty_assessment", novel_c, "limitations"),
    ]:
        first = getattr(service, method)(e["author"], c)
        replay = getattr(restarted, method)(e["author"], c)
        assert first.content_hash == replay.content_hash
        with pytest.raises(ResearchBaseError) as error:
            getattr(restarted, method)(e["author"], replace(c, **{field: "Changed material."}))
        assert error.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
        with pytest.raises(ResearchBaseError) as error:
            getattr(restarted, method)(e["reviewer"], c)
        assert error.value.code is ErrorCode.FORBIDDEN
    permuted = service.record_search_coverage(
        e["author"],
        replace(cov_c, search_execution_ids=tuple(reversed(cov_c.search_execution_ids))),
    )
    assert permuted.content_hash == cov.content_hash
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM search_coverage")).scalar_one() == 1
        assert (
            conn.execute(text("SELECT count(*) FROM search_coverage_executions")).scalar_one() == 2
        )
    e["credentials"].enabled = False
    with pytest.raises(ResearchBaseError) as error:
        restarted.record_search_coverage(e["author"], cov_c)
    assert error.value.code is ErrorCode.FORBIDDEN


@pytest.mark.parametrize("kind", ["coverage", "prior_art", "novelty"])
def test_unknown_commit_exact_uuid_recovery(novelty_env, monkeypatch, kind):
    import psycopg
    from sqlalchemy.exc import OperationalError

    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    e = novelty_env
    cov = (
        e["service"].record_search_coverage(
            e["author"],
            RecordSearchCoverageCommand(
                uuid4(), e["project"], e["plan"], e["executions"], "Selected scope."
            ),
        )
        if kind == "novelty"
        else None
    )
    c = {
        "coverage": lambda: RecordSearchCoverageCommand(
            uuid4(), e["project"], e["plan"], e["executions"], "Scope."
        ),
        "prior_art": lambda: RecordPriorArtRelationCommand(
            uuid4(),
            e["project"],
            e["claim"],
            e["source"],
            PriorArtKind.RELATED,
            "Comparison.",
            (e["evidence"],),
        ),
        "novelty": lambda: RecordNoveltyAssessmentCommand(
            uuid4(),
            e["project"],
            e["claim"],
            cov.id if cov else uuid4(),
            NoveltyOutcome.INCONCLUSIVE,
            "Limited.",
        ),
    }[kind]()
    method = {
        "coverage": "record_search_coverage",
        "prior_art": "record_prior_art_relation",
        "novelty": "record_novelty_assessment",
    }[kind]
    original = SqlAlchemyUnitOfWork.commit
    calls = []

    def uncertain(uow):
        original(uow)
        calls.append(True)
        raise OperationalError("uncertain commit", {}, psycopg.OperationalError("connection lost"))

    with monkeypatch.context() as patcher:
        patcher.setattr(SqlAlchemyUnitOfWork, "commit", uncertain)
        with pytest.raises(RuntimeError):
            getattr(e["service"], method)(e["author"], c)
    assert calls == [True]
    recovered = getattr(e["service"], method)(e["author"], c)
    assert recovered.id == c.id
