from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from tests.integration.test_pr17dr_adversarial import _seed_running_run

from researchbase.persistence.database import create_database_engine

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against PostgreSQL 18")
    value = create_database_engine()
    try:
        yield value
    finally:
        value.dispose()


def _seed_claim_version(engine: Engine) -> UUID:
    actor_id, project_id, claim_id, version_id = (uuid4() for _ in range(4))
    now = datetime(2026, 9, 6, tzinfo=UTC)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO actors(id, actor_type, display_name, created_at) "
                "VALUES (:id, 'HUMAN', 'pr17dr2', :now)"
            ),
            {"id": actor_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO projects(id, name, created_by, created_at) "
                "VALUES (:id, 'pr17dr2-claim', :actor, :now)"
            ),
            {"id": project_id, "actor": actor_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO claims(id, project_id, created_by, created_at) "
                "VALUES (:id, :project, :actor, :now)"
            ),
            {"id": claim_id, "project": project_id, "actor": actor_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO claim_versions "
                "(id, claim_id, version_number, status, statement, scope, qualification, "
                "support_set_hash, content_hash, created_by, created_at, frozen_at) "
                "VALUES (:id, :claim, 1, 'FROZEN', 'statement', '{}'::jsonb, 'qualification', "
                ":support_hash, :content_hash, :actor, :now, :now)"
            ),
            {
                "id": version_id,
                "claim": claim_id,
                "support_hash": "a" * 64,
                "content_hash": "b" * 64,
                "actor": actor_id,
                "now": now,
            },
        )
        connection.execute(
            text("UPDATE claims SET current_version_id=:version WHERE id=:claim"),
            {"version": version_id, "claim": claim_id},
        )
    return version_id


def _assert_trigger_sqlstate(operation: object, expected: str) -> None:
    with pytest.raises(DBAPIError) as raised:
        operation()  # type: ignore[operator]
    assert getattr(raised.value.orig, "sqlstate", None) == expected


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("content_hash", "c" * 64),
        ("frozen_at", datetime(2026, 9, 6, 1, tzinfo=UTC)),
        ("support_set_hash", "d" * 64),
    ],
)
def test_each_claim_supersession_protected_field_is_directly_guarded(
    engine: Engine, field: str, value: object
) -> None:
    version_id = _seed_claim_version(engine)

    with engine.connect() as connection:
        before = connection.execute(
            text(
                "SELECT status, support_set_hash, content_hash, frozen_at, row_version "
                "FROM public.claim_versions WHERE id=:id"
            ),
            {"id": version_id},
        ).one()

    def mutate() -> None:
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"UPDATE public.claim_versions SET status='SUPERSEDED', {field}=:value, "
                    "row_version=2 WHERE id=:id"
                ),
                {"id": version_id, "value": value},
            )

    # The frozen pre-PR17D finalized-material trigger is the first guard for
    # this multi-column mutation and reports PostgreSQL's check-violation
    # class.  The PR17D guard remains active and the mutation is rejected.
    _assert_trigger_sqlstate(mutate, "23514")
    with engine.connect() as connection:
        after = connection.execute(
            text(
                "SELECT status, support_set_hash, content_hash, frozen_at, row_version "
                "FROM public.claim_versions WHERE id=:id"
            ),
            {"id": version_id},
        ).one()
    assert after == before

    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE public.claim_versions SET status='SUPERSEDED', row_version=2 WHERE id=:id"
            ),
            {"id": version_id},
        )
    with engine.connect() as connection:
        legal = connection.execute(
            text("SELECT status, row_version FROM public.claim_versions WHERE id=:id"),
            {"id": version_id},
        ).one()
    assert (legal.status, legal.row_version) == ("SUPERSEDED", 2)


@pytest.mark.parametrize(
    ("status", "field", "value", "legal_exit_code", "legal_failure_reason"),
    [
        ("SUCCEEDED", "finished_at", None, None, None),
        ("SUCCEEDED", "inputs_sealed_at", datetime(2026, 9, 6, 2, tzinfo=UTC), None, None),
        ("SUCCEEDED", "started_at", datetime(2026, 9, 6, 2, tzinfo=UTC), None, None),
        ("SUCCEEDED", "exit_code", 1, None, None),
        ("SUCCEEDED", "failure_reason", "forbidden", None, None),
        ("FAILED", "finished_at", None, 0, "failed"),
        ("FAILED", "inputs_sealed_at", datetime(2026, 9, 6, 2, tzinfo=UTC), 0, "failed"),
        ("FAILED", "started_at", datetime(2026, 9, 6, 2, tzinfo=UTC), 0, "failed"),
        ("FAILED", "exit_code", None, None, None),
        ("FAILED", "failure_reason", None, 0, "failed"),
        ("CANCELLED", "finished_at", None, None, None),
        ("CANCELLED", "inputs_sealed_at", datetime(2026, 9, 6, 2, tzinfo=UTC), None, None),
        ("CANCELLED", "started_at", datetime(2026, 9, 6, 2, tzinfo=UTC), None, None),
        ("CANCELLED", "exit_code", 1, None, None),
        ("CANCELLED", "failure_reason", "forbidden", None, None),
    ],
)
def test_terminal_state_attacks_reject_seal_timestamp_and_metadata_mutations(
    engine: Engine,
    status: str,
    field: str,
    value: object,
    legal_exit_code: int | None,
    legal_failure_reason: str | None,
) -> None:
    run_id = _seed_running_run(engine)
    assignments = {
        "inputs_sealed_at": ":sealed",
        "started_at": ":started",
        "finished_at": ":finished",
        "exit_code": ":exit_code",
        "failure_reason": ":failure_reason",
    }
    assignments[field] = ":attack"
    set_clause = ", ".join(f"{column}={bind}" for column, bind in assignments.items())
    with engine.connect() as connection:
        before = connection.execute(
            text(
                "SELECT status, inputs_sealed_at, started_at, finished_at, exit_code, "
                "failure_reason, row_version FROM public.runs WHERE id=:id"
            ),
            {"id": run_id},
        ).one()

    def mutate() -> None:
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"UPDATE public.runs SET status=:status, {set_clause}, "
                    "row_version=2 WHERE id=:id"
                ),
                {
                    "id": run_id,
                    "status": status,
                    "attack": value,
                    "sealed": datetime(2026, 9, 6, 0, tzinfo=UTC),
                    "started": datetime(2026, 9, 6, 0, 30, tzinfo=UTC),
                    "finished": datetime(2026, 9, 6, 1, tzinfo=UTC),
                    "exit_code": legal_exit_code,
                    "failure_reason": legal_failure_reason,
                },
            )

    _assert_trigger_sqlstate(mutate, "P17D2")
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT status, inputs_sealed_at, started_at, finished_at, exit_code, "
                "failure_reason, row_version FROM public.runs WHERE id=:id"
            ),
            {"id": run_id},
        ).one()
    assert row == before


@pytest.mark.parametrize(
    ("status", "exit_code", "failure_reason"),
    [
        ("SUCCEEDED", 0, None),
        ("FAILED", 1, "failed"),
        ("FAILED", None, "failed"),
        ("CANCELLED", None, None),
    ],
)
def test_terminal_state_legal_controls_remain_accepted(
    engine: Engine, status: str, exit_code: int | None, failure_reason: str | None
) -> None:
    run_id = _seed_running_run(engine)
    finished = datetime(2026, 9, 6, 1, tzinfo=UTC)
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE public.runs SET status=:status, finished_at=:finished, "
                "exit_code=:exit_code, failure_reason=:failure_reason, row_version=2 WHERE id=:id"
            ),
            {
                "id": run_id,
                "status": status,
                "finished": finished,
                "exit_code": exit_code,
                "failure_reason": failure_reason,
            },
        )
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT status, finished_at, exit_code, failure_reason, row_version "
                "FROM public.runs WHERE id=:id"
            ),
            {"id": run_id},
        ).one()
    assert (row.status, row.finished_at, row.exit_code, row.failure_reason, row.row_version) == (
        status,
        finished,
        exit_code,
        failure_reason,
        2,
    )
