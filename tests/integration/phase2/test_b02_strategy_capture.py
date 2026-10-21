"""Real native execution; capture changes no scientific facts."""

import json
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import event

from researchbase.application.native_research_strategy import StrategyCancelled
from researchbase.application.strategy_candidate_promotion import (
    CaptureNativeStrategyCommand,
    ExactStrategyQuery,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b02_support import capture, count, restart


def test_capture_exact_bytes_after_restart_no_scientific_delta(b02_env):
    e = b02_env
    tables = ("research_questions", "hypotheses", "literature_evidence", "claims", "runs")
    before = [count(e, t) for t in tables]
    saved = capture(e)
    assert (
        restart(e).get_strategy_capture(e["other"], ExactStrategyQuery(saved.id, e["project"]))
        == saved
    )
    data = json.loads(e["store"].open("sha256:" + saved.artifact_content_hash))
    assert data["request"]["source_version_ids"] == [str(v) for v in sorted(e["sources"], key=str)]
    assert data["result"]["hypothesis_candidates"] == []
    assert data["result"]["research_brief_candidate"]["coverage_limitations"] == [
        "SOURCE_SET_ONLY",
        "NOT_COMPREHENSIVE",
    ]
    assert saved.strategy_version == "candidate-v1"
    assert [count(e, t) for t in tables] == before


def test_external_execution_is_outside_database_transaction(b02_env, monkeypatch):
    e = b02_env
    active = []
    engines = []
    original_factory = e["service"]._factory
    # Track the actual service connection from connection pool events.
    with original_factory() as uow:
        engine = uow._require_session().get_bind()
        engines.append(engine)
    event.listen(engine, "begin", lambda conn: active.append(conn))
    event.listen(engine, "commit", lambda conn: active.remove(conn))
    event.listen(engine, "rollback", lambda conn: active.remove(conn))
    answer = e["rag"].answer

    def checked(request, context):
        assert not active
        return answer(request, context)

    monkeypatch.setattr(e["rag"], "answer", checked)
    capture(e)
    assert len(e["rag"].calls) == 3


def test_handled_retrieval_failure_is_saved(b02_env):
    e = b02_env
    e["rag"].failure = {"What methods are reported for Recall?"}
    saved = capture(e)
    value = json.loads(e["store"].open("sha256:" + saved.artifact_content_hash))["result"]
    assert "RAG_UNAVAILABLE" in value["warnings"]
    assert value["research_brief_candidate"]["sections"][0]["answer_candidate"] is None
    assert "synthetic-secret" not in json.dumps(value)


@pytest.mark.parametrize(
    "case", ["missing_source", "cancelled", "oversize", "unconfigured", "bad_command"]
)
def test_capture_failure_no_canonical_delta(b02_env, monkeypatch, case):
    e = b02_env
    before = count(e, "artifacts")
    command = CaptureNativeStrategyCommand(uuid4(), e["project"], "Recall", e["sources"])
    if case == "missing_source":
        command = replace(command, source_version_ids=(uuid4(),))
    elif case == "cancelled":
        e["service"]._cancel = lambda: True
    elif case == "oversize":
        monkeypatch.setattr(
            "researchbase.application.strategy_candidate_promotion.MAX_ENVELOPE_BYTES", 100
        )
    elif case == "unconfigured":
        e["service"]._capabilities = None
    else:
        command = object()
    with pytest.raises((ResearchBaseError, StrategyCancelled)):
        e["service"].capture_native_strategy(e["principal"], command)
    assert count(e, "strategy_candidate_captures") == 0
    assert count(e, "artifacts") == before


def test_substituted_capture_bytes_fail_closed(b02_env, monkeypatch):
    e = b02_env
    saved = capture(e)
    original = e["store"].open
    monkeypatch.setattr(
        e["store"],
        "open",
        lambda key: b"{}" if key.endswith(saved.artifact_content_hash) else original(key),
    )
    with pytest.raises(ResearchBaseError) as denied:
        restart(e).get_strategy_capture(e["principal"], ExactStrategyQuery(saved.id, e["project"]))
    assert denied.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
