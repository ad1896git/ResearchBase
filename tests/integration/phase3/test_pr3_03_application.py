"""Real PostgreSQL Application commands, typed effects and finite observations."""

from dataclasses import replace

import pytest
from sqlalchemy import text
from tests.integration.phase3.gateway_fixtures import (
    finish,
    install,
    measure_gateway,
    request_command,
    request_invocation,
    revision,
    start,
)
from tests.integration.phase3.test_pr3_00_bootstrap import _rows

from researchbase.agent_runtime.application.gateway_contracts import CapabilityRequest
from researchbase.agent_runtime.ports.task_safety_repository import FakeConsumerCapability
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7


def test_normal_role_request_start_finish_and_effect_counts(gateway, monkeypatch):
    g = gateway
    measured = measure_gateway(monkeypatch)
    before = _rows(g.engine)
    request_invocation(g)
    start(g)
    finish(g)
    read = g.gateway_service.get_capability_invocation(
        g.owner, g.project, g.task, g.args.invocation_id
    )
    assert read.status == "SUCCEEDED" and not read.execution_enabled
    assert [e.event_type for e in read.events] == ["REQUESTED", "STARTED", "FINISHED"]
    with g.engine.connect() as conn:
        print(
            "RUNTIME_ROLE",
            conn.execute(text("SELECT current_user")).scalar_one(),
            "encoding",
            conn.execute(text("SHOW server_encoding")).scalar_one(),
            "version",
            conn.execute(text("SHOW server_version")).scalar_one(),
        )
        assert not conn.execute(
            text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")
        ).scalar()
        counts = {
            t: conn.execute(text(f"SELECT count(*) FROM {t}")).scalar_one()
            for t in (
                "agent_tool_policies",
                "agent_tool_policy_permissions",
                "capability_invocations",
                "capability_invocation_refs",
                "capability_invocation_events",
                "budget_reservations",
                "budget_usage_records",
            )
        }
    assert list(counts.values()) == [1, 1, 1, 1, 3, 1, 1]
    after = _rows(g.engine)
    scientific = (
        "artifacts",
        "artifact_versions",
        "research_questions",
        "hypotheses",
        "claims",
        "runs",
        "measurements",
        "statistical_results",
    )
    scientific_writes = sum(len(set(before[t]) ^ set(after[t])) for t in scientific)
    assert scientific_writes == 0
    assert measured == {"gateway_commits": 4, "fake_calls": 0}
    print("normal-role effects", counts, f"scientific_writes={scientific_writes}", measured)


@pytest.mark.parametrize("outcome", ["SUCCEEDED", "FAILED", "UNKNOWN_OUTCOME", "CANCELLED"])
def test_all_finish_outcomes(gateway, outcome):
    g = gateway
    request_invocation(g)
    start(g)
    finish(g, outcome)
    read = g.gateway_service.get_capability_invocation(
        g.owner, g.project, g.task, g.args.invocation_id
    )
    assert read.status == outcome
    assert len(read.events) == 3 and read.usage_record_id is not None
    if outcome == "UNKNOWN_OUTCOME":
        finish(g, "SUCCEEDED", "RECONCILE", 3)
        final = g.gateway_service.get_capability_invocation(
            g.owner, g.project, g.task, g.args.invocation_id
        )
        assert final.status == "UNKNOWN_OUTCOME" and final.effective_outcome == "SUCCEEDED"
        assert final.effective_usage_record_id != final.usage_record_id
        with pytest.raises(ResearchBaseError):
            finish(g, "FAILED", "RECONCILE", 3)


def test_prestart_cancel(gateway):
    g = gateway
    request_invocation(g)
    finish(g, "CANCELLED", inv_revision=1)
    read = g.gateway_service.get_capability_invocation(
        g.owner, g.project, g.task, g.args.invocation_id
    )
    assert read.status == "CANCELLED" and read.started_at is None
    assert len(read.events) == 2


def test_untrusted_consumer_has_no_effects(gateway):
    g = gateway
    install(g)
    before = _rows(g.engine)
    with pytest.raises(ResearchBaseError) as error:
        g.gateway_service.request_capability_invocation(
            g.owner,
            request_command(g),
            replace(g.context, consumer_capability=FakeConsumerCapability()),
        )
    assert error.value.code == ErrorCode.FORBIDDEN
    assert _rows(g.engine) == before


def test_invoke_one_fake_three_transactions_and_terminal_replay(gateway, monkeypatch):
    from researchbase.agent_runtime.application import routing

    g = gateway
    install(g)
    measured = measure_gateway(monkeypatch)
    calls = []
    original = routing.finite_fake_echo

    def echo(parameters):
        calls.append(parameters)
        return original(parameters)

    monkeypatch.setattr(routing, "finite_fake_echo", echo)
    c = CapabilityRequest(new_uuid7(), new_uuid7(), new_uuid7(), revision(g), g.args)
    before = revision(g)
    result = g.gateway_service.invoke(c, g.context)
    assert result.outcome == "SUCCEEDED" and len(calls) == 1
    assert revision(g) == before + 3
    assert measured == {"gateway_commits": 3, "fake_calls": 1}
    commits_before_replay = measured["gateway_commits"]
    assert g.gateway_service.invoke(c, g.context) == result and len(calls) == 1
    replay_commits = measured["gateway_commits"] - commits_before_replay
    assert replay_commits == 0
    assert measured["fake_calls"] == 1
    print("invoke", measured, f"replay_commits={replay_commits}")


@pytest.mark.parametrize(
    "operation,stage",
    [
        ("register", "research_task_command_receipts"),
        ("register", "agent_tool_policies"),
        ("register", "agent_tool_policy_permissions"),
        ("register", "research_task_events"),
        ("register", "research_task_receipt_events"),
        ("request", "research_task_command_receipts"),
        ("request", "budget_reservations"),
        ("request", "capability_invocations"),
        ("request", "capability_invocation_refs"),
        ("request", "capability_invocation_events"),
        ("request", "research_task_events"),
        ("request", "research_task_receipt_events"),
        ("start", "research_task_command_receipts"),
        ("start", "capability_invocation_events"),
        ("start", "research_task_events"),
        ("start", "research_task_receipt_events"),
        ("finish", "research_task_command_receipts"),
        ("finish", "budget_usage_records"),
        ("finish", "capability_invocation_events"),
        ("finish", "research_task_events"),
        ("finish", "research_task_receipt_events"),
    ],
)
def test_each_command_rolls_back_after_persisted_write(gateway, monkeypatch, operation, stage):
    from researchbase.persistence.capability_gateway_repository import SqlAlchemyGatewayRepository

    g = gateway
    if operation == "request":
        install(g)
    elif operation in ("start", "finish"):
        request_invocation(g)
        if operation == "finish":
            start(g)
    before = _rows(g.engine)
    original = SqlAlchemyGatewayRepository.insert
    reached = []

    def insert(repo, table, row):
        original(repo, table, row)
        if table == stage:
            reached.append(table)
            raise RuntimeError("S8 injected failure after SQL write")

    monkeypatch.setattr(SqlAlchemyGatewayRepository, "insert", insert)
    with pytest.raises(RuntimeError, match="S8 injected failure"):
        if operation == "register":
            install(g)
        elif operation == "request":
            g.gateway_service.request_capability_invocation(g.owner, request_command(g), g.context)
        elif operation == "start":
            start(g)
        else:
            finish(g)
    assert reached == [stage] and _rows(g.engine) == before


def test_agent_and_human_share_boundary_owner_only_registration(gateway):
    g = gateway
    before = _rows(g.engine)
    with pytest.raises(ResearchBaseError) as error:
        g.gateway_service.register_agent_tool_policy(g.agent_principal, g.registration)
    assert error.value.code == ErrorCode.FORBIDDEN and _rows(g.engine) == before
    install(g)
    c = request_command(g)
    context = replace(g.context, principal=g.agent_principal)
    result = g.gateway_service.request_capability_invocation(g.agent_principal, c, context)
    assert result.actor_id == g.agent_principal.actor_id
    with g.engine.connect() as conn:
        assert conn.execute(
            text("SELECT requested_by FROM capability_invocations")
        ).scalar_one() == (g.agent_principal.actor_id)


def test_post_start_cancel_permits_finite_finish_but_no_new_dispatch(gateway):
    g = gateway
    request_invocation(g)
    start(g)
    g.p.service.execute(
        g.owner,
        g.p.command(
            "cancel_research_task",
            g.task,
            revision(g),
            {"reason": "Stop future work."},
        ),
    )
    finish(g)
    current = g.gateway_service.get_capability_invocation(
        g.owner, g.project, g.task, g.args.invocation_id
    )
    assert current.status == "SUCCEEDED" and current.execution_enabled is False
    before = _rows(g.engine)
    with pytest.raises(ResearchBaseError):
        g.gateway_service.request_capability_invocation(
            g.owner, request_command(g, invocation_id=new_uuid7()), g.context
        )
    assert _rows(g.engine) == before


@pytest.mark.parametrize(
    "gateway", [{"budget": {"pricing_basis": "fake-usd-v1", "max_llm_calls": 1}}], indirect=True
)
@pytest.mark.parametrize("stop", ["own", "later", "cancel"])
def test_exact_cap_own_stop_start_and_later_stops(gateway, stop):
    from tests.integration.phase3.test_pr3_04_application import command, service

    g = gateway
    request_invocation(g)
    with g.engine.connect() as conn:
        assert conn.execute(
            text("""
            SELECT stop_budget FROM research_task_events
            WHERE research_task_id=:task ORDER BY sequence DESC LIMIT 1
        """),
            {"task": g.task},
        ).scalar_one()
    if stop == "later":
        service(g.p).execute(
            g.owner,
            command(
                g.p,
                g.task,
                revision(g),
                "evaluate_task_termination",
                {"reason": "Later stop evaluation."},
            ),
        )
    elif stop == "cancel":
        g.p.service.execute(
            g.owner,
            g.p.command(
                "cancel_research_task",
                g.task,
                revision(g),
                {"reason": "Additional human stop."},
            ),
        )
    if stop == "own":
        start(g)
        finish(g)
    else:
        before = _rows(g.engine)
        with pytest.raises(ResearchBaseError) as error:
            start(g)
        assert error.value.code == ErrorCode.INVALID_STATE_TRANSITION
        assert _rows(g.engine) == before


@pytest.mark.parametrize("operation", ["register", "request", "start", "finish"])
@pytest.mark.parametrize("stage", ["task_update", "constraints", "commit"])
def test_command_rollback_at_task_constraint_and_commit_stages(
    gateway, monkeypatch, operation, stage
):
    from researchbase.persistence.capability_gateway_repository import SqlAlchemyGatewayRepository
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    g = gateway
    if operation == "request":
        install(g)
    elif operation in ("start", "finish"):
        request_invocation(g)
        if operation == "finish":
            start(g)
    before = _rows(g.engine)
    target, method = (
        (SqlAlchemyUnitOfWork, "commit")
        if stage == "commit"
        else (
            SqlAlchemyGatewayRepository,
            "update_task" if stage == "task_update" else "force_constraints",
        )
    )
    original = getattr(target, method)
    reached = []

    def fail(obj, *args, **kwargs):
        if stage != "commit":
            original(obj, *args, **kwargs)
        reached.append(stage)
        raise RuntimeError("S8 stage rollback")

    monkeypatch.setattr(target, method, fail)
    with pytest.raises(RuntimeError, match="S8 stage rollback"):
        if operation == "register":
            install(g)
        elif operation == "request":
            g.gateway_service.request_capability_invocation(g.owner, request_command(g), g.context)
        elif operation == "start":
            start(g)
        else:
            finish(g)
    assert reached == [stage] and _rows(g.engine) == before


@pytest.mark.parametrize(
    "case",
    [
        "checkpoint",
        "policy_hash",
        "harness_hash",
        "parameters_hash",
        "missing_version",
        "policy_version",
        "manifest_skill",
        "manifest_strategy",
        "registry_bytes",
        "availability",
    ],
)
def test_each_gate_cap_version_and_manifest_denial_without_effects(gateway, monkeypatch, case):
    from tests.integration.phase3.test_pr3_04_application import command, service

    from researchbase.agent_runtime.application.agent_contracts import (
        AgentCommand,
        ChangeAgentAvailability,
    )
    from researchbase.agent_runtime.application.gateway_contracts import (
        GatewayCommand,
        RegisterToolPolicyArguments,
    )

    g = gateway
    install(g)
    args, context = g.args, g.context
    if case == "checkpoint":
        service(g.p).execute(
            g.owner,
            command(
                g.p,
                g.task,
                revision(g),
                "request_human_checkpoint",
                {
                    "checkpoint_id": str(new_uuid7()),
                    "step_id": None,
                    "checkpoint_type": "plan_review",
                    "reason": "Newest gate pending.",
                },
            ),
        )
    elif case == "policy_version":
        spec = replace(g.spec, version="other-policy-v2")
        identity = new_uuid7()
        g.gateway_service.register_agent_tool_policy(
            g.owner,
            GatewayCommand(
                g.project,
                g.task,
                new_uuid7(),
                revision(g),
                "register_agent_tool_policy",
                RegisterToolPolicyArguments(identity, spec, "Register distinct policy."),
            ),
        )
        args = replace(args, policy_id=identity, policy_content_hash=spec.digest(g.project))
    elif case == "availability":
        g.service.execute(
            AgentCommand(
                g.project,
                g.owner,
                new_uuid7(),
                "change_agent_availability",
                1,
                ChangeAgentAvailability(g.args.agent_version_id, "DISABLED", "Pause."),
            )
        )
    elif case == "missing_version":
        identity = new_uuid7()
        args = replace(args, agent_version_id=identity)
        context = replace(context, agent_version_id=identity)
    elif case == "manifest_skill":
        args = replace(args, skill_version="2.0.0")
    elif case == "manifest_strategy":
        args = replace(args, strategy_version="2.0.0")
    elif case.endswith("_hash"):
        field = {
            "policy_hash": "policy_content_hash",
            "harness_hash": "harness_content_hash",
            "parameters_hash": "parameters_content_hash",
        }[case]
        args = replace(args, **{field: "0" * 64})
    before = _rows(g.engine)
    with monkeypatch.context() as patch:
        if case == "registry_bytes":
            original = g.store.open
            patch.setattr(
                g.store,
                "open",
                lambda digest: b"wrong registry"
                if digest
                in (
                    g.spec.registry_content_hash,
                    "sha256:" + g.spec.registry_content_hash,
                )
                else original(digest),
            )
        c = GatewayCommand(
            g.project, g.task, new_uuid7(), revision(g), "request_capability_invocation", args
        )
        with pytest.raises(ResearchBaseError) as error:
            g.gateway_service.request_capability_invocation(g.owner, c, context)
    expected = {
        "checkpoint": {ErrorCode.INVALID_STATE_TRANSITION},
        "missing_version": {ErrorCode.NOT_FOUND},
        "policy_hash": {ErrorCode.FORBIDDEN},
        "policy_version": {ErrorCode.FORBIDDEN},
        "manifest_skill": {ErrorCode.FORBIDDEN},
        "manifest_strategy": {ErrorCode.FORBIDDEN},
        "availability": {ErrorCode.FORBIDDEN},
        "registry_bytes": {ErrorCode.PROVENANCE_CLOSURE_VIOLATION},
        "harness_hash": {ErrorCode.PROVENANCE_CLOSURE_VIOLATION},
        "parameters_hash": {ErrorCode.PROVENANCE_CLOSURE_VIOLATION},
    }
    assert error.value.code in expected[case]
    assert _rows(g.engine) == before


@pytest.mark.parametrize("outcome", ["SUCCEEDED", "FAILED", "CANCELLED"])
def test_reconciliation_all_final_outcomes_preserves_unknown_and_no_refund(gateway, outcome):
    from tests.integration.phase3.test_pr3_04_application import service

    g = gateway
    request_invocation(g)
    start(g)
    unknown_command, unknown = finish(g, "UNKNOWN_OUTCOME")
    with g.engine.connect() as conn:
        frozen_row = dict(
            conn.execute(text("SELECT * FROM capability_invocations")).mappings().one()
        )
        old_usage = dict(conn.execute(text("SELECT * FROM budget_usage_records")).mappings().one())
    safety = service(g.p).get_task_safety(g.owner, g.project, g.task)
    assert safety.reserved.llm_calls == 1 and safety.consumed.llm_calls == 0
    assert safety.parallel_branches == 1 and not old_usage["is_final"]
    before = _rows(g.engine)
    replay = g.gateway_service.finish_capability_invocation(
        g.owner, unknown_command, replace(g.context, finish_observation=unknown_command.arguments)
    )
    assert replay == replace(unknown, replayed=True) and _rows(g.engine) == before
    finish(g, outcome, "RECONCILE", 3)
    with g.engine.connect() as conn:
        assert (
            dict(conn.execute(text("SELECT * FROM capability_invocations")).mappings().one())
            == frozen_row
        )
        assert (
            dict(
                conn.execute(
                    text("SELECT * FROM budget_usage_records WHERE id=:id"), {"id": old_usage["id"]}
                )
                .mappings()
                .one()
            )
            == old_usage
        )
        assert (
            conn.execute(
                text("SELECT count(*) FROM budget_usage_records WHERE is_final")
            ).scalar_one()
            == 1
        )
    final = service(g.p).get_task_safety(g.owner, g.project, g.task)
    assert final.consumed.llm_calls == 1 and final.reserved.llm_calls == 0
    assert final.parallel_branches == 0
    assert final.consumed.token_cost == 0  # Explicit final fake observation has zero cost.
    before = _rows(g.engine)
    with pytest.raises(ResearchBaseError) as error:
        finish(g, outcome, "RECONCILE", 3)
    assert error.value.code == ErrorCode.INVALID_STATE_TRANSITION and _rows(g.engine) == before


@pytest.mark.parametrize("stage", ["invocation_update", "output_ref", "constraints", "commit"])
def test_finish_output_and_invocation_update_rollback(gateway, monkeypatch, stage):
    from researchbase.persistence.capability_gateway_repository import SqlAlchemyGatewayRepository
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    g = gateway
    request_invocation(g)
    start(g)
    before = _rows(g.engine)
    reached = []
    original_insert = SqlAlchemyGatewayRepository.insert
    original_update = SqlAlchemyGatewayRepository.update_invocation
    original_force = SqlAlchemyGatewayRepository.force_constraints

    def insert(repo, table, row):
        original_insert(repo, table, row)
        if table == "capability_invocation_refs":
            reached.append(stage)
            raise RuntimeError("S8 finish rollback")

    def update(repo, *args, **kwargs):
        original_update(repo, *args, **kwargs)
        reached.append(stage)
        raise RuntimeError("S8 finish rollback")

    def constraints(repo):
        original_force(repo)
        reached.append(stage)
        raise RuntimeError("S8 finish rollback")

    def commit(uow):
        reached.append(stage)
        raise RuntimeError("S8 finish rollback")

    if stage == "output_ref":
        monkeypatch.setattr(SqlAlchemyGatewayRepository, "insert", insert)
    elif stage == "invocation_update":
        monkeypatch.setattr(SqlAlchemyGatewayRepository, "update_invocation", update)
    elif stage == "constraints":
        monkeypatch.setattr(SqlAlchemyGatewayRepository, "force_constraints", constraints)
    else:
        monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", commit)
    with pytest.raises(RuntimeError, match="S8 finish rollback"):
        finish(g, output_refs=(g.args.input_refs[0],))
    assert reached == [stage] and _rows(g.engine) == before
