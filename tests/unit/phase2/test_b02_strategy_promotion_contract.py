"""Closed B02 commands, selectors and transport compatibility."""

from dataclasses import FrozenInstanceError, replace
from typing import Any
from uuid import UUID, uuid4

import pytest

from researchbase.application.native_research_strategy import (
    NativeResearchStrategy,
    ResearchStrategyContext,
    ResearchStrategyRequest,
)
from researchbase.application.strategy_candidate_promotion import (
    CaptureNativeStrategyCommand,
    ExactStrategyQuery,
    PromoteStrategyHypothesisCommand,
    PromoteStrategyQuestionCommand,
    capture_envelope,
    validate_envelope,
)
from researchbase.domain.strategy_candidate_promotion import (
    normalize_text,
    select_hypothesis,
    select_question,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.unit.phase2.test_pr2_08_native_strategy import ScriptedRAG


def command():
    return CaptureNativeStrategyCommand(
        uuid4(), uuid4(), " Cafe\u0301 ", (UUID(int=2), UUID(int=1))
    )


def test_closed_frozen_normalized_command():
    c: Any = command()
    assert c.topic == "Café"
    assert c.source_version_ids == (UUID(int=1), UUID(int=2))
    with pytest.raises(FrozenInstanceError):
        c.topic = "changed"
    with pytest.raises(TypeError):
        CaptureNativeStrategyCommand(
            **dict(
                id=c.id,
                project_id=c.project_id,
                topic="a",
                source_version_ids=c.source_version_ids,
                actor_id=uuid4(),
            )
        )
    h = PromoteStrategyHypothesisCommand(uuid4(), c.project_id, c.id, 0, " reason ", " a\u0301  b ")
    assert h.statement == "á  b" and h.research_question_id is None
    assert not hasattr(h, "expected_direction")


@pytest.mark.parametrize(
    "changes",
    [
        dict(id="bad"),
        dict(project_id=True),
        dict(topic=""),
        dict(topic="x" * 256),
        dict(topic="a\n b"),
        dict(topic="a\ud800"),
        dict(source_version_ids=[]),
        dict(source_version_ids=()),
        dict(source_version_ids=(uuid4(),) * 2),
        dict(source_version_ids=tuple(uuid4() for _ in range(101))),
        dict(source_version_ids=("bad",)),
        dict(max_evidence_candidates=True),
        dict(max_evidence_candidates=0),
        dict(max_evidence_candidates=101),
        dict(max_evidence_candidates="1"),
    ],
)
def test_capture_strict_bounds(changes):
    with pytest.raises(ResearchBaseError) as caught:
        replace(command(), **changes)
    assert caught.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("index", [True, -1, 1000, 0.5, "0", None])
def test_admission_strict_index(index):
    with pytest.raises(ResearchBaseError):
        PromoteStrategyQuestionCommand(uuid4(), uuid4(), uuid4(), index, "reason")


@pytest.mark.parametrize("text", ["", " ", "x" * 16001, "line\nfeed", "bad\x00", "bad\udfff"])
def test_authored_text_bounds(text):
    with pytest.raises(ResearchBaseError):
        normalize_text(text)


def test_selectors_preserve_original_duplicate_positions_and_empty_denial():
    result = {
        "open_question_candidates": [" Café ", " Café "],
        "research_brief_candidate": {
            "sections": [{"answer_candidate": None}, {"answer_candidate": " exact answer "}]
        },
    }
    assert select_question(result, 0) == select_question(result, 1) == (" Café ", "Café")
    assert select_hypothesis(result, 1) == " exact answer "
    for index in (0, 2):
        with pytest.raises(ResearchBaseError):
            select_hypothesis(result, index)
    with pytest.raises(ResearchBaseError):
        select_question({"open_question_candidates": []}, 0)
    with pytest.raises(ResearchBaseError):
        select_question(result, 2)


def test_closed_envelope_unknown_fields_and_no_native_hypotheses():
    import json

    from researchbase.foundation.canonical_json import canonical_json_bytes

    c = command()
    req = ResearchStrategyRequest(c.topic, c.source_version_ids)
    ctx = ResearchStrategyContext(req, lambda: False)
    native = NativeResearchStrategy()
    result = native.execute(
        native.prepare_plan(req, ctx), ScriptedRAG(c.source_version_ids[0]), ctx
    )
    data = capture_envelope(c, result)
    assert validate_envelope(data, c.project_id)["result"]["hypothesis_candidates"] == []
    for path in ((), ("result",), ("result", "execution_metadata"), ("request",)):
        value = json.loads(data)
        target = value
        for key in path:
            target = target[key]
        target["unapproved"] = "x"
        with pytest.raises(ResearchBaseError):
            validate_envelope(canonical_json_bytes(value), c.project_id)
    with pytest.raises(ResearchBaseError):
        capture_envelope(c, replace(result, hypothesis_candidates=("invented",)))


def test_exact_query_strict_ids():
    with pytest.raises(ResearchBaseError):
        bad: Any = "bad"
        ExactStrategyQuery(bad, uuid4())


@pytest.mark.parametrize(
    "name,http,cli",
    [
        ("VALIDATION_ERROR", 422, 2),
        ("AUTHENTICATION_REQUIRED", 401, 3),
        ("FORBIDDEN", 403, 3),
        ("NOT_FOUND", 404, 3),
        ("SOURCE_VERSION_NOT_FOUND", 404, 3),
        ("FROZEN_REFERENCE_REQUIRED", 409, 5),
        ("PROVENANCE_CLOSURE_VIOLATION", 409, 5),
        ("IDEMPOTENCY_CONFLICT", 409, 4),
        ("DUPLICATE_CONTENT", 409, 4),
        ("IMMUTABLE_RECORD", 409, 4),
        ("REFERENTIAL_INTEGRITY_ERROR", 409, 5),
        ("CONCURRENT_MODIFICATION", 409, 4),
        ("ADAPTER_UNAVAILABLE", 503, 5),
    ],
)
def test_exact_existing_transport_mapping(name, http, cli):
    from researchbase.api.errors import _STATUS
    from researchbase.cli.errors import CLI_EXIT_CODES

    code = ErrorCode(name)
    assert _STATUS[code] == http and CLI_EXIT_CODES[code] == cli


def test_brief_original_multiline_prose_is_retained_without_authored_normalization():
    original = "First line.\nSecond line."
    assert (
        select_hypothesis(
            {"research_brief_candidate": {"sections": [{"answer_candidate": original}]}}, 0
        )
        == original
    )
    # Only caller-authored statement/rationale and derived question text normalize.
    with pytest.raises(ResearchBaseError):
        normalize_text(original)
