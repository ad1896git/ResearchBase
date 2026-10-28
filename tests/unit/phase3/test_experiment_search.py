"""Bounded S4 command evidence; recordings do not establish S8 race acceptance."""

from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import DBAPIError
from tests.integration.phase2.pr2_20_support import upgrade
from tests.integration.phase3.agent_fixtures import (
    agents as agents,
)
from tests.integration.phase3.agent_fixtures import enrollment
from tests.integration.phase3.conftest import Credentials, PlanningFixture
from tests.integration.phase3.search_fixtures import (
    _search_env as _search_env,
)
from tests.integration.phase3.test_pr3_04_application import approve, bind
from tests.unit.phase3.search_fixtures import (
    LOCK_STAGES,
    NOW,
    WRITE_TABLES,
    Fixture,
    label,
)

from researchbase.agent_runtime.application.experiment_search import ExperimentSearchService
from researchbase.agent_runtime.application.research_task import ResearchTaskService
from researchbase.agent_runtime.application.search_contracts import (
    AppendSearchArguments,
    CreateSearchArguments,
    SearchCommand,
)
from researchbase.agent_runtime.domain.experiment_search import BranchKind, ObjectiveDefinition
from researchbase.agent_runtime.domain.task_safety import ResourceVector
from researchbase.agent_runtime.ports.task_repository import UncertainTaskCommit
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.experiment_search_repository import (
    SqlAlchemyExperimentSearchRepository,
)
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

WRITE_STAGES = (
    "update:research_tasks",
    *("insert:" + table for table in WRITE_TABLES),
    "flush",
    "constraints",
    "final",
)
ALL_STAGES = tuple(label(s) for s in LOCK_STAGES) + WRITE_STAGES


@pytest.mark.parametrize("kind", ["HUMAN", "AGENT"])
@pytest.mark.parametrize("status", ["CREATED", "PLANNING"])
def test_create_session_has_one_receipt_and_no_execution(kind, status):
    f = Fixture()
    f.actor_type, f.role = kind, "RESEARCHER"
    f.task_row["status"] = status
    before = deepcopy(f.tables)
    objective = f.task_row["objective"]
    command = f.command()
    result = f.run(command)
    assert result.session_id == command.arguments.session_id
    assert result.node_id is None and not result.command_result.replayed
    assert result.command_result.task_id == f.task
    assert result.command_result.resulting_row_version == f.task_row["row_version"] == 2
    assert len(result.command_result.task_event_ids) == 1
    assert result.command_result.step_event_ids == ()
    assert f.commands == f.commits == 1 and f.rollbacks == 0
    assert f.task_row["objective"] == objective
    assert ObjectiveDefinition(f.task, objective).projection()["text"] == objective
    for table, rows in f.tables.items():
        assert len(rows) - len(before[table]) == int(table in WRITE_TABLES)
    session = f.tables["experiment_search_sessions"][0]
    assert session["budget_id"] == f.task_row["budget_policy_id"]
    assert session["research_task_id"] == f.task and session["project_id"] == f.project
    assert "objective" not in session and "objective_definition" not in session
    event = f.tables["experiment_search_events"][0]
    assert event["event_type"] == "SESSION_CREATED" and event["sequence"] == 1
    assert event["id"] == result.search_event_id and event["node_id"] is None
    receipt = f.tables["research_task_command_receipts"][0]
    assert receipt["request_hash"] == command.request_hash(f.actor)
    assert receipt["material_version"] == 1 and receipt["result_search_node_id"] is None
    assert receipt["completed_at"] == session["created_at"] == event["occurred_at"] == NOW
    assert (
        ("stage", "actor_key") in f.trace
        if kind == "AGENT"
        else ("stage", "actor_key") not in f.trace
    )
    assert [table for table, _ in f.writes] == ["update", *WRITE_TABLES]


@pytest.mark.parametrize("stage_name", ALL_STAGES)
@pytest.mark.parametrize("outcome", ["replay", "conflict", "revoked"])
def test_current_entitlement_and_saved_replay_precede_cas_after_every_wait(stage_name, outcome):
    f = Fixture()
    command = f.command()
    result = f.run(command)
    receipt = deepcopy(f.tables["research_task_command_receipts"][0])
    # Use a fresh attempt so every lock, DML, flush and constraints callback is
    # reached. A committed receipt becomes visible exactly at the selected stage.
    f.task_row["row_version"] = 1
    for table in WRITE_TABLES:
        f.tables[table].clear()
    f.trace.clear()
    f.writes.clear()
    f.replay_result = replace(result.command_result, replayed=True)
    reached = []

    def hook(stage):
        if label(stage) == stage_name and not reached:
            reached.append(True)
            f.replay_receipt = receipt
            f.task_row["row_version"] = 999
            f.task_row["status"] = "CANCELLED"
            f.active = False
            f.role = "VIEWER"
            if outcome == "conflict":
                receipt["request_hash"] = "f" * 64
            if outcome == "revoked":
                f.valid = False

    f.hook = hook
    if outcome == "replay":
        replay = f.run(command)
        assert replay == replace(result, command_result=f.replay_result)
    else:
        with pytest.raises(ResearchBaseError) as error:
            f.run(command)
        assert error.value.code == (
            ErrorCode.FORBIDDEN if outcome == "revoked" else ErrorCode.IDEMPOTENCY_CONFLICT
        )
    assert reached and f.commits == 1
    index = f.trace.index(("stage", stage_name))
    after = f.trace[index + 1 :]
    assert "credential" in after
    if outcome == "revoked":
        assert "committed_receipt" not in after
    else:
        assert after.index("credential") < after.index("committed_receipt")
        assert "task_read" not in after
    # Effects executed before the newly visible replay/denial are rolled back.
    assert f.task_row["row_version"] == 1
    assert all(not f.tables[table] for table in WRITE_TABLES)


@pytest.mark.parametrize("stage_name", WRITE_STAGES)
@pytest.mark.parametrize("failure", ["storage", "credential"])
def test_rollback_at_each_write_and_constraint_stage(stage_name, failure):
    f = Fixture()
    before = deepcopy((f.task_row, f.tables))
    if failure == "storage":
        f.fail_stage = stage_name
        expected = RuntimeError
    else:
        f.hook = lambda stage: setattr(f, "valid", False) if label(stage) == stage_name else None
        expected = ResearchBaseError
    with pytest.raises(expected):
        f.run()
    assert (f.task_row, f.tables) == before
    assert f.commits == 0 and f.rollbacks == 1 and f.open_uows == 0


@pytest.mark.parametrize("kind", ["HUMAN", "AGENT"])
def test_append_denied_without_d1_and_without_effects(kind):
    f = Fixture()
    f.actor_type = kind
    before = deepcopy((f.task_row, f.tables))
    args = AppendSearchArguments(
        new_uuid7(), new_uuid7(), BranchKind.BASELINE, "Candidate intent", new_uuid7()
    )
    command = f.command(command_name="append_search_node", arguments=args)
    with pytest.raises(ResearchBaseError) as error:
        f.service.append_search_node(f.principal, command)
    assert error.value.code == ErrorCode.INVALID_STATE_TRANSITION
    assert error.value.message == "Search state unavailable." and error.value.details is None
    assert (f.task_row, f.tables) == before
    assert f.commands == f.commits == f.open_uows == 0 and f.writes == [] and f.trace == []


@pytest.mark.parametrize(
    "verifier",
    [None, object(), SimpleNamespace(is_valid=False), SimpleNamespace(is_valid=lambda *args: 1)],
)
def test_absent_or_unsupported_verifier_denies(verifier):
    f = Fixture()
    f.service = ExperimentSearchService(f.factory, verifier)
    with pytest.raises(ResearchBaseError) as error:
        f.run()
    assert error.value.code == ErrorCode.FORBIDDEN
    assert f.writes == [] and f.commits == 0


def test_async_and_raising_verifiers_deny():
    async def asynchronous(*args):
        return True

    def unavailable(*args):
        raise OSError("credential unavailable")

    for method in (asynchronous, unavailable):
        f = Fixture()
        f.service = ExperimentSearchService(f.factory, SimpleNamespace(is_valid=method))
        with pytest.raises(ResearchBaseError) as error:
            f.run()
        assert error.value.code == ErrorCode.FORBIDDEN
        assert f.writes == []


def test_stable_exact_result_replay_conflict_and_current_authority():
    f = Fixture()
    command = f.command()
    result = f.run(command)
    saved = deepcopy((f.task_row, f.tables))
    f.writes.clear()
    f.role = "VIEWER"
    f.active = False
    replay = f.run(command)
    assert replay == replace(result, command_result=replace(result.command_result, replayed=True))
    assert f.writes == [] and (f.task_row, f.tables) == saved
    conflicting = replace(command, expected_row_version=2)
    with pytest.raises(ResearchBaseError) as error:
        f.run(conflicting)
    assert error.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    f.valid = False
    with pytest.raises(ResearchBaseError) as error:
        f.run(command)
    assert error.value.code == ErrorCode.FORBIDDEN
    assert f.writes == [] and (f.task_row, f.tables) == saved


@pytest.mark.parametrize(
    "control",
    [
        "cas",
        "scope",
        "project",
        "absent",
        "state",
        "write",
        "credential",
        "future_credential",
        "checkpoint",
        "stop",
        "autonomy",
        "policy_hash",
        "policy_missing",
    ],
)
def test_fresh_create_denies_invalid_admission_without_effects(control):
    f = Fixture()
    command = f.command()
    expected = ErrorCode.INVALID_STATE_TRANSITION
    if control == "cas":
        f.task_row["row_version"] = 2
        expected = ErrorCode.CONCURRENT_MODIFICATION
    elif control == "scope":
        f.task_row["project_id"] = new_uuid7()
        expected = ErrorCode.FORBIDDEN
    elif control == "project":
        command = replace(command, project_id=new_uuid7())
        expected = ErrorCode.FORBIDDEN
    elif control == "absent":
        command = replace(command, task_id=new_uuid7())
        expected = ErrorCode.NOT_FOUND
    elif control == "state":
        f.task_row["status"] = "CANCELLED"
    elif control == "write":
        f.role = "VIEWER"
        expected = ErrorCode.FORBIDDEN
    elif control == "credential":
        f.valid = False
        expected = ErrorCode.FORBIDDEN
    elif control == "future_credential":
        f.principal = replace(f.principal, verified_at=NOW + timedelta(seconds=1))
        expected = ErrorCode.FORBIDDEN
    elif control == "checkpoint":
        f.tables["human_checkpoints"][0]["status"] = "REJECTED"
    elif control == "stop":
        f.tables["research_task_events"].append(dict(command_id=new_uuid7(), stop_human=True))
    elif control == "autonomy":
        f.task_row["autonomy_level"] = "A3"
    elif control == "policy_hash":
        f.tables["execution_budgets"][0]["content_hash"] = "f" * 64
        expected = ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    elif control == "policy_missing":
        f.task_row["budget_policy_id"] = new_uuid7()
    before = deepcopy((f.task_row, f.tables))
    with pytest.raises(ResearchBaseError) as error:
        f.run(command)
    assert error.value.code == expected
    assert (f.task_row, f.tables) == before and f.writes == []


@pytest.mark.parametrize("hypothesis", [True, False])
@pytest.mark.parametrize("control", ["valid", "absent", "scope", "draft", "hash", "owner"])
def test_exact_owning_references(hypothesis, control):
    f = Fixture()
    identity = new_uuid7()
    row = dict(
        id=identity, project_id=f.project, status="FROZEN", frozen_at=NOW, content_hash="a" * 64
    )
    f.references[identity] = row
    f.owners[identity] = SimpleNamespace(content_hash="a" * 64)
    args = CreateSearchArguments(
        new_uuid7(), identity if hypothesis else None, None if hypothesis else identity
    )
    command = f.command(arguments=args)
    expected = None
    if control == "absent":
        f.references.clear()
        expected = ErrorCode.NOT_FOUND
    elif control == "scope":
        row["project_id"] = new_uuid7()
        expected = ErrorCode.FORBIDDEN
    elif control == "draft":
        row["status"] = "DRAFT"
        expected = ErrorCode.VERSION_NOT_FROZEN
    elif control == "hash":
        row["content_hash"] = "b" * 64
        expected = ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    elif control == "owner":
        f.owners.clear()
        expected = ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    if expected:
        with pytest.raises(ResearchBaseError) as error:
            f.run(command)
        assert error.value.code == expected and f.writes == []
    else:
        f.run(command)
        col = "root_hypothesis_content_hash" if hypothesis else "root_experiment_spec_content_hash"
        assert f.tables["experiment_search_sessions"][0][col] == "a" * 64


@pytest.mark.parametrize(
    ("control", "expected"),
    [
        ("absent", ErrorCode.NOT_FOUND),
        ("draft", ErrorCode.VERSION_NOT_FROZEN),
        ("hash", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
    ],
)
def test_fresh_reference_errors_precede_terminal_task(control, expected):
    f = Fixture()
    f.task_row["status"] = "CANCELLED"
    identity = new_uuid7()
    if control != "absent":
        f.references[identity] = dict(
            id=identity,
            project_id=f.project,
            status="DRAFT" if control == "draft" else "FROZEN",
            frozen_at=NOW,
            content_hash="a" * 64,
        )
        f.owners[identity] = SimpleNamespace(content_hash="b" * 64)
    command = f.command(arguments=CreateSearchArguments(new_uuid7(), identity, None))
    before = deepcopy((f.task_row, f.tables))
    with pytest.raises(ResearchBaseError) as error:
        f.run(command)
    assert error.value.code == expected
    assert (f.task_row, f.tables) == before and f.writes == []


def test_committed_replay_precedes_terminal_task_and_missing_reference():
    f = Fixture()
    identity = new_uuid7()
    f.references[identity] = dict(
        id=identity, project_id=f.project, status="FROZEN", frozen_at=NOW, content_hash="a" * 64
    )
    f.owners[identity] = SimpleNamespace(content_hash="a" * 64)
    command = f.command(arguments=CreateSearchArguments(new_uuid7(), identity, None))
    result = f.run(command)
    f.task_row["status"] = "CANCELLED"
    f.references.clear()
    f.writes.clear()
    before = deepcopy((f.task_row, f.tables))
    assert f.run(command) == replace(
        result, command_result=replace(result.command_result, replayed=True)
    )
    assert (f.task_row, f.tables) == before and f.writes == []


@pytest.mark.parametrize("kind", ["HUMAN", "AGENT"])
@pytest.mark.parametrize(
    ("stale", "hypothesis", "spec", "lower_failure", "expected"),
    [
        (True, "absent", "valid", None, ErrorCode.NOT_FOUND),
        (True, "foreign", "valid", None, ErrorCode.FORBIDDEN),
        (True, "valid", "absent", None, ErrorCode.NOT_FOUND),
        (True, "valid", "foreign", None, ErrorCode.FORBIDDEN),
        (False, "draft", "absent", None, ErrorCode.NOT_FOUND),
        (False, "draft", "foreign", None, ErrorCode.FORBIDDEN),
        (False, "hash", "draft", None, ErrorCode.VERSION_NOT_FROZEN),
        (True, "valid", "valid", None, ErrorCode.CONCURRENT_MODIFICATION),
        (True, "draft", "hash", None, ErrorCode.CONCURRENT_MODIFICATION),
        (False, "valid", "absent", "lifecycle", ErrorCode.NOT_FOUND),
        (False, "foreign", "valid", "safety", ErrorCode.FORBIDDEN),
        (False, "valid", "draft", "lifecycle", ErrorCode.VERSION_NOT_FROZEN),
        (False, "draft", "hash", "safety", ErrorCode.VERSION_NOT_FROZEN),
        (False, "hash", "valid", "lifecycle", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        (False, "valid", "hash", "safety", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        (False, "valid", "valid", "lifecycle", ErrorCode.INVALID_STATE_TRANSITION),
        (False, "valid", "valid", "safety", ErrorCode.INVALID_STATE_TRANSITION),
    ],
)
def test_fresh_validation_precedence_matrix(kind, stale, hypothesis, spec, lower_failure, expected):
    f = Fixture()
    f.actor_type = kind
    identities = (new_uuid7(), new_uuid7())
    for identity, control in zip(identities, (hypothesis, spec), strict=True):
        if control != "absent":
            f.references[identity] = dict(
                id=identity,
                project_id=new_uuid7() if control == "foreign" else f.project,
                status="DRAFT" if control == "draft" else "FROZEN",
                frozen_at=NOW,
                content_hash="a" * 64,
            )
            f.owners[identity] = SimpleNamespace(
                content_hash=("b" if control == "hash" else "a") * 64
            )
    f.task_row["row_version"] += int(stale)
    if lower_failure == "lifecycle":
        f.task_row["status"] = "CANCELLED"
    elif lower_failure == "safety":
        f.tables["human_checkpoints"][0]["status"] = "REJECTED"
    command = f.command(arguments=CreateSearchArguments(new_uuid7(), *identities))
    before = deepcopy((f.task_row, f.tables))
    with pytest.raises(ResearchBaseError) as exc:
        f.run(command)
    assert exc.value.code == expected and exc.value.details is None
    assert (f.task_row, f.tables) == before
    assert f.writes == [] and f.commits == 0 and f.rollbacks == 1
    assert [entry for entry in f.trace if isinstance(entry, tuple) and entry[0] == "stage"] == [
        ("stage", "share")
    ]


@pytest.mark.parametrize("stage_name", ["task_row", "insert:experiment_search_sessions", "final"])
@pytest.mark.parametrize(
    ("stale", "hypothesis", "spec", "expected"),
    [
        (True, "valid", "absent", ErrorCode.NOT_FOUND),
        (True, "valid", "foreign", ErrorCode.FORBIDDEN),
        (False, "draft", "absent", ErrorCode.NOT_FOUND),
        (False, "draft", "foreign", ErrorCode.FORBIDDEN),
        (False, "hash", "draft", ErrorCode.VERSION_NOT_FROZEN),
        (True, "valid", "valid", ErrorCode.CONCURRENT_MODIFICATION),
    ],
)
def test_fresh_precedence_rechecked_at_callbacks(stage_name, stale, hypothesis, spec, expected):
    f = Fixture()
    identities = (new_uuid7(), new_uuid7())
    for identity in identities:
        f.references[identity] = dict(
            id=identity, project_id=f.project, status="FROZEN", frozen_at=NOW, content_hash="a" * 64
        )
        f.owners[identity] = SimpleNamespace(content_hash="a" * 64)
    command = f.command(arguments=CreateSearchArguments(new_uuid7(), *identities))
    before = deepcopy((f.task_row, f.tables))
    reached = []

    def change(stage):
        if label(stage) != stage_name:
            return
        reached.append(len(f.writes))
        f.task_row["row_version"] += 10 * int(stale)
        for identity, control in zip(identities, (hypothesis, spec), strict=True):
            if control == "absent":
                del f.references[identity]
            elif control == "foreign":
                f.references[identity]["project_id"] = new_uuid7()
            elif control == "draft":
                f.references[identity]["status"] = "DRAFT"
            elif control == "hash":
                f.owners[identity].content_hash = "b" * 64

    f.hook = change
    with pytest.raises(ResearchBaseError) as exc:
        f.run(command)
    assert exc.value.code == expected and exc.value.details is None
    assert reached == [len(f.writes)]  # No effects after the failing callback.
    assert (f.task_row, f.tables) == before and f.commits == 0 and f.rollbacks == 1


@pytest.mark.parametrize("kind", ["HUMAN", "AGENT"])
@pytest.mark.parametrize("outcome", ["replay", "conflict", "revoked"])
def test_replay_priority_ignores_mutable_references_cas_and_lifecycle(kind, outcome):
    f = Fixture()
    f.actor_type = kind
    identities = (new_uuid7(), new_uuid7())
    for identity in identities:
        f.references[identity] = dict(
            id=identity, project_id=f.project, status="FROZEN", frozen_at=NOW, content_hash="a" * 64
        )
        f.owners[identity] = SimpleNamespace(content_hash="a" * 64)
    command = f.command(arguments=CreateSearchArguments(new_uuid7(), *identities))
    result = f.run(command)
    f.references.clear()
    f.owners.clear()
    f.task_row.update(status="CANCELLED", row_version=999)
    f.tables["human_checkpoints"][0]["status"] = "REJECTED"
    f.role, f.active = "VIEWER", False
    f.valid = outcome != "revoked"
    f.writes.clear()
    f.trace.clear()
    before = deepcopy((f.task_row, f.tables))
    if outcome == "conflict":
        command = replace(command, expected_row_version=2)
    if outcome == "replay":
        assert f.run(command) == replace(
            result, command_result=replace(result.command_result, replayed=True)
        )
    else:
        with pytest.raises(ResearchBaseError) as exc:
            f.run(command)
        assert exc.value.code == (
            ErrorCode.FORBIDDEN if outcome == "revoked" else ErrorCode.IDEMPOTENCY_CONFLICT
        )
        assert exc.value.details is None
    assert "task_read" not in f.trace
    assert (f.task_row, f.tables) == before and f.writes == [] and f.commits == 1


def test_own_effect_callbacks_keep_post_revision_and_never_replay_own_receipt():
    f = Fixture()
    observed = []

    def hook(stage):
        if stage.operation in {"insert", "update", "flush", "constraints", "final"}:
            observed.append((label(stage), f.task_row["row_version"]))

    f.hook = hook
    result = f.run()
    assert not result.command_result.replayed
    assert observed and all(revision == 2 for _, revision in observed)
    assert sum(name == "constraints" for name, _ in observed) == 2
    assert observed[-1] == ("final", 2) and f.commits == 1


@pytest.mark.parametrize("operation", ["flush", "constraints"])
@pytest.mark.parametrize("failure", ["storage", "credential"])
def test_uow_repeated_precommit_stages_roll_back(operation, failure):
    f = Fixture()
    before = deepcopy((f.task_row, f.tables))
    visits = []

    def hook(stage):
        if stage.operation == operation:
            visits.append(True)
            if len(visits) == 2:
                if failure == "storage":
                    raise RuntimeError("precommit storage failure")
                f.valid = False

    f.hook = hook
    with pytest.raises(RuntimeError if failure == "storage" else ResearchBaseError):
        f.run()
    assert len(visits) == 2 and f.commits == 0 and f.rollbacks == 1
    assert (f.task_row, f.tables) == before


@pytest.mark.parametrize("stage", ["share", "insert:experiment_search_sessions", "constraints"])
def test_authority_cas_and_reference_changes_after_stages_rollback(stage):
    f = Fixture()
    before = deepcopy((f.task_row, f.tables))
    f.hook = lambda current: f.task_row.update(row_version=99) if label(current) == stage else None
    with pytest.raises(ResearchBaseError) as error:
        f.run()
    assert error.value.code == ErrorCode.CONCURRENT_MODIFICATION
    assert (f.task_row, f.tables) == before and f.commits == 0


@pytest.mark.parametrize("outcome", ["committed", "rolled_back"])
def test_uncertain_commit_recovers_original_ids(outcome):
    f = Fixture()
    f.uncertain = outcome
    command = f.command()
    if outcome == "committed":
        result = f.run(command)
        assert result.command_result.replayed
        assert result.session_id == command.arguments.session_id
        assert result.search_event_id == f.tables["experiment_search_events"][0]["id"]
        assert result.command_result.task_event_ids == (f.tables["research_task_events"][0]["id"],)
        assert f.commits == 1 and f.task_row["row_version"] == 2
    else:
        before = deepcopy((f.task_row, f.tables))
        with pytest.raises(UncertainTaskCommit):
            f.run(command)
        assert (f.task_row, f.tables) == before
    assert f.commands == 1 and f.trace.count("read_begin") == 1


def test_bounded_transient_retry_keeps_generated_ids_and_timeout_never_retries():
    f = Fixture()
    f.retry_stage = "constraints"
    result = f.run()
    receipts = [row for table, row in f.writes if table == "research_task_command_receipts"]
    assert f.commands == 2 and f.commits == 1 and f.rollbacks == 1
    assert len(receipts) == 2 and receipts[0] == receipts[1]
    assert result.search_event_id == receipts[0]["result_search_event_id"]
    f = Fixture()
    attempts = []

    def retry(stage):
        if stage.operation == "share":
            attempts.append(True)
            raise ResearchBaseError(
                ErrorCode.CONCURRENT_MODIFICATION, "deadlock", {"retryable_pr301": True}
            )

    f.hook = retry
    with pytest.raises(ResearchBaseError):
        f.run()
    assert len(attempts) == f.commands == f.rollbacks == 3
    f = Fixture()
    f.fail_stage = "share"
    with pytest.raises(RuntimeError):
        f.run()
    assert f.commands == 1 and f.writes == []


def test_actor_kind_is_resolved_after_share_without_preliminary_sql():
    from tests.unit.phase3.test_experiment_search_repository import RecordingSession, repository

    session = RecordingSession()
    repo = repository(session)
    events = []

    def source():
        assert events == ["share"]
        assert len(session.trace) == 1
        return "AGENT"

    repo.lock_write(
        new_uuid7(),
        new_uuid7(),
        new_uuid7(),
        new_uuid7(),
        caller_kind=source,
        after_stage=lambda stage: events.append(stage.operation),
    )
    assert events[:5] == ["share", "project", "command_key", "task_key", "actor_key"]


def test_agent_revocation_after_actor_key_denies_without_effects():
    f = Fixture()
    f.actor_type, f.role = "AGENT", "RESEARCHER"
    f.hook = lambda stage: setattr(f, "valid", False) if stage.operation == "actor_key" else None
    with pytest.raises(ResearchBaseError) as error:
        f.run()
    assert error.value.code == ErrorCode.FORBIDDEN
    assert ("stage", "actor_key") in f.trace and f.writes == []


def test_reference_changes_after_own_session_insert_roll_back():
    f = Fixture()
    identity = new_uuid7()
    f.references[identity] = dict(
        id=identity, project_id=f.project, status="FROZEN", frozen_at=NOW, content_hash="a" * 64
    )
    f.owners[identity] = SimpleNamespace(content_hash="a" * 64)
    command = f.command(arguments=CreateSearchArguments(new_uuid7(), identity))
    before = deepcopy((f.task_row, f.tables))

    def change(stage):
        if label(stage) == "insert:experiment_search_sessions":
            f.references[identity]["content_hash"] = "b" * 64
            f.owners[identity].content_hash = "b" * 64

    f.hook = change
    with pytest.raises(ResearchBaseError) as error:
        f.run(command)
    assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert (f.task_row, f.tables) == before and f.commits == 0


@pytest.mark.parametrize("control", ["cap", "zero_cap", "wall", "failure", "no_improvement"])
def test_existing_accounting_stops_session_creation_without_budget_effects(control):
    from dataclasses import asdict

    f = Fixture()
    reservation: dict[str, Any] = dict(
        id=new_uuid7(), created_at=NOW, **asdict(ResourceVector.zero())
    )
    if control == "cap":
        reservation["tree_nodes"] = 10
    elif control == "zero_cap":
        reservation["gpu_hours"] = Decimal("0.000001")
    elif control == "wall":
        reservation["created_at"] = NOW - timedelta(seconds=1800)
    else:
        f.tables["budget_usage_records"].append(
            dict(
                reservation_id=reservation["id"],
                is_final=True,
                failure_streak=2 if control == "failure" else 0,
                no_improvement_streak=5 if control == "no_improvement" else 0,
                **asdict(ResourceVector.zero()),
            )
        )
    f.tables["budget_reservations"].append(reservation)
    before = deepcopy((f.task_row, f.tables))
    with pytest.raises(ResearchBaseError) as error:
        f.run()
    assert error.value.code == ErrorCode.INVALID_STATE_TRANSITION
    assert (f.task_row, f.tables) == before and f.writes == []


def test_unverified_principal_never_opens_a_transaction():
    f = Fixture()
    with pytest.raises(ResearchBaseError) as error:
        f.service.create_search_session(object(), f.command())
    assert error.value.code == ErrorCode.AUTHENTICATION_REQUIRED
    assert f.commands == 0 and f.trace == []


@pytest.mark.parametrize(
    "name,code",
    [
        ("preheld", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        ("scope", ErrorCode.FORBIDDEN),
        ("state", ErrorCode.INVALID_STATE_TRANSITION),
        ("not_frozen", ErrorCode.VERSION_NOT_FROZEN),
        ("provenance", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        ("completeness", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        ("reference", ErrorCode.REFERENTIAL_INTEGRITY_ERROR),
        ("immutable", ErrorCode.IMMUTABLE_RECORD),
        ("activation", ErrorCode.INVALID_STATE_TRANSITION),
        ("validation", ErrorCode.VALIDATION_ERROR),
    ],
)
def test_search_guard_normalization_is_scoped_to_search_uow(name, code):
    uow = SqlAlchemyUnitOfWork(cast(Any, lambda: None))
    uow._research_task_error_normalization = True
    original = Exception("private SQL and foreign identities")
    cast(Any, original).sqlstate = "23514"
    cast(Any, original).diag = SimpleNamespace(constraint_name="pr316_" + name)
    database_error = DBAPIError("private SQL", {}, original)
    uow._search_command = True
    normalized = uow._command_database_error(database_error)
    assert normalized.code == code and "private" not in normalized.message
    assert normalized.details is not None and not normalized.details["retryable_pr301"]
    uow._search_command = False
    assert uow._command_database_error(database_error).code == ErrorCode.VALIDATION_ERROR


def test_occupied_session_identity_is_denied_without_effects():
    f = Fixture()
    first = f.command()
    f.run(first)
    before = deepcopy((f.task_row, f.tables))
    f.writes.clear()
    with pytest.raises(ResearchBaseError) as error:
        f.run(f.command(expected_row_version=2, arguments=first.arguments))
    assert error.value.code == ErrorCode.VALIDATION_ERROR
    assert (f.task_row, f.tables) == before and f.writes == []


def pg_command(env):
    with env.engine.connect() as conn:
        revision = conn.execute(
            text("SELECT row_version FROM research_tasks WHERE id=:id"), {"id": env.task}
        ).scalar_one()
    return SearchCommand(
        env.p.project,
        new_uuid7(),
        env.task,
        revision,
        "create_search_session",
        CreateSearchArguments(new_uuid7()),
    )


@pytest.mark.integration
def test_postgres_session_create_replay_and_exact_guarded_effects(search_env):
    env = search_env
    command = pg_command(env)
    service = ExperimentSearchService(env.p.factory, Credentials())
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(env.engine, "before_cursor_execute", record)
    try:
        result = service.create_search_session(env.p.principal, command)
    finally:
        event.remove(env.engine, "before_cursor_execute", record)
    assert statements[0].startswith("LOCK TABLE actor_subject_bindings,")
    assert not any("agent_versions" in sql or "agent_availability" in sql for sql in statements)
    assert sum(sql.startswith("UPDATE research_tasks") for sql in statements) == 1
    assert sum(sql.startswith("INSERT INTO ") for sql in statements) == 5
    statements.clear()
    event.listen(env.engine, "before_cursor_execute", record)
    try:
        replay = service.create_search_session(env.p.principal, command)
    finally:
        event.remove(env.engine, "before_cursor_execute", record)
    assert replay == replace(result, command_result=replace(result.command_result, replayed=True))
    assert not any(sql.startswith(("INSERT", "UPDATE", "DELETE")) for sql in statements)
    with env.engine.connect() as conn:
        receipt = (
            conn.execute(
                text("SELECT * FROM research_task_command_receipts WHERE command_id=:id"),
                {"id": command.command_id},
            )
            .mappings()
            .one()
        )
        session = (
            conn.execute(
                text("SELECT * FROM experiment_search_sessions WHERE id=:id"),
                {"id": result.session_id},
            )
            .mappings()
            .one()
        )
        search = (
            conn.execute(
                text("SELECT * FROM experiment_search_events WHERE receipt_id=:id"),
                {"id": receipt["id"]},
            )
            .mappings()
            .one()
        )
        task_event = (
            conn.execute(
                text(
                    "SELECT e.* FROM research_task_receipt_events l "
                    "JOIN research_task_events e ON e.id=l.event_id "
                    "WHERE l.receipt_id=:id"
                ),
                {"id": receipt["id"]},
            )
            .mappings()
            .one()
        )
        assert task_event["id"] == result.command_result.task_event_ids[0]
        assert task_event["task_row_version"] == command.expected_row_version + 1
        assert search["id"] == result.search_event_id and search["sequence"] == 1
        assert session["receipt_id"] == search["receipt_id"] == receipt["id"]
        assert receipt["request_hash"] == command.request_hash(env.p.principal.actor_id)
        assert receipt["completed_at"] == session["created_at"] == search["occurred_at"]
        assert (
            conn.execute(
                text("SELECT count(*) FROM experiment_search_nodes WHERE search_session_id=:id"),
                {"id": result.session_id},
            ).scalar_one()
            == 0
        )
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM experiment_search_node_runs WHERE search_session_id=:id"
                ),
                {"id": result.session_id},
            ).scalar_one()
            == 0
        )


@pytest.mark.integration
def test_postgres_constraint_failure_rolls_back_all_effects(search_env, monkeypatch):
    env = search_env
    command = pg_command(env)
    original = SqlAlchemyExperimentSearchRepository.insert

    def corrupt(repo, table, row):
        if table == "research_task_command_receipts":
            row = {**row, "request_hash": "f" * 64}
        original(repo, table, row)

    monkeypatch.setattr(SqlAlchemyExperimentSearchRepository, "insert", corrupt)
    with pytest.raises(ResearchBaseError) as error:
        ExperimentSearchService(env.p.factory, Credentials()).create_search_session(
            env.p.principal, command
        )
    assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    with env.engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT row_version FROM research_tasks WHERE id=:id"), {"id": env.task}
            ).scalar_one()
            == command.expected_row_version
        )
        assert (
            conn.execute(
                text("SELECT count(*) FROM research_task_command_receipts WHERE command_id=:id"),
                {"id": command.command_id},
            ).scalar_one()
            == 0
        )

        assert (
            conn.execute(
                text("SELECT count(*) FROM experiment_search_sessions WHERE id=:id"),
                {"id": command.arguments.session_id},
            ).scalar_one()
            == 0
        )
        assert (
            conn.execute(
                text("SELECT count(*) FROM experiment_search_events WHERE search_session_id=:id"),
                {"id": command.arguments.session_id},
            ).scalar_one()
            == 0
        )
        assert (
            conn.execute(
                text("SELECT count(*) FROM research_task_events WHERE command_id=:id"),
                {"id": command.command_id},
            ).scalar_one()
            == 0
        )


@pytest.mark.integration
def test_postgres_verified_agent_creates_session_without_version_or_execution(request):
    env = request.getfixturevalue("agents")
    enrolled = enrollment(env)
    env.service.execute(enrolled)
    principal = env.identity.resolve_agent_subject(enrolled.arguments.subject)
    upgrade(env.url, "0082_experiment_search_core")
    with env.engine.connect() as conn:
        role = conn.execute(text("SELECT current_user")).scalar_one()
    admin = create_engine(env.url)
    try:
        with admin.begin() as conn:
            # The reused Agent fixture predates 0080..0082; their preservation
            # guards read the added tables while executing ordinary task commands.
            conn.execute(text(f'GRANT SELECT ON ALL TABLES IN SCHEMA public TO "{role}"'))
            conn.execute(
                text(
                    "GRANT SELECT,INSERT ON experiment_search_sessions,"
                    "experiment_search_events,experiment_search_nodes,"
                    f'experiment_search_node_runs TO "{role}"'
                )
            )
        p = PlanningFixture(
            env.engine,
            env.factory,
            ResearchTaskService(env.factory, Credentials(), env.store),
            env.owner,
            env.project,
            env.url,
            env.store,
        )
        task = p.create()
        bind(p, task)
        approve(p, task, 2)
        # create=1, bind=2, request checkpoint=3, approve=4.
        command = SearchCommand(
            env.project,
            new_uuid7(),
            task,
            4,
            "create_search_session",
            CreateSearchArguments(new_uuid7()),
        )
        result = ExperimentSearchService(env.factory, Credentials()).create_search_session(
            principal, command
        )
        assert result.session_id == command.arguments.session_id
        assert result.command_result.resulting_row_version == 5
        with env.engine.connect() as conn:
            assert (
                conn.execute(
                    text("SELECT created_by FROM experiment_search_sessions WHERE id=:id"),
                    {"id": result.session_id},
                ).scalar_one()
                == principal.actor_id
            )
            assert (
                conn.execute(
                    text("SELECT count(*) FROM agent_versions WHERE actor_id=:id"),
                    {"id": principal.actor_id},
                ).scalar_one()
                == 0
            )
            assert (
                conn.execute(
                    text(
                        "SELECT count(*) FROM agent_execution_instances WHERE research_task_id=:id"
                    ),
                    {"id": task},
                ).scalar_one()
                == 0
            )
    finally:
        admin.dispose()
