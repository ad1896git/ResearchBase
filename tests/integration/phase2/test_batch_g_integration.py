"""Batch G composition: exact migration predecessors and screening review history."""

import hashlib
import json
from dataclasses import replace
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import create_engine, text

from researchbase.application.revision_action import (
    RecordConcernReReviewCommand,
    RecordNoveltyRevisionCommand,
    RevisionActionService,
)
from researchbase.domain.novelty import NoveltyOutcome
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b20_screening_support import (
    compared,
    record,
    request,
    successful_plan,
)
from tests.integration.phase2.test_b22_prior_art_schema import config
from tests.integration.phase2.test_b23_novelty_review import _review

pytest_plugins = ("tests.integration.phase2.pr2_18_fixtures",)
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("shape", ["incomplete", "no_hits", "not_close"])
def test_screening_assessment_review_and_replay(novelty_env, shape):
    e = novelty_env
    if shape == "not_close":
        e, assessment_command, _, _ = compared(e)
    elif shape == "no_hits":
        e, _, _ = successful_plan(e)
        assessment_command = replace(
            request(e), assessment=NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE
        )
    else:
        assessment_command = request(e)
    assessment = record(e, assessment_command)
    request_id = uuid4()
    service, review = _review(e, assessment, request_id)
    assert review.target.screening_basis == assessment.screening_basis
    assert service.read(e["reviewer"], e["project"], review.id).content_hash == review.content_hash
    assert _review(e, assessment, request_id)[1].content_hash == review.content_hash
    with e["engine"].connect() as conn:
        assert (
            conn.execute(
                text("SELECT b23_assessment_hash(:id,:project)"),
                {"id": assessment.id, "project": e["project"]},
            ).scalar_one()
            == assessment.content_hash
        )
        kinds = set(
            conn.execute(
                text("SELECT kind FROM b23_dependencies(ARRAY[CAST(:id AS uuid)])"),
                {"id": assessment.id},
            ).scalars()
        )
        assert "novelty_assessment_probes" in kinds
        if shape != "no_hits":
            assert "novelty_assessment_screening_results" in kinds

    successor = record(
        e, replace(assessment_command, id=uuid4(), supersedes_assessment_id=assessment.id)
    )
    actions = RevisionActionService(e["factory"], e["credentials"], e["literature"])
    if shape == "incomplete":
        with pytest.raises(ResearchBaseError) as caught:
            actions.record_novelty_revision(
                e["author"],
                RecordNoveltyRevisionCommand(
                    uuid4(), e["project"], review.issues[0].id, successor.id
                ),
            )
        assert caught.value.code is ErrorCode.INVALID_STATE_TRANSITION
        return
    action = actions.record_novelty_revision(
        e["author"],
        RecordNoveltyRevisionCommand(uuid4(), e["project"], review.issues[0].id, successor.id),
    )
    _, re_review = _review(e, successor, issues=())
    link = actions.record_concern_re_review(
        e["reviewer"],
        RecordConcernReReviewCommand(e["project"], action.id, re_review.id),
        novelty=True,
    )
    assert link.action.result.screening_basis == successor.screening_basis
    assert (
        actions.read_novelty_re_review(
            e["reviewer"], e["project"], action.id, re_review.id
        ).action.content_hash
        == action.content_hash
    )


def test_each_downgrade_restores_exact_predecessor_catalog(phase2_database_url):
    cfg = config(phase2_database_url)
    engine = create_engine(phase2_database_url)

    def catalog():
        with engine.connect() as conn:
            return {
                "functions": conn.execute(
                    text(
                        "SELECT p.oid::regprocedure::text,pg_get_functiondef(p.oid) "
                        "FROM pg_proc p WHERE p.pronamespace='public'::regnamespace ORDER BY 1"
                    )
                ).all(),
                "constraints": conn.execute(
                    text(
                        "SELECT conrelid::regclass::text,conname,pg_get_constraintdef(oid) "
                        "FROM pg_constraint WHERE connamespace='public'::regnamespace ORDER BY 1,2"
                    )
                ).all(),
                "triggers": conn.execute(
                    text(
                        "SELECT tgrelid::regclass::text,tgname,pg_get_triggerdef(oid) "
                        "FROM pg_trigger WHERE NOT tgisinternal AND tgrelid IN "
                        "(SELECT oid FROM pg_class WHERE relnamespace='public'::regnamespace) "
                        "ORDER BY 1,2"
                    )
                ).all(),
            }

    def summary(snapshot):
        result = {
            kind: {
                "count": len(rows),
                "sha256": hashlib.sha256(
                    json.dumps([list(row) for row in rows], ensure_ascii=False).encode()
                ).hexdigest(),
            }
            for kind, rows in snapshot.items()
        }
        result["b13_stale"] = {
            "sha256": hashlib.sha256(
                next(
                    definition
                    for name, definition in snapshot["functions"]
                    if name == "b13_stale(approval_grants)"
                ).encode()
            ).hexdigest()
        }
        return result

    revisions = (
        "0068_b21_unresolved_capture",
        "0069_b13_stale_gate_denials",
        "0070_b20_screening_basis",
        "0071_b23_novelty_review",
        "0072_b03_discussion_hypothesis",
        "0073_b02_strategy_admission",
    )
    try:
        snapshots = {}
        for revision in revisions:
            command.upgrade(cfg, revision)
            snapshots[revision] = catalog()
            print("UPGRADE", revision, summary(snapshots[revision]))
        for revision in reversed(revisions[:-1]):
            command.downgrade(cfg, revision)
            restored = catalog()
            assert restored == snapshots[revision]
            print("DOWNGRADE", revision, "EXACT MATCH", summary(restored))
        command.upgrade(cfg, "head")
        assert catalog() == snapshots[revisions[-1]]
        print("RE-UPGRADE", revisions[-1], "EXACT MATCH", summary(catalog()))
    finally:
        engine.dispose()
