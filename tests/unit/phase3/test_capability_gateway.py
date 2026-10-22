"""S4 transaction, admission, accounting and replay evidence with recording UoWs."""

import json
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import timedelta
from decimal import Decimal

import pytest
from tests.unit.phase3.gateway_fixtures import Fixture

from researchbase.agent_runtime.application.capability_gateway import FAKE_RESOURCES
from researchbase.agent_runtime.application.safety_contracts import BudgetSpec, policy_hash
from researchbase.agent_runtime.application.task_safety import TaskSafetyService
from researchbase.agent_runtime.ports.task_safety_repository import FakeConsumerCapability
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7


def denied(f, code, *, register=False, command=None, context=None):
    before = deepcopy((f.task_row, f.tables))
    with pytest.raises(ResearchBaseError) as error:
        f.run(command, register=register, context=context)
    assert error.value.code == code
    assert (f.task_row, f.tables) == before
    return error.value


def test_registration_one_transaction_no_reservation_and_complete_policy():
    f = Fixture()
    result = f.run(register=True)
    assert not result.replayed and result.policy_id == f.policy_id
    assert result.invocation_id is result.reservation_id is None
    assert f.command_transactions == f.commits == 1
    assert len(f.tables["research_task_command_receipts"]) == 1
    assert len(f.tables["agent_tool_policies"]) == 1
    assert len(f.tables["agent_tool_policy_permissions"]) == 1
    assert not f.tables["budget_reservations"]
    assert len([w for w in f.attempt_writes if w[0] == "task"]) == 1


def test_request_atomic_effects_exact_vector_refs_and_no_nested_safety(monkeypatch, tmp_path):
    f = Fixture()
    f.install_policy()

    def forbidden(*args, **kwargs):
        raise AssertionError("nested safety command")

    monkeypatch.setattr(TaskSafetyService, "execute", forbidden)
    result = f.run()
    assert f.command_transactions == f.commits == 1
    assert len(f.tables["research_task_command_receipts"]) == 2  # one registration, one request
    assert len(f.tables["budget_reservations"]) == len(f.tables["capability_invocations"]) == 1
    assert len([w for w in f.attempt_writes if w[0] == "task"]) == 1
    reservation = f.tables["budget_reservations"][0]
    assert {k: reservation[k] for k in asdict(FAKE_RESOURCES)} == asdict(FAKE_RESOURCES)
    assert reservation["operation_id"] == f.args.invocation_id
    assert reservation["observed_depth"] == 0 and reservation["observed_parallel_branches"] == 1
    ref = f.tables["capability_invocation_refs"][0]
    assert ref["research_question_version_id"] == f.ref_id and ref["content_hash"] == f.ref_hash
    assert ref["receipt_id"] == result.receipt_id
    for table, time in (
        ("research_task_command_receipts", "completed_at"),
        ("budget_reservations", "created_at"),
        ("capability_invocations", "created_at"),
        ("capability_invocation_events", "occurred_at"),
        ("research_task_events", "occurred_at"),
    ):
        assert f.tables[table][-1][time] == result.completed_at
    first_lock = next(i for i, v in enumerate(f.trace) if v[0] == "lock")
    assert all(i < first_lock for i, v in enumerate(f.trace) if v[0] == "bytes")
    for i, v in enumerate(f.trace):
        if v[0] == "lock":
            assert [x[0] for x in f.trace[i + 1 : i + 4]] == [
                "authority",
                "credential",
                "committed_receipt",
            ]
    target = tmp_path / "s4-no-io-trace.json"
    target.write_text(json.dumps(f.trace, default=str, indent=2) + "\n")


@pytest.mark.parametrize(
    "actor_type,role", [("AGENT", "OWNER"), ("HUMAN", "RESEARCHER"), ("HUMAN", "VIEWER")]
)
def test_registration_requires_current_human_owner(actor_type, role):
    f = Fixture()
    f.actor_type, f.role = actor_type, role
    denied(f, ErrorCode.FORBIDDEN, register=True)
    assert not f.attempt_writes


@pytest.mark.parametrize("kind", ["new_instance", "no_context", "wrong_scope", "wrong_principal"])
def test_identity_trust_and_context_binding(kind):
    f = Fixture()
    f.install_policy()
    context = f.context
    if kind == "new_instance":
        context = replace(context, consumer_capability=FakeConsumerCapability())
    elif kind == "no_context":
        context = False
    elif kind == "wrong_scope":
        context = replace(context, task_id=new_uuid7())
    else:
        context = replace(context, principal=replace(f.principal, credential_id="other"))
    denied(f, ErrorCode.FORBIDDEN, context=context)
    assert not f.attempt_writes


def test_exact_final_unit_sets_sticky_stop_and_denies_next_request():
    f = Fixture()
    budget = f.tables["execution_budgets"][0]
    spec = BudgetSpec("fake-usd-v1", max_llm_calls=1, max_token_cost=Decimal("0.125000"))
    budget.update(asdict(spec), content_hash=policy_hash("ExecutionBudgetPolicy", spec))
    f.install_policy()
    f.run()
    assert f.tables["research_task_events"][-1]["stop_budget"] is True
    f.args = replace(f.args, invocation_id=new_uuid7())
    denied(f, ErrorCode.INVALID_STATE_TRANSITION)


def test_policy_switch_retains_task_wide_call_count():
    f = Fixture()
    f.install_policy()
    f.run()
    f.policy_id = new_uuid7()
    f.policy = replace(f.policy, version="policy-2", max_tool_calls=1)
    f.run(register=True)
    # Seed a prior final charge to free occupancy without refunding the admitted call.
    reservation = f.tables["budget_reservations"][0]
    f.tables["budget_usage_records"].append(
        {
            "reservation_id": reservation["id"],
            "is_final": True,
            "failure_streak": 0,
            "no_improvement_streak": 0,
            **asdict(FAKE_RESOURCES),
        }
    )
    f.version_id = new_uuid7()
    f.version = dict(f.version, id=f.version_id, tool_policy_version=f.policy.version)
    f.context = replace(f.context, agent_version_id=f.version_id)
    f.args = replace(
        f.args,
        invocation_id=new_uuid7(),
        agent_version_id=f.version_id,
        policy_id=f.policy_id,
        policy_content_hash=f.policy.digest(f.project),
    )
    denied(f, ErrorCode.FORBIDDEN)
    assert len(f.tables["budget_reservations"]) == 1


STAGES = (
    "task",
    "research_task_command_receipts",
    "budget_reservations",
    "capability_invocations",
    "capability_invocation_events",
    "capability_invocation_refs",
    "research_task_events",
    "research_task_receipt_events",
    "constraints",
    "commit",
)


@pytest.mark.parametrize("stage", STAGES)
def test_request_rollback_at_every_write_stage(stage):
    f = Fixture()
    f.install_policy()
    before = deepcopy((f.task_row, f.tables))
    f.fail_stage = stage
    with pytest.raises(RuntimeError, match="injected"):
        f.run()
    assert (f.task_row, f.tables) == before
    assert f.commits == 0


@pytest.mark.parametrize("stage", ("agent_tool_policies", "agent_tool_policy_permissions"))
def test_registration_rollback(stage):
    f = Fixture()
    before = deepcopy((f.task_row, f.tables))
    f.fail_stage = stage
    with pytest.raises(RuntimeError):
        f.run(register=True)
    assert (f.task_row, f.tables) == before


@pytest.mark.parametrize("register", [False, True])
def test_saved_replay_precedes_stale_cas_role_availability_and_preflight_failure(register):
    f = Fixture()
    if not register:
        f.install_policy()
    command = f.command(register=register)
    first = f.run(command, register=register)
    f.byte_failure = True
    f.role = "VIEWER"
    f.availability["status"] = "DISABLED"
    f.task_row["status"] = "CANCELLED"
    f.task_row["row_version"] += 4
    replay = f.run(command, register=register, context=False)
    assert replay == replace(first, replayed=True)
    assert f.commits == 1
    denied(
        f,
        ErrorCode.IDEMPOTENCY_CONFLICT,
        register=register,
        command=replace(command, arguments=replace(command.arguments, reason="changed")),
    )
    f.valid = False
    denied(f, ErrorCode.FORBIDDEN, register=register, command=command)


@pytest.mark.parametrize(
    "stage",
    [
        "share",
        "project",
        "command",
        "task_key",
        "agent_key",
        "version_key",
        "task_row",
        "steps",
        "checkpoints",
        "availability",
        "invocations",
    ],
)
def test_after_every_wait_authentication_and_receipt_precede_diagnostics(stage):
    f = Fixture()
    f.install_policy()

    def revoke(current):
        if current == stage:
            f.valid = False

    f.wait_hook = revoke
    denied(f, ErrorCode.FORBIDDEN)
    assert not f.attempt_writes


@pytest.mark.parametrize("stage", STAGES[:-1])
def test_after_write_wait_revocation_rolls_back(stage):
    f = Fixture()
    f.install_policy()

    def revoke(current):
        if current == stage:
            f.valid = False

    f.stage_hook = revoke
    denied(f, ErrorCode.FORBIDDEN)


def test_stable_ids_across_fresh_whole_transaction_retry():
    f = Fixture()
    f.install_policy()
    f.retry_stage = "research_task_receipt_events"
    f.run()
    assert f.command_transactions == 2 and f.commits == 1
    for table in STAGES[1:-2]:
        written = [r for t, r in f.attempt_writes if t == table]
        assert len(written) == 2 and written[0] == written[1]
    assert len(f.tables["budget_reservations"]) == 1


@pytest.mark.parametrize(
    "kind",
    [
        "no_version",
        "disabled",
        "not_live",
        "checkpoint",
        "bundle",
        "budget",
        "pin",
        "size",
        "stop",
        "hash",
    ],
)
def test_request_denials_have_zero_effects(kind):
    f = Fixture()
    f.install_policy()
    code = ErrorCode.INVALID_STATE_TRANSITION
    if kind == "no_version":
        f.args = replace(f.args, agent_version_id=new_uuid7())
        code = ErrorCode.NOT_FOUND
    elif kind == "disabled":
        f.availability["status"] = "DISABLED"
        code = ErrorCode.FORBIDDEN
    elif kind == "not_live":
        f.agent_live = False
        code = ErrorCode.FORBIDDEN
    elif kind == "checkpoint":
        f.tables["human_checkpoints"][0]["status"] = "REJECTED"
    elif kind == "bundle":
        f.task_row["budget_policy_id"] = None
    elif kind == "budget":
        f.tables["execution_budgets"][0]["max_llm_calls"] = 0
        code = ErrorCode.VALIDATION_ERROR
    elif kind == "pin":
        f.args = replace(f.args, harness_content_hash="a" * 64)
        code = ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    elif kind == "size":
        f.artifacts[f.harness]["byte_size"] += 1
        code = ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    elif kind == "stop":
        f.tables["research_task_events"][-1]["stop_human"] = True
    elif kind == "hash":
        f.args = replace(f.args, policy_content_hash="a" * 64)
        code = ErrorCode.FORBIDDEN
    denied(f, code)
    assert not f.attempt_writes


def test_constraint_wait_advancing_time_does_not_use_provenance_timestamp():
    f = Fixture()
    f.install_policy()

    def advance(stage):
        if stage == "constraints":
            f.clock += timedelta(seconds=61)

    f.stage_hook = advance
    denied(f, ErrorCode.INVALID_STATE_TRANSITION)


@pytest.mark.parametrize(
    "stage",
    [
        "share",
        "project",
        "command",
        "task_key",
        "agent_key",
        "version_key",
        "task_row",
        "steps",
        "checkpoints",
        "availability",
        "invocations",
    ],
)
def test_committed_receipt_discovered_after_each_wait_wins_before_fresh_diagnostics(
    stage, monkeypatch
):
    f = Fixture()
    f.install_policy()
    command = f.command()
    first = f.run(command)
    f.task_row["row_version"] += 100
    f.role = "VIEWER"
    f.byte_failure = True
    writes = len(f.attempt_writes)
    visible = False
    original = f.repo.committed_receipt

    def wait(current):
        nonlocal visible
        if current == stage:
            visible = True

    def lookup(*args):
        return original(*args) if visible else None

    f.wait_hook = wait
    monkeypatch.setattr(f.repo, "committed_receipt", lookup)
    assert f.run(command) == replace(first, replayed=True)
    assert len(f.attempt_writes) == writes


def test_three_attempt_limit_and_timeout_never_retries(monkeypatch):
    f = Fixture()
    f.install_policy()
    calls = []

    def failure(*args, **kwargs):
        calls.append(True)
        raise ResearchBaseError(
            ErrorCode.CONCURRENT_MODIFICATION, "transient", {"retryable_pr301": True}
        )

    monkeypatch.setattr(f.service, "_once", failure)
    denied(f, ErrorCode.CONCURRENT_MODIFICATION)
    assert len(calls) == 3
    calls.clear()

    def timeout(*args, **kwargs):
        calls.append(True)
        raise ResearchBaseError(
            ErrorCode.CONCURRENT_MODIFICATION, "timeout", {"retryable_pr301": False}
        )

    monkeypatch.setattr(f.service, "_once", timeout)
    denied(f, ErrorCode.CONCURRENT_MODIFICATION)
    assert len(calls) == 1


def test_uncertain_commit_reconciles_original_saved_receipt(monkeypatch):
    from tests.unit.phase3.gateway_fixtures import Uow

    from researchbase.agent_runtime.ports.task_repository import UncertainTaskCommit

    f = Fixture()
    f.install_policy()
    original = Uow.commit

    def lost_response(unit):
        original(unit)
        raise UncertainTaskCommit("lost commit response")

    monkeypatch.setattr(Uow, "commit", lost_response)
    result = f.run()
    assert result.replayed and f.command_transactions == f.commits == 1
    assert len(f.tables["budget_reservations"]) == 1
    assert len(f.tables["capability_invocation_events"]) == 1


def test_entitled_agent_request_uses_same_application_command():
    f = Fixture()
    f.install_policy()
    f.actor_type, f.role = "AGENT", "RESEARCHER"
    assert f.run().reservation_id is not None


def test_reused_command_uuid_from_another_actor_cannot_hide_a_prior_stop():
    f = Fixture()
    f.install_policy()
    command = f.command()
    old = f.tables["research_task_events"][-1]
    # A historical stop from a different actor may share the caller's command UUID:
    # command identity is project + authenticated actor + UUID, not UUID alone.
    f.tables["research_task_events"].append(
        {
            **old,
            "id": new_uuid7(),
            "actor_id": new_uuid7(),
            "command_id": command.command_id,
            "event_type": "TERMINATION_EVALUATED",
            "stop_human": True,
        }
    )
    denied(f, ErrorCode.INVALID_STATE_TRANSITION, command=command)
    assert not f.attempt_writes
