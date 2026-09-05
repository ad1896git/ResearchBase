from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from threading import Event, Thread
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError

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


def _seed_research_question_version(engine: Engine) -> tuple[UUID, UUID]:
    actor_id, project_id, question_id, version_id = (uuid4() for _ in range(4))
    now = datetime(2026, 9, 5, tzinfo=UTC)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO actors(id, actor_type, display_name, created_at) "
                "VALUES (:id, 'human', 'test', :now)"
            ),
            {"id": actor_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO projects(id, name, created_by, created_at) "
                "VALUES (:id, 'pr17dr', :actor, :now)"
            ),
            {"id": project_id, "actor": actor_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO research_questions(id, project_id, created_by, created_at) "
                "VALUES (:id, :project, :actor, :now)"
            ),
            {"id": question_id, "project": project_id, "actor": actor_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO research_question_versions "
                "(id, research_question_id, version_number, status, question_text, "
                "content_hash, created_by, created_at, frozen_at) "
                "VALUES (:id, :question, 1, 'FROZEN', 'frozen question', :hash, :actor, :now, :now)"
            ),
            {
                "id": version_id,
                "question": question_id,
                "hash": "a" * 64,
                "actor": actor_id,
                "now": now,
            },
        )
    return version_id, question_id


def _seed_running_run(engine: Engine) -> UUID:
    actor_id, project_id, spec_id, spec_version_id, run_id = (uuid4() for _ in range(5))
    now = datetime(2026, 9, 5, tzinfo=UTC)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO actors(id, actor_type, display_name, created_at) "
                "VALUES (:id, 'human', 'test', :now)"
            ),
            {"id": actor_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO projects(id, name, created_by, created_at) "
                "VALUES (:id, 'pr17dr-run', :actor, :now)"
            ),
            {"id": project_id, "actor": actor_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO experiment_specs(id, project_id, created_by, created_at) "
                "VALUES (:id, :project, :actor, :now)"
            ),
            {"id": spec_id, "project": project_id, "actor": actor_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO experiment_spec_versions "
                "(id, experiment_spec_id, version_number, status, title, objective, "
                "protocol, content_hash, created_by, created_at, frozen_at) "
                "VALUES (:id, :spec, 1, 'FROZEN', 'title', 'objective', "
                "'{}'::jsonb, :hash, :actor, :now, :now)"
            ),
            {
                "id": spec_version_id,
                "spec": spec_id,
                "hash": "b" * 64,
                "actor": actor_id,
                "now": now,
            },
        )
        connection.execute(
            text(
                "INSERT INTO runs "
                "(id, project_id, experiment_spec_version_id, run_type, status, "
                "inputs_sealed_at, started_at, created_by, created_at) "
                "VALUES (:id, :project, :spec_version, 'experiment', 'RUNNING', "
                ":now, :now, :actor, :now)"
            ),
            {
                "id": run_id,
                "project": project_id,
                "spec_version": spec_version_id,
                "actor": actor_id,
                "now": now,
            },
        )
    return run_id


def _seed_planned_run_with_snapshot(engine: Engine) -> tuple[UUID, UUID]:
    actor_id, project_id, spec_id, spec_version_id, run_id = (uuid4() for _ in range(5))
    dataset_id, snapshot_id = (uuid4() for _ in range(2))
    now = datetime(2026, 9, 5, tzinfo=UTC)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO actors(id, actor_type, display_name, created_at) "
                "VALUES (:id, 'human', 'test', :now)"
            ),
            {"id": actor_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO projects(id, name, created_by, created_at) "
                "VALUES (:id, 'pr17dr-input', :actor, :now)"
            ),
            {"id": project_id, "actor": actor_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO experiment_specs(id, project_id, created_by, created_at) "
                "VALUES (:id, :project, :actor, :now)"
            ),
            {"id": spec_id, "project": project_id, "actor": actor_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO experiment_spec_versions "
                "(id, experiment_spec_id, version_number, status, title, objective, protocol, "
                "content_hash, created_by, created_at, frozen_at) VALUES "
                "(:id, :spec, 1, 'FROZEN', 'title', 'objective', '{}'::jsonb, :hash, "
                ":actor, :now, :now)"
            ),
            {
                "id": spec_version_id,
                "spec": spec_id,
                "hash": "e" * 64,
                "actor": actor_id,
                "now": now,
            },
        )
        connection.execute(
            text(
                "INSERT INTO runs(id, project_id, experiment_spec_version_id, run_type, status, "
                "created_by, created_at) VALUES (:id, :project, :spec, 'experiment', 'PLANNED', "
                ":actor, :now)"
            ),
            {
                "id": run_id,
                "project": project_id,
                "spec": spec_version_id,
                "actor": actor_id,
                "now": now,
            },
        )
        connection.execute(
            text(
                "INSERT INTO datasets(id, project_id, name, lifecycle_status, "
                "created_by, created_at) "
                "VALUES (:id, :project, 'dataset', 'active', :actor, :now)"
            ),
            {"id": dataset_id, "project": project_id, "actor": actor_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO dataset_snapshots "
                "(id, dataset_id, manifest_hash, selection_definition, content_hash, "
                "created_by, created_at) "
                "VALUES (:id, :dataset, :hash, '{}'::jsonb, :hash, :actor, :now)"
            ),
            {
                "id": snapshot_id,
                "dataset": dataset_id,
                "hash": "f" * 64,
                "actor": actor_id,
                "now": now,
            },
        )
    return run_id, snapshot_id


def _seed_audit_finding(engine: Engine) -> UUID:
    actor_id, project_id, finding_id = (uuid4() for _ in range(3))
    now = datetime(2026, 9, 5, tzinfo=UTC)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO actors(id, actor_type, display_name, created_at) "
                "VALUES (:id, 'human', 'test', :now)"
            ),
            {"id": actor_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO projects(id, name, created_by, created_at) "
                "VALUES (:id, 'pr17dr-audit', :actor, :now)"
            ),
            {"id": project_id, "actor": actor_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO audit_findings "
                "(id, project_id, finding_type, severity, title, description, target_type, "
                "target_id, status, created_by, created_at) VALUES "
                "(:id, :project, 'quality', 'minor', 'finding', 'description', 'run', "
                ":target, 'open', :actor, :now)"
            ),
            {
                "id": finding_id,
                "project": project_id,
                "target": uuid4(),
                "actor": actor_id,
                "now": now,
            },
        )
    return finding_id


def _assert_trigger_error(operation: Callable[[], object], expected_sqlstate: str) -> None:
    with pytest.raises(DBAPIError) as raised:
        operation()
    assert getattr(raised.value.orig, "sqlstate", None) == expected_sqlstate


@pytest.mark.parametrize("field", ["content_hash", "frozen_at"])
def test_frozen_to_superseded_cannot_change_protected_version_fields(
    engine: Engine, field: str
) -> None:
    version_id, _ = _seed_research_question_version(engine)
    now = datetime(2026, 9, 5, 1, tzinfo=UTC)
    value = "c" * 64 if field == "content_hash" else now

    def mutate() -> None:
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"UPDATE public.research_question_versions SET status='SUPERSEDED', "
                    f"{field}=:value, row_version=2 WHERE id=:id"
                ),
                {"id": version_id, "value": value},
            )

    _assert_trigger_error(mutate, "P17D1")
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT status, content_hash, frozen_at, row_version "
                "FROM public.research_question_versions WHERE id=:id"
            ),
            {"id": version_id},
        ).one()
    assert row.status == "FROZEN"
    assert row.content_hash == "a" * 64
    assert row.frozen_at == datetime(2026, 9, 5, tzinfo=UTC)
    assert row.row_version == 1


def test_frozen_to_superseded_status_only_transition_succeeds(engine: Engine) -> None:
    version_id, _ = _seed_research_question_version(engine)

    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE public.research_question_versions SET status='SUPERSEDED', row_version=2 "
                "WHERE id=:id"
            ),
            {"id": version_id},
        )

    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT status, content_hash, frozen_at, row_version "
                "FROM public.research_question_versions WHERE id=:id"
            ),
            {"id": version_id},
        ).one()
    assert row.status == "SUPERSEDED"
    assert row.content_hash == "a" * 64
    assert row.frozen_at == datetime(2026, 9, 5, tzinfo=UTC)
    assert row.row_version == 2


@pytest.mark.parametrize(
    ("status", "exit_code", "failure_reason"),
    [
        ("SUCCEEDED", None, "must be null"),
        ("CANCELLED", 1, None),
        ("CANCELLED", None, "must be null"),
        ("FAILED", None, None),
    ],
)
def test_run_guard_rejects_illegal_terminal_metadata(
    engine: Engine, status: str, exit_code: int | None, failure_reason: str | None
) -> None:
    run_id = _seed_running_run(engine)
    finished = datetime(2026, 9, 5, 1, tzinfo=UTC)

    def mutate() -> None:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE public.runs SET status=:status, finished_at=:finished, "
                    "exit_code=:exit_code, failure_reason=:failure_reason, "
                    "row_version=2 WHERE id=:id"
                ),
                {
                    "id": run_id,
                    "status": status,
                    "finished": finished,
                    "exit_code": exit_code,
                    "failure_reason": failure_reason,
                },
            )

    _assert_trigger_error(mutate, "P17D2")
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT status, finished_at, exit_code, failure_reason, row_version "
                "FROM public.runs WHERE id=:id"
            ),
            {"id": run_id},
        ).one()
    assert row.status == "RUNNING"
    assert row.finished_at is None
    assert row.exit_code is None
    assert row.failure_reason is None
    assert row.row_version == 1


@pytest.mark.parametrize(
    ("status", "exit_code", "failure_reason"),
    [
        ("SUCCEEDED", 0, None),
        ("FAILED", 1, "failed"),
        ("FAILED", None, "failed without exit code"),
        ("SUCCEEDED", None, None),
        ("CANCELLED", None, None),
    ],
)
def test_run_guard_accepts_legal_terminal_metadata(
    engine: Engine, status: str, exit_code: int | None, failure_reason: str | None
) -> None:
    run_id = _seed_running_run(engine)
    finished = datetime(2026, 9, 5, 1, tzinfo=UTC)

    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE public.runs SET status=:status, finished_at=:finished, "
                "exit_code=:exit_code, failure_reason=:failure_reason, "
                "row_version=2 WHERE id=:id"
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
    assert row.status == status
    assert row.finished_at == finished
    assert row.exit_code == exit_code
    assert row.failure_reason == failure_reason
    assert row.row_version == 2


def test_run_input_attach_and_remove_are_legal_only_before_parent_protection(
    engine: Engine,
) -> None:
    run_id, snapshot_id = _seed_planned_run_with_snapshot(engine)
    values = {"run": run_id, "snapshot": snapshot_id}

    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO public.run_dataset_inputs "
                "(run_id, dataset_snapshot_id, role, ordinal) "
                "VALUES (:run, :snapshot, 'train', 0)"
            ),
            values,
        )
        connection.execute(
            text(
                "DELETE FROM public.run_dataset_inputs "
                "WHERE run_id=:run AND dataset_snapshot_id=:snapshot AND role='train'"
            ),
            values,
        )
        connection.execute(
            text(
                "UPDATE public.runs SET status='RUNNING', inputs_sealed_at=:now, "
                "started_at=:now, row_version=2 WHERE id=:run"
            ),
            {"run": run_id, "now": datetime(2026, 9, 5, 1, tzinfo=UTC)},
        )


def test_run_input_post_protection_insert_is_rejected_and_row_is_absent(engine: Engine) -> None:
    run_id, snapshot_id = _seed_planned_run_with_snapshot(engine)
    now = datetime(2026, 9, 5, 1, tzinfo=UTC)
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE public.runs SET status='RUNNING', inputs_sealed_at=:now, "
                "started_at=:now, row_version=2 WHERE id=:run"
            ),
            {"run": run_id, "now": now},
        )

    def attach() -> None:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO public.run_dataset_inputs "
                    "(run_id, dataset_snapshot_id, role, ordinal) "
                    "VALUES (:run, :snapshot, 'train', 0)"
                ),
                {"run": run_id, "snapshot": snapshot_id},
            )

    _assert_trigger_error(attach, "P17D1")
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM public.run_dataset_inputs WHERE run_id=:run"),
                {"run": run_id},
            ).scalar_one()
            == 0
        )


def test_run_input_update_is_rejected_without_disabling_other_triggers(engine: Engine) -> None:
    run_id, snapshot_id = _seed_planned_run_with_snapshot(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO public.run_dataset_inputs "
                "(run_id, dataset_snapshot_id, role, ordinal) "
                "VALUES (:run, :snapshot, 'train', 0)"
            ),
            {"run": run_id, "snapshot": snapshot_id},
        )

    def mutate() -> None:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE public.run_dataset_inputs SET ordinal=1 "
                    "WHERE run_id=:run AND dataset_snapshot_id=:snapshot AND role='train'"
                ),
                {"run": run_id, "snapshot": snapshot_id},
            )

    _assert_trigger_error(mutate, "P17D1")
    with engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT ordinal FROM public.run_dataset_inputs WHERE run_id=:run "
                    "AND dataset_snapshot_id=:snapshot AND role='train'"
                ),
                {"run": run_id, "snapshot": snapshot_id},
            ).scalar_one()
            == 0
        )


def test_audit_finding_transition_and_material_immutability_are_database_enforced(
    engine: Engine,
) -> None:
    finding_id = _seed_audit_finding(engine)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE public.audit_findings SET status='confirmed', row_version=2 WHERE id=:id"),
            {"id": finding_id},
        )
        connection.execute(
            text("UPDATE public.audit_findings SET status='resolved', row_version=3 WHERE id=:id"),
            {"id": finding_id},
        )

    illegal_id = _seed_audit_finding(engine)

    def illegal_transition() -> None:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE public.audit_findings SET status='resolved', row_version=2 WHERE id=:id"
                ),
                {"id": illegal_id},
            )

    _assert_trigger_error(illegal_transition, "P17D2")

    def illegal_material_update() -> None:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE public.audit_findings SET title='changed', row_version=2 WHERE id=:id"
                ),
                {"id": illegal_id},
            )

    _assert_trigger_error(illegal_material_update, "23514")
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT status, title, row_version FROM public.audit_findings WHERE id=:id"),
            {"id": illegal_id},
        ).one()
    assert (row.status, row.title, row.row_version) == ("open", "finding", 1)


def test_parent_state_lock_race_rejects_child_after_parent_seals(engine: Engine) -> None:
    run_id, snapshot_id = _seed_planned_run_with_snapshot(engine)
    parent_locked = Event()
    child_attempting = Event()
    errors: list[BaseException] = []

    def parent_transaction() -> None:
        try:
            with engine.begin() as connection:
                connection.execute(
                    text("SELECT id FROM public.runs WHERE id=:run FOR UPDATE"),
                    {"run": run_id},
                )
                parent_locked.set()
                assert child_attempting.wait(timeout=5)
                connection.execute(
                    text(
                        "UPDATE public.runs SET status='RUNNING', inputs_sealed_at=:now, "
                        "started_at=:now, row_version=2 WHERE id=:run"
                    ),
                    {"run": run_id, "now": datetime(2026, 9, 5, 1, tzinfo=UTC)},
                )
        except BaseException as exc:
            errors.append(exc)

    child_error: list[BaseException] = []

    def child_transaction() -> None:
        assert parent_locked.wait(timeout=5)
        try:
            with engine.begin() as connection:
                child_attempting.set()
                connection.execute(
                    text(
                        "INSERT INTO public.run_dataset_inputs "
                        "(run_id, dataset_snapshot_id, role, ordinal) "
                        "VALUES (:run, :snapshot, 'train', 0)"
                    ),
                    {"run": run_id, "snapshot": snapshot_id},
                )
        except BaseException as exc:
            child_error.append(exc)

    parent = Thread(target=parent_transaction)
    child = Thread(target=child_transaction)
    parent.start()
    child.start()
    parent.join(timeout=10)
    child.join(timeout=10)
    assert not parent.is_alive()
    assert not child.is_alive()
    assert not errors
    assert child_error
    assert getattr(getattr(child_error[0], "orig", None), "sqlstate", None) == "P17D1"
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT status, row_version FROM public.runs WHERE id=:run"),
            {"run": run_id},
        ).one()
        child_count = connection.execute(
            text("SELECT count(*) FROM public.run_dataset_inputs WHERE run_id=:run"),
            {"run": run_id},
        ).scalar_one()
    assert (row.status, row.row_version, child_count) == ("RUNNING", 2, 0)
