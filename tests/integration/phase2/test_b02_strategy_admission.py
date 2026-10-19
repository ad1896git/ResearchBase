"""Typed admission creates one fresh DRAFT; HUMAN and AGENT use the same policy."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.strategy_candidate_promotion import ExactStrategyQuery
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b02_support import (
    capture,
    count,
    hcommand,
    qcommand,
    reader_role,
    restart,
)

pytest_plugins = ("tests.integration.phase2.b02_support",)


def test_saved_question_and_researcher_adaptation_drafts(b02_env):
    e = b02_env
    saved = capture(e)
    question = e["service"].promote_strategy_question(e["other"], qcommand(e, saved))
    hypothesis = e["service"].promote_strategy_hypothesis(
        e["principal"], hcommand(e, saved, research_question_id=question.research_question_id)
    )
    assert question.admitted_by != saved.captured_by
    assert hypothesis.candidate_text == "Unverified candidate"
    assert hypothesis.statement == "Recall may improve"
    with e["engine"].connect() as conn:
        for table, fk, identity, version in (
            (
                "research_question",
                "research_question_id",
                question.research_question_id,
                question.research_question_version_id,
            ),
            (
                "hypothesis",
                "hypothesis_id",
                hypothesis.hypothesis_id,
                hypothesis.hypothesis_version_id,
            ),
        ):
            row = (
                conn.execute(text(f"SELECT * FROM {table}_versions WHERE id=:id"), {"id": version})
                .mappings()
                .one()
            )
            assert row[fk] == identity and row["status"] == "DRAFT" and row["version_number"] == 1
            assert row["content_hash"] is row["frozen_at"] is None
            assert row["rationale"] == (
                question.rationale if table == "research_question" else hypothesis.rationale
            )
        assert (
            conn.execute(
                text("SELECT scope FROM research_question_versions WHERE id=:id"),
                {"id": question.research_question_version_id},
            ).scalar_one()
            is None
        )
        assert conn.execute(
            text(
                "SELECT expected_direction,success_criteria FROM hypothesis_versions WHERE id=:id"
            ),
            {"id": hypothesis.hypothesis_version_id},
        ).one() == (None, None)
    assert (
        restart(e).get_strategy_question_promotion(
            e["principal"], ExactStrategyQuery(question.id, e["project"])
        )
        == question
    )
    assert (
        restart(e).get_strategy_hypothesis_promotion(
            e["other"], ExactStrategyQuery(hypothesis.id, e["project"])
        )
        == hypothesis
    )


@pytest.mark.parametrize(
    "case,code",
    [
        ("no_answer", ErrorCode.VALIDATION_ERROR),
        ("question_index", ErrorCode.VALIDATION_ERROR),
        ("parent_missing", ErrorCode.NOT_FOUND),
        ("capture_missing", ErrorCode.NOT_FOUND),
    ],
)
def test_bad_admission_has_no_scientific_delta(b02_env, case, code):
    e = b02_env
    saved = capture(e)
    before = [count(e, t) for t in ("research_questions", "hypotheses")]
    with pytest.raises(ResearchBaseError) as caught:
        if case == "question_index":
            e["service"].promote_strategy_question(
                e["principal"], qcommand(e, saved, candidate_index=1)
            )
        else:
            changes = (
                {"candidate_index": 2}
                if case == "no_answer"
                else {"research_question_id": uuid4()}
                if case == "parent_missing"
                else {"capture_id": uuid4()}
            )
            e["service"].promote_strategy_hypothesis(e["principal"], hcommand(e, saved, **changes))
    assert caught.value.code is code
    assert [count(e, t) for t in ("research_questions", "hypotheses")] == before


@pytest.mark.parametrize("role", ["VIEWER", "REVIEWER", "APPROVER", "RESEARCHER"])
def test_reader_roles_and_writer_policy(b02_env, role):
    e = b02_env
    saved = capture(e)
    reader_role(e, e["other"], role)
    assert (
        e["service"].get_strategy_capture(e["other"], ExactStrategyQuery(saved.id, e["project"]))
        == saved
    )
    if role == "RESEARCHER":
        assert (
            e["service"].promote_strategy_question(e["other"], qcommand(e, saved)).admitted_by
            == e["other"].actor_id
        )
    else:
        with pytest.raises(ResearchBaseError) as denied:
            e["service"].promote_strategy_question(e["other"], qcommand(e, saved))
        assert denied.value.code is ErrorCode.FORBIDDEN


@pytest.mark.parametrize("actor_type", ["HUMAN", "AGENT"])
def test_unbound_principal_denied_with_existing_error(b02_env, actor_type):
    e = b02_env
    saved = capture(e)
    actor = uuid4()
    with e["engine"].begin() as conn:
        conn.execute(
            text(
                "INSERT INTO actors(id,actor_type,display_name,created_at) "
                "VALUES(:id,:kind,'Unbound',clock_timestamp())"
            ),
            {"id": actor, "kind": actor_type},
        )
    principal = replace(e["principal"], actor_id=actor)
    e["credentials"].principals[actor] = principal
    for invoke in (
        lambda: e["service"].get_strategy_capture(
            principal, ExactStrategyQuery(saved.id, e["project"])
        ),
        lambda: e["service"].promote_strategy_question(principal, qcommand(e, saved)),
        lambda: e["service"].promote_strategy_hypothesis(principal, hcommand(e, saved)),
    ):
        with pytest.raises(ResearchBaseError) as denied:
            invoke()
        assert denied.value.code is ErrorCode.FORBIDDEN
    assert (
        count(e, "strategy_question_admissions") == count(e, "strategy_hypothesis_admissions") == 0
    )


def test_missing_principal_and_cross_project_are_fail_closed(b02_env):
    e = b02_env
    saved = capture(e)
    with pytest.raises(ResearchBaseError) as denied:
        e["service"].get_strategy_capture(None, ExactStrategyQuery(saved.id, e["project"]))
    assert denied.value.code is ErrorCode.AUTHENTICATION_REQUIRED
    with pytest.raises(ResearchBaseError) as denied:
        e["service"].get_strategy_capture(e["principal"], ExactStrategyQuery(uuid4(), e["project"]))
    assert denied.value.code is ErrorCode.NOT_FOUND


def test_same_reader_cannot_resolve_cross_project_ids_or_parent(b02_env):
    e = b02_env
    saved = capture(e)
    other_project = e["other_project"]
    for identity in (saved.id, uuid4()):
        with pytest.raises(ResearchBaseError) as denied:
            e["service"].get_strategy_capture(
                e["principal"], ExactStrategyQuery(identity, other_project)
            )
        assert denied.value.code is ErrorCode.NOT_FOUND
    question = e["service"].promote_strategy_question(e["principal"], qcommand(e, saved))
    with pytest.raises(ResearchBaseError) as denied:
        e["service"].promote_strategy_hypothesis(
            e["principal"],
            hcommand(
                e,
                saved,
                project_id=other_project,
                research_question_id=question.research_question_id,
            ),
        )
    assert denied.value.code is ErrorCode.NOT_FOUND
