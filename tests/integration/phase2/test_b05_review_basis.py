"""Complete exact manuscript review basis without authority or readiness effects."""

# ruff: noqa: E501
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.internal_review import ReviewIssueRequest
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
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

b04_env = _b04_env
b05_env = _b05_env
conclusion_env = _conclusion_env
phase2_database_url = _phase2_database_url

pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


def test_empty_then_all_types_recommendations_repeated_reviewer_and_blocker(b05_env):
    env = b05_env
    seal(env)
    basis = collect(env)
    assert not basis.gate_satisfied and basis.reviews == ()
    assert len(basis.basis) == 1
    types = [
        "SCIENTIFIC",
        "STATISTICAL",
        "LITERATURE",
        "REPRODUCIBILITY",
        "EDITORIAL",
        "COMPREHENSIVE",
    ]
    recommendations = ["ACCEPT", "MINOR_REVISION", "MAJOR_REVISION", "REJECT", "UNCERTAIN"]
    saved = []
    for kind in types:
        for recommendation in recommendations:
            saved.append(create(env, review_type=kind, recommendation=recommendation))
    basis = collect(env)
    assert basis.gate_satisfied
    assert [r.id for r in basis.reviews] == sorted([r.id for r in saved], key=str)
    assert len(basis.basis) == 31
    assert [r.ordinal for r in basis.basis] == list(range(31))
    assert [(r.type, str(r.id), r.content_hash) for r in basis.basis] == sorted(
        (r.type, str(r.id), r.content_hash) for r in basis.basis
    )
    unfavorable = create(
        env,
        recommendation="REJECT",
        issues=(ReviewIssueRequest("BLOCKING", "OTHER", "Open blocker"),),
    )
    blocked = collect(env)
    assert not blocked.gate_satisfied and blocked.blocking_issue_ids == (unfavorable.issues[0].id,)
    assert len(blocked.reviews) == 31 and len(blocked.basis) == 32


def test_later_issue_changes_gate_and_replay_not_saved_review_hash(b05_env):
    env = b05_env
    seal(env)
    request = uuid4()
    review = create(env, request=request)
    assert collect(env).gate_satisfied
    with env[4]() as uow:
        uow.internal_review.insert_issue(
            {
                "id": uuid4(),
                "review_record_id": review.id,
                "severity": "BLOCKING",
                "issue_type": "OTHER",
                "description": "Later blocker",
                "ordinal": 0,
                "created_at": uow.manuscript_freeze.at(),
            }
        )
        uow.commit()
    read = env[0].read(env[3], env[1].project_id, review.id)
    assert read.content_hash == review.content_hash and len(read.issues) == 1
    assert not collect(env).gate_satisfied
    with pytest.raises(ResearchBaseError) as exc:
        create(env, request=request)
    assert exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT


@pytest.mark.parametrize(
    "field,value", [("content_hash", "0" * 64), ("target_content_hash", "0" * 64)]
)
def test_corrupt_exact_review_fails_closed(b05_env, field, value):
    env = b05_env
    seal(env)
    request = uuid4()
    review = create(env, request=request)
    # Deliberate corruption by privileged import; no fabricated manuscript seal.
    with env[5].begin() as conn:
        conn.execute(text("ALTER TABLE internal_review_records DISABLE TRIGGER USER"))
        conn.execute(
            text(f"UPDATE internal_review_records SET {field}=:value WHERE id=:id"),
            {"id": review.id, "value": value},
        )
        conn.execute(text("ALTER TABLE internal_review_records ENABLE TRIGGER USER"))
    with pytest.raises(ResearchBaseError) as exc:
        collect(env)
    assert exc.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    with pytest.raises(ResearchBaseError) as exc:
        create(env, request=request)
    assert exc.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_historical_authority_survives_reviewer_retirement(b05_env):
    env = b05_env
    seal(env)
    review = create(env)
    with env[5].begin() as conn:
        conn.execute(
            text(
                "UPDATE actors SET retired_at=clock_timestamp(),row_version=row_version+1 WHERE id=:id"
            ),
            {"id": env[3].actor_id},
        )
    # Author is permitted to read an independent historical evaluation.
    assert env[0].read(env[2], env[1].project_id, review.id) == review
    with env[4]() as uow:
        uow.internal_review.prepare_write()
        basis = env[0].collect_manuscript_review_basis(
            uow, env[1].project_id, env[1].manuscript_version_id
        )
    assert basis.gate_satisfied


def test_helper_rejects_unprotected_transaction(b05_env):
    env = b05_env
    with env[4]() as uow:
        with pytest.raises(ResearchBaseError) as exc:
            env[0].collect_manuscript_review_basis(
                uow, env[1].project_id, env[1].manuscript_version_id
            )
    assert exc.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


@pytest.mark.parametrize(
    "table,field", [("internal_review_records", "summary"), ("review_issues", "description")]
)
def test_saved_non_nfc_material_rejected(b05_env, table, field):
    env = b05_env
    seal(env)
    review = create(env, summary="é", issues=(ReviewIssueRequest("MINOR", "OTHER", "é"),))
    with env[5].begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER USER"))
        where = "id=:id" if table == "internal_review_records" else "review_record_id=:id"
        conn.execute(
            text(f"UPDATE {table} SET {field}=:text WHERE {where}"),
            {"id": review.id, "text": "e\u0301"},
        )
        conn.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER USER"))
    with pytest.raises(ResearchBaseError) as exc:
        collect(env)
    assert exc.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
