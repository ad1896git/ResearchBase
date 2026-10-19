"""Direct SQL creation closure, immutable admission and protected downgrade."""

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.integration.phase2.pr2_19_support import (
    discussion_database_url as _discussion_database_url,
)
from tests.integration.phase2.pr2_19_support import (
    discussion_env as _discussion_env,
)
from tests.integration.phase2.pr2_19_support import (
    pr219_discussion_env as _pr219_discussion_env,
)
from tests.integration.phase2.test_b03_discussion_hypothesis import b03 as _b03
from tests.integration.phase2.test_b03_discussion_hypothesis import (
    durable,
)

pytestmark = pytest.mark.integration


def _insert(c, table, row):
    cols = tuple(row)
    c.execute(
        text(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join(':' + k for k in cols)})"),
        row,
    )


def raw_admission(c, cmd, principal, defect=None):
    at = c.execute(text("SELECT clock_timestamp()")).scalar_one()
    question = c.execute(
        text("SELECT research_question_id FROM research_question_versions WHERE id=:id"),
        {"id": cmd.candidate.research_question_version_id},
    ).scalar_one()
    hid, vid, rid = uuid4(), uuid4(), uuid4()
    h = dict(
        id=hid,
        project_id=cmd.project_id,
        research_question_id=question,
        created_by=principal.actor_id,
        created_at=at,
        current_version_id=None,
        row_version=1,
    )
    v = dict(
        id=vid,
        hypothesis_id=hid,
        version_number=1,
        status="DRAFT",
        statement=cmd.candidate.statement,
        expected_direction=cmd.candidate.expected_direction,
        rationale=cmd.candidate.rationale,
        success_criteria=None,
        created_by=principal.actor_id,
        created_at=at,
        row_version=1,
    )
    if defect == "creator":
        actor = uuid4()
        _insert(
            c,
            "actors",
            dict(id=actor, actor_type="HUMAN", display_name="Guard test", created_at=at),
        )
        v["created_by"] = actor
    if defect == "question":
        h["research_question_id"] = None
    if defect == "material":
        v["statement"] = "wrong initial material"
    if defect == "time":
        v["created_at"] = at.replace(year=2025)
    if defect == "version":
        v["version_number"] = 2
    if defect == "row_version":
        h["row_version"] = 2
    if defect == "frozen":
        v.update(status="FROZEN", content_hash="a" * 64, frozen_at=at)
    _insert(c, "hypotheses", h)
    _insert(c, "hypothesis_versions", v)
    if defect != "pointer":
        c.execute(
            text("UPDATE hypotheses SET current_version_id=:v WHERE id=:h"), {"v": vid, "h": hid}
        )
    r = dict(
        id=rid,
        deployment_id=principal.deployment_id,
        project_id=cmd.project_id,
        actor_id=principal.actor_id,
        command_name="PROMOTE_HYPOTHESIS",
        request_id=uuid4(),
        input_hash="b" * 64,
        result_session_id=cmd.session_id,
        result_turn_id=None,
        completed_at=at,
    )
    if defect == "command":
        r["command_name"] = "CLOSE_SESSION"
    _insert(c, "discussion_command_receipts", r)
    a = dict(
        receipt_id=rid,
        project_id=cmd.project_id,
        session_id=cmd.session_id,
        turn_id=cmd.candidate.turn_id,
        transcript_artifact_version_id=cmd.candidate.transcript_artifact_version_id,
        research_question_version_id=cmd.candidate.research_question_version_id,
        hypothesis_version_id=vid,
        candidate_hash="c" * 64,
        statement=cmd.candidate.statement,
        expected_direction=cmd.candidate.expected_direction,
        rationale=cmd.candidate.rationale,
    )
    if defect == "transcript":
        a["transcript_artifact_version_id"] = c.execute(
            text("SELECT id FROM artifact_versions WHERE id<>:id LIMIT 1"),
            {"id": a["transcript_artifact_version_id"]},
        ).scalar_one()
    if defect != "missing":
        _insert(c, "discussion_hypothesis_admissions", a)
    return r, a


@pytest.mark.parametrize(
    "defect",
    [
        "creator",
        "missing",
        "command",
        "question",
        "material",
        "time",
        "version",
        "row_version",
        "frozen",
        "pointer",
        "transcript",
    ],
)
def test_deferred_creation_failure_rolls_back_every_row(b03, defect):
    _, cmd, env, *_ = b03
    before = durable(env[1])
    with pytest.raises(DBAPIError) as exc:
        with env[1].begin() as c:
            raw_admission(c, cmd, env[3], defect)
            # Deferred closure has not fired until commit.
            assert c.execute(text("SELECT count(*) FROM hypotheses")).scalar_one() == 1
    assert getattr(exc.value.orig, "sqlstate", None) == "P17D3"
    assert durable(env[1]) == before


@pytest.mark.parametrize(
    "table", ["discussion_command_receipts", "discussion_hypothesis_admissions"]
)
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_admission_and_receipt_are_immutable(b03, table, operation):
    service, cmd, env, *_ = b03
    result = service.promote_discussion_to_hypothesis(env[3], cmd)
    column = "id" if table == "discussion_command_receipts" else "receipt_id"
    with pytest.raises(DBAPIError) as exc:
        with env[1].begin() as c:
            sql = (
                f"UPDATE {table} SET {column}={column}"
                if operation == "UPDATE"
                else f"DELETE FROM {table}"
            )
            c.execute(text(sql + f" WHERE {column}=:id"), {"id": result.receipt_id})
    assert getattr(exc.value.orig, "sqlstate", None) == "P17D1"
    assert (
        service.get_discussion_hypothesis_admission(env[3], cmd.project_id, result.receipt_id)
        == result
    )


def test_populated_downgrade_refused(b03):
    service, cmd, env, *_ = b03
    result = service.promote_discussion_to_hypothesis(env[3], cmd)
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", env[1].url.render_as_string(hide_password=False))
    with pytest.raises(DBAPIError) as exc:
        command.downgrade(cfg, "0068_b21_unresolved_capture")
    assert getattr(exc.value.orig, "sqlstate", None) == "P17D3"
    assert (
        service.get_discussion_hypothesis_admission(env[3], cmd.project_id, result.receipt_id)
        == result
    )


def test_existing_output_graft_rejected(b03):
    _, cmd, env, *_ = b03
    with env[1].begin() as c:
        # Commit a valid raw output (creation guard intentionally does not authenticate hashes).
        r, a = raw_admission(c, cmd, env[3])
    before = durable(env[1])
    with pytest.raises(DBAPIError) as exc:
        with env[1].begin() as c:
            # Another relation cannot adopt a committed output even if creation material matches.
            r["id"] = uuid4()
            r["request_id"] = uuid4()
            _insert(c, "discussion_command_receipts", r)
            a["receipt_id"] = r["id"]
            a["candidate_hash"] = "d" * 64
            # Remove existing relation only inside this rolled-back adversarial test.
            c.execute(
                text(
                    "ALTER TABLE discussion_hypothesis_admissions "
                    "DISABLE TRIGGER b03_admission_immutable"
                )
            )
            c.execute(text("DELETE FROM discussion_hypothesis_admissions"))
            _insert(c, "discussion_hypothesis_admissions", a)
    assert getattr(exc.value.orig, "sqlstate", None) == "P17D3"
    assert durable(env[1]) == before


discussion_database_url = _discussion_database_url
discussion_env = _discussion_env
pr219_discussion_env = _pr219_discussion_env
b03 = _b03


@pytest.mark.parametrize(
    "field,constraint",
    [
        ("turn_id", "fk_b03_turn"),
        ("research_question_version_id", "fk_b03_question"),
        ("transcript_artifact_version_id", "fk_b03_transcript"),
        ("project_id", "fk_b03_receipt"),
    ],
)
def test_exact_foreign_keys_reject_mismatched_context(b03, field, constraint):
    _, cmd, env, *_ = b03
    before = durable(env[1])
    with pytest.raises(DBAPIError) as exc:
        with env[1].begin() as c:
            r, a = raw_admission(c, cmd, env[3], "missing")
            a[field] = uuid4()
            _insert(c, "discussion_hypothesis_admissions", a)
    assert getattr(exc.value.orig, "sqlstate", None) == "23503"
    # PostgreSQL may encounter either project FK first; both reject the same invalid scope.
    actual = getattr(getattr(exc.value.orig, "diag", None), "constraint_name", None)
    assert actual in (
        {"fk_b03_receipt", "fk_b03_session"} if field == "project_id" else {constraint}
    )
    assert durable(env[1]) == before
