"""Disabled Stage2 on real PG18, including ordinary-role complete denied effects.

Synthetic W/bindings below test guard shape only. They are not registration,
measured allowance, positive admission, actual evaluation or production evidence.
Positive Application admission/settlement, attributed concurrency and deployment
performance remain blocked by literal-false enablement and absent Stage3 wiring.
"""

import hashlib
import importlib.util
import json
import re
from dataclasses import fields, replace
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest
from alembic import command as alembic_command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import CheckConstraint, Table, create_engine, inspect, text
from sqlalchemy.exc import DBAPIError
from tests.application_compat import LegacyApplicationService
from tests.disposable_postgres import disposable_database
from tests.integration.phase2.pr2_20_support import upgrade
from tests.integration.phase2.test_pr2_10_binding_contract import _artifact
from tests.integration.phase3.conftest import Credentials
from tests.integration.phase3.search_fixtures import (
    catalog_snapshot,
    create_rows,
    insert,
    lock,
    search_environment,
)
from tests.integration.phase3.test_pr3_04_application import (
    approve,
    command,
    reserve,
    resources,
    service,
    settle,
)
from tests.integration.phase3.test_pr3_16_application import snapshot
from tests.integration.test_pr06_application import register_command, snapshot_command
from tests.integration.test_pr08_application import create_command as metric_command
from tests.unit.phase3.test_bearing_contracts import VECTORS, command_from_vector

from researchbase.agent_runtime.application.bearing_contracts import (
    AdmitBearingArguments,
    BearingBinding,
)
from researchbase.agent_runtime.application.experiment_search import ExperimentSearchService
from researchbase.agent_runtime.application.safety_contracts import material_value
from researchbase.agent_runtime.application.search_contracts import (
    CreateSearchArguments,
    SearchCommand,
)
from researchbase.agent_runtime.services.fake_consumer import TrustedFakeConsumer
from researchbase.application.commands import FreezeMetricDefinitionCommand
from researchbase.domain.evidence import DatasetId
from researchbase.domain.organization import ProjectId
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.ids import new_uuid7
from researchbase.foundation.time import SystemClock
from researchbase.persistence.models import Base, BudgetReservationsModel

PARENT = "0082_experiment_search_core"
HEAD = "0083_bearing_evaluation_guards"
COLUMNS = (
    "labels_artifact_version_id",
    "baseline_predictions_artifact_version_id",
    "candidate_predictions_artifact_version_id",
    "protocol_artifact_version_id",
    "evaluator_artifact_version_id",
    "dataset_snapshot_id",
    "metric_definition_version_id",
    "consumer_generation",
)
CHANGED_FUNCTIONS = {
    "pr316_command_event",
    "pr316_receipt_insert",
    "pr316_node_proof",
    "pr316_state",
    "pr316_lineage_insert",
    "pr316_validate_receipt",
    "pr304_child_guard",
    "pr304_validate_safety",
    "pr301_receipt_complete",
}
CHANGED_CHECKS = {
    "pr316_command_names",
    "research_task_command_receipts_material_version_check",
    "pr316_receipt_shape_ck",
    "pr316_task_event_names",
    "pr316_task_event_states",
    "pr316_task_event_reason",
    "pr303_event_stop_kind",
}
FKS = {
    "pr316d1_labels_av_fk",
    "pr316d1_baseline_predictions_av_fk",
    "pr316d1_candidate_predictions_av_fk",
    "pr316d1_protocol_av_fk",
    "pr316d1_evaluator_av_fk",
    "pr316d1_dataset_snapshot_fk",
    "pr316d1_metric_version_fk",
}
NEW_FUNCTIONS = {
    "pr316d1_enabled",
    "pr316d1_authority",
    "pr316d1_admission",
    "pr316d1_validate_receipt",
}
FROZEN = {
    "0078_task_safety_policies.py": "7c312389444e9edfea89f10c472462b7"
    "d2ca9c739a951c905d09140058b8c255",
    "0080_capability_gateway.py": "b1ef6a678620acb27282eb68d08c658e"
    "7bfaad85f591ca93f298545007326561",
    "0081_agent_execution_intents.py": "142c7a9061785a971d7043667041cf53"
    "68be24e38069c59900640d13c2259e52",
    "0082_experiment_search_core.py": "0166bdc1e30c9c3963c9655b6cfd7fed"
    "1cdcd0e6822a39a666de2fb7adb52470",
}


def old_rows(engine, columns=None):
    """Include xmin and every old column, so additive DDL cannot hide rewrites."""
    columns = columns or {
        table: [c["name"] for c in inspect(engine).get_columns(table)]
        for table in inspect(engine).get_table_names()
        if table != "alembic_version"
    }
    with engine.connect() as conn:
        rows = {
            table: sorted(
                conn.execute(
                    text(
                        "SELECT row_to_json(x)::text FROM (SELECT "
                        + ",".join('"' + c + '"' for c in names)
                        + ',xmin::text AS __xmin FROM "'
                        + table
                        + '") x'
                    )
                ).scalars()
            )
            for table, names in columns.items()
        }
    return columns, rows


def assert_delta(before, after):
    for key in ("indexes", "triggers", "privileges"):
        assert before[key] == after[key], key
    old = {row[0]: row[1:] for row in before["functions"]}
    new = {row[0]: row[1:] for row in after["functions"]}
    assert not old.keys() - new.keys()
    assert {k.split("(")[0] for k in new.keys() - old.keys()} == NEW_FUNCTIONS
    assert {k.split("(")[0] for k in old if old[k] != new[k]} == CHANGED_FUNCTIONS
    assert all(old[k][1] == new[k][1] for k in old)  # Explicit and PUBLIC ACLs.
    old = {r[:2]: r[2:] for r in before["constraints"]}
    new = {r[:2]: r[2:] for r in after["constraints"]}
    assert not old.keys() - new.keys()
    assert {k[1] for k in new.keys() - old.keys()} == FKS | {"pr316d1_reservation_binding_shape_ck"}
    assert {k[1] for k in old if old[k] != new[k]} == CHANGED_CHECKS
    old = {r[:2]: r[2:] for r in before["columns"]}
    new = {r[:2]: r[2:] for r in after["columns"]}
    assert {k: new[k] for k in old} == old
    assert new.keys() - old.keys() == {("budget_reservations", c) for c in COLUMNS}


@pytest.fixture(scope="module")
def d1(tmp_path_factory):
    context = search_environment(tmp_path_factory)  # Historical 0082 remains explicit.
    env = next(context)
    try:
        env.binding = frozen_binding(env)
        before = catalog_snapshot(env.admin)
        columns, rows = old_rows(env.admin)
        upgrade(env.url, HEAD)
        assert old_rows(env.admin, columns)[1] == rows
        assert_delta(before, catalog_snapshot(env.admin))
        env.engine.dispose()  # Discard pre-DDL prepared SELECT * row descriptors.
        yield env
    finally:
        context.close()


@pytest.fixture(scope="module")
def binding(d1):
    return d1.binding


def frozen_binding(d1):
    """Genuine frozen reference metadata via the existing public scientific setup."""
    p = d1.p
    app = LegacyApplicationService(p.factory, SystemClock(), p.store)
    ctx = ExecutionContext(
        actor_id=p.principal.actor_id, request_id=new_uuid7(), client_type="test"
    )
    project = ProjectId(p.project)
    artifact_ids = [
        _artifact(p.factory, p.store, p.principal, project, role.encode(), "other")
        for role in ("labels", "baseline", "candidate", "protocol", "evaluator")
    ]
    dataset = app.register_dataset(register_command(project, ctx))
    ds = app.create_dataset_snapshot(snapshot_command(DatasetId(dataset.id), ctx))
    metric = app.create_metric_definition(
        metric_command(ctx, project, definition={"kind": "paired_accuracy_delta"}, unit=None)
    )
    mv = app.freeze_metric_definition(
        FreezeMetricDefinitionCommand(metric.id, metric.current_version_id, ctx, 1)
    )
    with d1.engine.connect() as conn:
        hashes = [
            conn.scalar(text("SELECT content_hash FROM artifact_versions WHERE id=:id"), {"id": v})
            for v in artifact_ids
        ]
        ds_hash = conn.execute(
            text("SELECT manifest_hash,content_hash FROM dataset_snapshots WHERE id=:id"),
            {"id": ds.id},
        ).one()
    values: dict[str, Any] = dict(
        zip(COLUMNS, [*artifact_ids, ds.id, mv.id, new_uuid7()], strict=True)
    )
    values.update(
        dict(
            zip(
                [
                    "labels_content_hash",
                    "baseline_predictions_content_hash",
                    "candidate_predictions_content_hash",
                    "protocol_content_hash",
                    "evaluator_content_hash",
                    "dataset_manifest_hash",
                    "dataset_content_hash",
                    "metric_content_hash",
                ],
                [*hashes, *ds_hash, mv.content_hash],
                strict=True,
            )
        )
    )
    return BearingBinding(**cast(dict[str, Any], values))


def prepared_task(d1, binding, *, tree_cap=10):
    p = d1.p
    task = p.create()
    c = command(
        p,
        task,
        1,
        "bind_task_policies",
        dict(
            budget_id=str(new_uuid7()),
            budget={
                "pricing_basis": "bearing-local-cpu-v1:" + "a" * 64,
                "max_tree_nodes": tree_cap,
            },
            termination_policy_id=str(new_uuid7()),
            termination={
                "score_metric_version_id": str(binding.metric_definition_version_id),
                "score_direction": "MAXIMIZE",
                "evaluator_version": "paired-test-v1",
            },
            checkpoint_policy_id=str(new_uuid7()),
            checkpoint={},
            reason="Test-only policies.",
        ),
    )
    service(p).execute(p.principal, c)
    approve(p, task, 2)
    with d1.engine.begin() as conn:
        saved = create_rows(conn, d1, task=task)
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    return task, saved.session


def candidate(
    conn,
    env,
    binding,
    task,
    session,
    *,
    change=None,
    omit=None,
    extra=False,
    stop_budget=False,
    reservation_changes=None,
):
    """Raw SQL attack candidate; it can reach deferred guards, never commit v2."""
    p = env.p
    base, _ = command_from_vector(VECTORS[0])
    assert isinstance(base.arguments, AdmitBearingArguments)
    node_id = new_uuid7()
    args = replace(
        base.arguments,
        binding=binding,
        session_id=session,
        node_id=node_id,
        operation_id=node_id,
        reservation_id=new_uuid7(),
        resources=replace(base.arguments.resources, wall_time_seconds=120),
        deadline_seconds=120,
        reason="Account for comparison.",
        mutation_reason="Explore this candidate.",
    )
    if change:
        args = replace(args, **change)
    revision = conn.scalar(
        text("SELECT row_version FROM research_tasks WHERE id=:id"), {"id": task}
    )
    c = replace(
        base,
        project_id=p.project,
        task_id=task,
        command_id=new_uuid7(),
        expected_row_version=revision,
        arguments=args,
    )
    lock(conn, p.project, p.principal.actor_id, c.command_id, task)
    conn.execute(
        text("UPDATE research_tasks SET row_version=:v WHERE id=:id"),
        {"id": task, "v": revision + 1},
    )
    at = conn.scalar(text("SELECT transaction_timestamp()"))
    receipt, event, task_event = (new_uuid7() for _ in range(3))
    if omit != "receipt":
        insert(
            conn,
            "research_task_command_receipts",
            dict(
                id=receipt,
                project_id=p.project,
                actor_id=p.principal.actor_id,
                command_id=c.command_id,
                research_task_id=task,
                command_name=c.command_name,
                request_hash=c.request_hash(p.principal.actor_id),
                hash_scheme="sha256-cjson-v1",
                material_version=2,
                resulting_row_version=revision + 1,
                completed_at=at,
                result_search_session_id=session,
                result_search_node_id=args.node_id,
                result_search_event_id=event,
            ),
        )
    reservation = dict(
        id=args.reservation_id,
        research_task_id=task,
        created_at=at,
        receipt_id=receipt,
        step_id=args.step_id,
        operation_id=args.operation_id,
        **{
            f.name: getattr(binding, f.name)
            for f in fields(binding)
            if not f.name.endswith("_hash")
        },
        **{k: v for k, v in material_value(args.resources).items()},
        observed_depth=args.observed_depth,
        observed_parallel_branches=args.observed_parallel_branches,
    )
    reservation["budget_id"] = conn.scalar(
        text("SELECT budget_policy_id FROM research_tasks WHERE id=:id"), {"id": task}
    )
    reservation["deadline"] = conn.scalar(
        text("SELECT transaction_timestamp()+:seconds*interval '1 second'"),
        {"seconds": args.deadline_seconds},
    )
    reservation.update(reservation_changes or {})
    if omit != "reservation":
        insert(conn, "budget_reservations", reservation)
    if omit != "node":
        insert(
            conn,
            "experiment_search_nodes",
            dict(
                id=args.node_id,
                research_task_id=task,
                search_session_id=session,
                parent_node_id=args.parent_node_id,
                depth=args.observed_depth,
                branch_kind=args.branch_kind.value,
                mutation_reason=args.mutation_reason,
                hypothesis_version_id=args.hypothesis_version_id,
                hypothesis_content_hash=None,
                experiment_spec_version_id=args.experiment_spec_version_id,
                experiment_spec_content_hash=None,
                reservation_id=args.reservation_id,
                created_by=p.principal.actor_id,
                created_at=at,
                receipt_id=receipt,
            ),
        )
    if omit != "search_event":
        insert(
            conn,
            "experiment_search_events",
            dict(
                id=event,
                research_task_id=task,
                search_session_id=session,
                node_id=args.node_id,
                sequence=2,
                event_type="NODE_APPENDED",
                reason=args.mutation_reason,
                actor_id=p.principal.actor_id,
                occurred_at=at,
                receipt_id=receipt,
            ),
        )
    if omit != "task_event":
        insert(
            conn,
            "research_task_events",
            dict(
                id=task_event,
                research_task_id=task,
                actor_id=p.principal.actor_id,
                command_id=c.command_id,
                event_type="BEARING_EVALUATION_ADMITTED",
                sequence=revision + 1,
                task_row_version=revision + 1,
                prior_status="CREATED",
                new_status="CREATED",
                reason=args.reason,
                occurred_at=at,
                stop_budget=stop_budget,
            ),
        )
    if omit != "association":
        insert(
            conn,
            "research_task_receipt_events",
            dict(
                receipt_id=receipt,
                research_task_id=task,
                event_id=task_event,
            ),
        )
    if extra:
        # A v2 receipt can own exactly one reservation, not another charged operation.
        insert(
            conn,
            "budget_reservations",
            {**reservation, "id": new_uuid7(), "operation_id": new_uuid7()},
        )
    return c


def constraint(error):
    return getattr(error.value.orig.diag, "constraint_name", None)


def test_sole_head_and_frozen_source_bytes():
    scripts = ScriptDirectory.from_config(Config("alembic.ini"))
    assert scripts.get_heads() == [HEAD]
    assert scripts.get_revision(HEAD).down_revision == PARENT
    for name, digest in FROZEN.items():
        assert (
            hashlib.sha256((Path("migrations/versions") / name).read_bytes()).hexdigest() == digest
        )


def test_pristine_upgrade_exact_delta_and_forward_only(monkeypatch):
    with disposable_database("researchbase_pr212_test_") as url:
        upgrade(url, PARENT)
        engine = create_engine(url)
        try:
            columns, rows = old_rows(engine)
            before = catalog_snapshot(engine)
            upgrade(url, HEAD)
            assert old_rows(engine, columns)[1] == rows
            assert_delta(before, catalog_snapshot(engine))
            after = catalog_snapshot(engine)
            monkeypatch.setenv("DATABASE_URL", url)
            with pytest.raises(RuntimeError, match="0083 is forward-only"):
                alembic_command.downgrade(Config("alembic.ini"), PARENT)
            assert catalog_snapshot(engine) == after
        finally:
            engine.dispose()


def test_populated_upgrade_preserves_all_old_columns_xmin_acl_and_triggers(d1):
    # The fixture verifies the populated before/after snapshot prior to making new fixtures.
    with d1.engine.connect() as conn:
        assert conn.scalar(text("SELECT version_num FROM alembic_version")) == HEAD
        assert (
            conn.scalar(
                text(
                    "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal "
                    "AND tgname LIKE 'pr316_%'"
                )
            )
            == 16
        )


@pytest.mark.parametrize("vector", VECTORS, ids=lambda v: v["name"])
def test_all_eight_literal_utf8_and_sql_hash_vectors(d1, vector):
    c, actor = command_from_vector(vector)
    with d1.engine.connect() as conn:
        material = c.material(actor)
        actual = conn.scalar(
            text("SELECT pr302s2_cjson(CAST(:v AS jsonb))"),
            {"v": json.dumps(material, ensure_ascii=False)},
        )
        digest = conn.scalar(
            text("SELECT pr302s2_value_digest(CAST(:v AS jsonb))"),
            {"v": json.dumps(material, ensure_ascii=False)},
        )
    assert actual.encode() == canonical_json_bytes(material) == vector["material_utf8"].encode()
    assert digest == vector["sha256"]


def test_binding_shape_all_256_masks_and_ordinary_restrict_fks(d1):
    with d1.engine.connect() as conn:
        expr = conn.scalar(
            text(
                "SELECT pg_get_expr(conbin,conrelid) FROM pg_constraint "
                "WHERE conname='pr316d1_reservation_binding_shape_ck'"
            )
        )
        for mask in range(256):
            projection = ",".join(f"CAST(:v{i} AS uuid) AS {c}" for i, c in enumerate(COLUMNS))
            values = {f"v{i}": UUID(int=1) if mask & (1 << i) else None for i in range(8)}
            assert conn.scalar(
                text(f"SELECT ({expr}) FROM (SELECT {projection}) candidate"), values
            ) is (mask in (0, 255))
        fks = conn.execute(
            text(
                "SELECT conname,confdeltype,condeferrable,condeferred,convalidated "
                "FROM pg_constraint WHERE conname=ANY(:names)"
            ),
            {"names": sorted(FKS)},
        ).all()
        assert len(fks) == 7
        assert all(tuple(row)[1:] == ("r", False, False, True) for row in fks)
    model = cast(Table, BudgetReservationsModel.__table__)
    assert set(COLUMNS) <= set(model.columns.keys())
    assert {fk.name for fk in model.foreign_key_constraints if fk.name in FKS} == FKS
    assert "pr316d1_reservation_binding_shape_ck" in {
        ck.name for ck in model.constraints if isinstance(ck, CheckConstraint)
    }


@pytest.mark.parametrize(
    "settings",
    [{}, {"researchbase.bearing_enabled": "true"}, {"researchbase.consumer_generation": "spoof"}],
)
def test_complete_candidate_denied_by_disabled_guard_not_missing_privileges(d1, binding, settings):
    task, session = prepared_task(d1, binding)
    before = snapshot(d1)
    with pytest.raises(DBAPIError) as error, d1.engine.begin() as conn:
        assert (
            conn.scalar(text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")) is False
        )
        for table in ("budget_reservations", "experiment_search_nodes", "research_task_events"):
            assert conn.scalar(
                text("SELECT has_table_privilege(current_user,:t,'INSERT')"), {"t": table}
            )
        for key, value in settings.items():
            conn.execute(text("SELECT set_config(:key,:value,true)"), {"key": key, "value": value})
        assert conn.scalar(text("SELECT pr316d1_enabled()")) is False
        candidate(conn, d1, binding, task, session)
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert constraint(error) == "pr316d1_disabled"
    assert snapshot(d1) == before


@pytest.mark.parametrize(
    "omit", ["receipt", "reservation", "node", "search_event", "task_event", "association"]
)
def test_missing_effects_roll_back_every_new_row(d1, binding, omit):
    task, session = prepared_task(d1, binding)
    before = snapshot(d1)
    with pytest.raises(DBAPIError), d1.engine.begin() as conn:
        candidate(conn, d1, binding, task, session, omit=omit)
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert snapshot(d1) == before


def test_extra_effect_rolls_back_full_candidate(d1, binding):
    task, session = prepared_task(d1, binding)
    before = snapshot(d1)
    with pytest.raises(DBAPIError) as error, d1.engine.begin() as conn:
        candidate(conn, d1, binding, task, session, extra=True)
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert constraint(error) == "pr301_validation"
    assert snapshot(d1) == before


def test_shorter_dto_deadline_cannot_clip_reserved_w(d1, binding):
    task, session = prepared_task(d1, binding)
    before = snapshot(d1)
    with pytest.raises(DBAPIError) as error, d1.engine.begin() as conn:
        candidate(conn, d1, binding, task, session, change={"deadline_seconds": 119})
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert constraint(error) == "pr316d1_admission"
    assert snapshot(d1) == before


@pytest.mark.parametrize("column", COLUMNS)
def test_legacy_reservation_binding_is_immutable_including_noop(d1, column):
    p = d1.p
    task = p.create()
    from tests.integration.phase3.test_pr3_04_application import bind

    bind(p, task)
    approve(p, task, 2)
    legacy = TrustedFakeConsumer(p.factory, Credentials(), p.store)
    result = legacy.execute(p.principal, reserve(p, task, 4))
    with pytest.raises(DBAPIError) as error, d1.engine.begin() as conn:
        conn.execute(
            text(f"UPDATE budget_reservations SET {column}={column} WHERE id=:id"),
            {"id": result.reservation_ids[0]},
        )
    assert constraint(error) == "pr301_immutable"


def test_public_legacy_search_safety_replay_and_cancel_recovery_on_upgraded_head(d1):
    from tests.integration.phase3.test_pr3_04_application import bind

    p = d1.p
    task = p.create()
    c, _ = bind(p, task)
    assert service(p).execute(p.principal, c).command_result.replayed
    approve(p, task, 2)
    search = ExperimentSearchService(p.factory, Credentials())
    create = SearchCommand(
        p.project, new_uuid7(), task, 4, "create_search_session", CreateSearchArguments(new_uuid7())
    )
    result = search.execute(p.principal, create)
    assert search.execute(p.principal, create).command_result.replayed
    assert result.command_result.resulting_row_version == 5
    legacy = TrustedFakeConsumer(p.factory, Credentials(), p.store)
    reserved = legacy.execute(p.principal, reserve(p, task, 5))
    p.service.execute(
        p.principal,
        p.command("cancel_research_task", task, 6, {"reason": "Cancel after reservation."}),
    )
    observed = legacy.execute(p.principal, settle(p, task, 7, reserved.reservation_ids[0]))
    assert len(observed.usage_record_ids) == 1
    with d1.engine.connect() as conn:
        assert (
            conn.scalar(
                text(
                    "SELECT count(*) FROM budget_reservations WHERE consumer_generation IS NOT NULL"
                )
            )
            == 0
        )


def test_new_helpers_have_no_dml_and_no_test_enable_hook():
    spec = importlib.util.spec_from_file_location(
        "d1_migration", "migrations/versions/0083_bearing_evaluation_guards.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for body in (module.AUTHORITY, module.ADMISSION, module.VALIDATE):
        assert not re.search(r"(?im)^\s*(INSERT INTO|UPDATE |DELETE FROM)", body)
    assert (
        "SELECT false" in Path("migrations/versions/0083_bearing_evaluation_guards.py").read_text()
    )


@pytest.mark.parametrize("column", COLUMNS[:-1])
def test_nonexistent_binding_rejected_by_named_immediate_fk(d1, binding, column):
    task, session = prepared_task(d1, binding)
    before = snapshot(d1)
    with pytest.raises(DBAPIError) as error, d1.engine.begin() as conn:
        candidate(conn, d1, replace(binding, **{column: new_uuid7()}), task, session)
    assert constraint(error) in FKS
    assert snapshot(d1) == before


def test_binding_hash_reconstructed_from_owner_and_accounting_reason(d1, binding):
    task, session = prepared_task(d1, binding)
    before = snapshot(d1)
    with pytest.raises(DBAPIError) as error, d1.engine.begin() as conn:
        candidate(conn, d1, replace(binding, labels_content_hash="0" * 64), task, session)
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert constraint(error) == "pr316_provenance"
    assert snapshot(d1) == before


def test_partial_binding_sql_attack_cannot_commit(d1, binding):
    task, session = prepared_task(d1, binding)
    before = snapshot(d1)
    with pytest.raises(DBAPIError) as error, d1.engine.begin() as conn:
        candidate(
            conn,
            d1,
            binding,
            task,
            session,
            reservation_changes={"labels_artifact_version_id": None},
        )
    assert constraint(error) == "pr316d1_reservation_binding_shape_ck"
    assert snapshot(d1) == before


def test_last_unit_candidate_reaches_disabled_gate_with_durable_stop_shape(d1, binding):
    task, session = prepared_task(d1, binding, tree_cap=1)
    before = snapshot(d1)
    with pytest.raises(DBAPIError) as error, d1.engine.begin() as conn:
        candidate(conn, d1, binding, task, session, stop_budget=True)
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert constraint(error) == "pr316d1_disabled"
    assert snapshot(d1) == before


def test_prior_legacy_scored_nullable_step_scope_rejects_v2(d1, binding):
    p = d1.p
    task, session = prepared_task(d1, binding)
    approve(p, task, 5, kind="code_risk")
    legacy = TrustedFakeConsumer(p.factory, Credentials(), p.store)
    reserved = legacy.execute(p.principal, reserve(p, task, 7, code_iterations=1))
    observation = settle(
        p, task, 8, reserved.reservation_ids[0], measured=resources(code_iterations=1)
    )
    observation = replace(
        observation,
        arguments=replace(
            observation.arguments, score=Decimal("0.100000"), evaluator_version="paired-test-v1"
        ),
    )
    legacy.execute(p.principal, observation)
    before = snapshot(d1)
    with pytest.raises(DBAPIError) as error, d1.engine.begin() as conn:
        candidate(conn, d1, binding, task, session)
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert constraint(error) == "pr316d1_comparison"
    assert snapshot(d1) == before


def test_v2_settlement_cannot_take_legacy_reservation(d1, binding):
    from tests.integration.phase3.test_pr3_04_application import bind

    p = d1.p
    task = p.create()
    bind(p, task)
    approve(p, task, 2)
    legacy = TrustedFakeConsumer(p.factory, Credentials(), p.store)
    reserved = legacy.execute(p.principal, reserve(p, task, 4))
    before = snapshot(d1)
    with pytest.raises(DBAPIError) as error, d1.engine.begin() as conn:
        cid, rid = new_uuid7(), new_uuid7()
        lock(conn, p.project, p.principal.actor_id, cid, task)
        conn.execute(text("UPDATE research_tasks SET row_version=6 WHERE id=:id"), {"id": task})
        at = conn.scalar(text("SELECT transaction_timestamp()"))
        insert(
            conn,
            "research_task_command_receipts",
            dict(
                id=rid,
                project_id=p.project,
                actor_id=p.principal.actor_id,
                command_id=cid,
                research_task_id=task,
                command_name="settle_bearing_evaluation_v2",
                request_hash="0" * 64,
                hash_scheme="sha256-cjson-v1",
                material_version=2,
                resulting_row_version=6,
                completed_at=at,
            ),
        )
        insert(
            conn,
            "budget_usage_records",
            dict(
                id=new_uuid7(),
                research_task_id=task,
                reservation_id=reserved.reservation_ids[0],
                receipt_id=rid,
                created_at=at,
                settled_at=at,
                outcome="FAILED",
                is_final=True,
                failure_streak=1,
                no_improvement_streak=0,
                **resources(),
            ),
        )
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert constraint(error) == "pr316d1_binding"
    assert snapshot(d1) == before


def load_migration(name):
    spec = importlib.util.spec_from_file_location(name, "migrations/versions/" + name + ".py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_all_nine_body_edits_match_frozen_current_sources_and_preserve_gateway_branches():
    """Source-anchor proof complements, and cannot replace, PG compilation/catalog proof."""
    old = load_migration("0082_experiment_search_core")
    gateway = load_migration("0080_capability_gateway")
    new = load_migration("0083_bearing_evaluation_guards")
    text_sql = old.SCALAR_FUNCTIONS + old.GUARDS + old.RECEIPT_COMPLETE
    routines = {}
    for match in re.finditer(r"CREATE (?:OR REPLACE )?FUNCTION (\w+)\(.*?\$\$;", text_sql, re.S):
        routines[match[1]] = match[0]
    routines["pr304_child_guard"] = gateway.PR304_CHILD_GUARD_SQL
    routines["pr304_validate_safety"] = gateway.PR304_VALIDATE_SAFETY_SQL
    signatures = {
        "pr316_command_event": "text",
        "pr316_node_proof": "experiment_search_nodes",
        "pr316_state": "research_task_command_receipts,experiment_search_events",
        "pr316_validate_receipt": "uuid",
        "pr304_validate_safety": "uuid",
    }
    for name in CHANGED_FUNCTIONS:
        original = routines[name]
        changed = new.amend_function(name + "(" + signatures.get(name, "") + ")", original)
        assert original != changed
        assert original.split("AS $$", 1)[0] == changed.split("AS $$", 1)[0]
        # Every pre-existing exception remains, along with its owning error branches.
        assert set(re.findall(r"RAISE EXCEPTION\s+'([^']*)'", original)) <= set(
            re.findall(r"RAISE EXCEPTION\s+'([^']*)'", changed)
        )
        if name == "pr316_validate_receipt":
            assert changed.index("pr316d1_validate_receipt") < changed.index("search_command:=")
            assert "te.reason IS DISTINCT FROM e.reason" in changed
        if name == "pr316_node_proof":
            assert "pr316_activation" in changed and "pr316_admission(n.research_task_id" in changed
        if name == "pr304_validate_safety":
            assert "'request_capability_invocation','finish_capability_invocation'" in changed
            assert "scientific execution prerequisites unavailable in fake slice" in changed
            assert "counterfeit streak" in changed


def test_cross_project_frozen_artifact_metadata_denied(d1, binding):
    from researchbase.application.commands import CreateProjectCommand

    p = d1.p
    app = LegacyApplicationService(p.factory, SystemClock(), p.store)
    ctx = ExecutionContext(
        actor_id=p.principal.actor_id, request_id=new_uuid7(), client_type="test"
    )
    foreign_project = app.create_project(CreateProjectCommand("Foreign D1 fixture", None, ctx))
    foreign = _artifact(
        p.factory, p.store, p.principal, ProjectId(foreign_project.id), b"foreign labels", "other"
    )
    task, session = prepared_task(d1, binding)
    before = snapshot(d1)
    with pytest.raises(DBAPIError) as error, d1.engine.begin() as conn:
        candidate(conn, d1, replace(binding, labels_artifact_version_id=foreign), task, session)
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert constraint(error) == "pr316d1_binding"
    assert snapshot(d1) == before


def test_draft_artifact_is_not_a_frozen_binding(d1, binding):
    from researchbase.application.commands import (
        CreateArtifactCommand,
        CreateArtifactVersionCommand,
    )
    from researchbase.domain.artifact import ArtifactId

    p = d1.p
    app = LegacyApplicationService(p.factory, SystemClock(), p.store)
    ctx = ExecutionContext(
        actor_id=p.principal.actor_id, request_id=new_uuid7(), client_type="test"
    )
    artifact = app.create_artifact(
        CreateArtifactCommand(ProjectId(p.project), "other", "Draft", None, ctx)
    )
    version = app.create_artifact_version(
        CreateArtifactVersionCommand(
            ArtifactId(artifact.id), b"draft", None, None, "text/plain", 5, None, ctx
        )
    )
    task, session = prepared_task(d1, binding)
    before = snapshot(d1)
    with pytest.raises(DBAPIError) as error, d1.engine.begin() as conn:
        candidate(conn, d1, replace(binding, labels_artifact_version_id=version.id), task, session)
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert constraint(error) == "pr316d1_binding"
    assert snapshot(d1) == before


def test_legacy_receipt_cannot_own_complete_v2_binding(d1, binding):
    p = d1.p
    task, _ = prepared_task(d1, binding)
    before = snapshot(d1)
    with pytest.raises(DBAPIError) as error, d1.engine.begin() as conn:
        cid, rid = new_uuid7(), new_uuid7()
        lock(conn, p.project, p.principal.actor_id, cid, task)
        conn.execute(text("UPDATE research_tasks SET row_version=6 WHERE id=:id"), {"id": task})
        at = conn.scalar(text("SELECT transaction_timestamp()"))
        insert(
            conn,
            "research_task_command_receipts",
            dict(
                id=rid,
                project_id=p.project,
                actor_id=p.principal.actor_id,
                command_id=cid,
                research_task_id=task,
                command_name="reserve_task_budget",
                request_hash="0" * 64,
                hash_scheme="sha256-cjson-v1",
                material_version=1,
                resulting_row_version=6,
                completed_at=at,
            ),
        )
        bid = conn.scalar(
            text("SELECT budget_policy_id FROM research_tasks WHERE id=:id"), {"id": task}
        )
        deadline = conn.scalar(text("SELECT transaction_timestamp()+interval '1 second'"))
        insert(
            conn,
            "budget_reservations",
            dict(
                id=new_uuid7(),
                research_task_id=task,
                receipt_id=rid,
                created_at=at,
                budget_id=bid,
                operation_id=new_uuid7(),
                step_id=None,
                deadline=deadline,
                observed_depth=0,
                observed_parallel_branches=1,
                **resources(),
                **{column: getattr(binding, column) for column in COLUMNS},
            ),
        )
    assert constraint(error) == "pr316d1_binding"
    assert snapshot(d1) == before


def test_unexpected_helper_default_acl_refuses_upgrade_transactionally():
    with disposable_database("researchbase_pr212_test_") as url:
        upgrade(url, PARENT)
        engine = create_engine(url)
        try:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC")
                )
            before = catalog_snapshot(engine)
            with pytest.raises(RuntimeError, match="unexpected helper default grants"):
                upgrade(url, HEAD)
            assert catalog_snapshot(engine) == before
            with engine.connect() as conn:
                assert conn.scalar(text("SELECT version_num FROM alembic_version")) == PARENT
                assert conn.scalar(text("SELECT to_regprocedure('pr316d1_enabled()')")) is None
        finally:
            engine.dispose()


def test_amended_check_metadata_matches_public_catalog(d1):
    with d1.engine.begin() as conn:
        for table in ("research_task_command_receipts", "research_task_events"):
            temp = "metadata_" + table
            conn.execute(text(f"CREATE TEMP TABLE {temp} (LIKE public.{table})"))
            checks = {
                c.name: c
                for c in Base.metadata.tables[table].constraints
                if isinstance(c, CheckConstraint) and c.name in CHANGED_CHECKS
            }
            for name, check in checks.items():
                conn.execute(
                    text(f'ALTER TABLE {temp} ADD CONSTRAINT "{name}" CHECK ({check.sqltext})')
                )
            actual = dict(
                conn.execute(
                    text(
                        "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                        "WHERE conrelid=CAST(:table AS regclass) AND conname=ANY(:names)"
                    ),
                    {"table": "public." + table, "names": list(checks)},
                ).all()
            )
            compiled = dict(
                conn.execute(
                    text(
                        "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                        "WHERE conrelid=CAST(:table AS regclass) AND conname=ANY(:names)"
                    ),
                    {"table": temp, "names": list(checks)},
                ).all()
            )
            assert actual == compiled
            assert set(actual) == set(checks)
        assert (
            sum(
                c.name in CHANGED_CHECKS
                for table in ("research_task_command_receipts", "research_task_events")
                for c in Base.metadata.tables[table].constraints
            )
            == 7
        )
