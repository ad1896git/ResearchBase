# ruff: noqa: E501
"""Normal-role adversarial SQL, exact catalog and deferred graph enforcement."""

from time import monotonic

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from tests.integration.phase3.conftest import raw_plan

from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.database import Base
from researchbase.persistence.research_task_repository import (
    SqlAlchemyResearchTaskRepository,
)


def _function_counts(rows):
    return {str(r[0]): int(r[1]) for r in rows}


def test_exact_catalog_and_two_final_checks(planning):
    with planning.engine.connect() as conn:
        tables = (
            conn.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'research_task%' ORDER BY tablename"
                )
            )
            .scalars()
            .all()
        )
        assert len(tables) == 10
        triggers = conn.execute(
            text(
                "SELECT tgname,tgdeferrable,tginitdeferred FROM pg_trigger WHERE tgname LIKE 'pr301_%' ORDER BY tgname"
            )
        ).all()
        assert len(triggers) == 19
        assert sum(r.tgdeferrable for r in triggers) == 4
        assert {r.tgname for r in triggers if r.tgdeferrable} == {
            "pr301_task_final",
            "pr301_receipt_complete_commit",
            "pr301_dependency_acyclic_commit",
            "pr301_parent_acyclic_commit",
        }
        assert (
            conn.execute(
                text("SELECT count(*) FROM pg_proc WHERE proname LIKE 'pr301_%'")
            ).scalar_one()
            == 14
        )
        indexes = (
            conn.execute(
                text(
                    "SELECT indexname FROM pg_indexes WHERE schemaname='public' AND indexname LIKE 'pr301_%'"
                )
            )
            .scalars()
            .all()
        )
        assert len(indexes) == 34
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM pg_constraint WHERE conrelid IN (SELECT oid FROM pg_class WHERE relname LIKE 'research_task%') AND contype='f' AND confdeltype<>'r'"
                )
            ).scalar_one()
            == 0
        )
        for table in tables:
            assert not any(
                c["type"].__class__.__name__ in {"JSON", "JSONB"}
                for c in inspect(conn).get_columns(table)
            )
            assert set(Base.metadata.tables[table].columns.keys()) == {
                c["name"] for c in inspect(conn).get_columns(table)
            }
        fk = next(
            f
            for f in inspect(conn).get_foreign_keys("research_tasks")
            if f["name"] == "pr301_current_step_same_task"
        )
        assert fk["constrained_columns"] == ["id", "current_step_id"]


def test_ordinary_normal_role_plan_commits(planning, normal_engine):
    task = planning.create()
    a, b = new_uuid7(), new_uuid7()
    with Session(normal_engine) as session, session.begin():
        repo = SqlAlchemyResearchTaskRepository(session)
        raw_plan(repo, planning, task, [(a, 1, None), (b, 2, a)], [(a, b)])
        repo.force_constraints()
    graph = planning.service.get_task_graph(planning.principal, planning.project, task)
    assert len(graph.nodes) == 2 and len(graph.edges) == 1


@pytest.mark.parametrize(
    "case",
    (
        "edge_cycle",
        "parent_cycle",
        "self",
        "duplicate",
        "cross_task",
        "last_edge",
        "later_edit",
        "later_parent",
    ),
)
def test_bad_sql_graph_rolls_back(planning, normal_engine, case):
    task = planning.create()
    a, b, c = new_uuid7(), new_uuid7(), new_uuid7()
    nodes = [(a, 1, None), (b, 2, None), (c, 3, None)]
    edges = [(a, b)]
    if case == "edge_cycle":
        edges.append((b, a))
    elif case == "parent_cycle":
        nodes = [(a, 1, b), (b, 2, a), (c, 3, None)]
    elif case == "self":
        edges = [(a, a)]
    elif case == "duplicate":
        edges *= 2
    elif case == "cross_task":
        edges = [(a, new_uuid7())]
    elif case == "last_edge":
        edges = [(a, b), (b, c), (c, a)]
    with pytest.raises(DBAPIError):
        with Session(normal_engine) as session, session.begin():
            repo = SqlAlchemyResearchTaskRepository(session)
            raw_plan(repo, planning, task, nodes, edges)
            if case == "later_edit":
                session.flush()
                session.execute(
                    text(
                        "UPDATE research_task_step_dependencies SET predecessor_id=:b,dependent_id=:a WHERE research_task_id=:t AND predecessor_id=:a"
                    ),
                    {"t": task, "a": a, "b": b},
                )
                repo.insert(
                    "research_task_step_dependencies",
                    {"research_task_id": task, "predecessor_id": a, "dependent_id": b},
                )
            if case == "later_parent":
                session.flush()
                session.execute(
                    text(
                        "UPDATE research_task_steps SET parent_step_id=CASE WHEN id=:a THEN :b ELSE :a END WHERE research_task_id=:t AND id IN (:a,:b)"
                    ),
                    {"t": task, "a": a, "b": b},
                )
            repo.force_constraints()
    assert (
        planning.service.get_research_task(planning.principal, planning.project, task).row_version
        == 1
    )


@pytest.mark.parametrize(
    "table",
    (
        "research_task_steps",
        "research_task_step_dependencies",
        "research_task_inputs",
        "research_task_step_inputs",
        "research_task_command_receipts",
    ),
)
def test_child_requires_current_transaction_task_revision(planning, normal_engine, table):
    task, cmd = planning.plan()
    graph = planning.service.get_task_graph(planning.principal, planning.project, task)
    with pytest.raises(DBAPIError) as caught:
        with normal_engine.begin() as conn:
            if table == "research_task_steps":
                conn.execute(
                    text(
                        "INSERT INTO research_task_steps(id,research_task_id,step_type,ordinal,status,row_version) VALUES (:id,:t,'PLAN',3,'PENDING',1)"
                    ),
                    {"id": new_uuid7(), "t": task},
                )
            else:
                # Copying any committed row is still a later-transaction insertion attempt.
                columns = {
                    "research_task_step_dependencies": "research_task_id,predecessor_id,dependent_id",
                    "research_task_inputs": "id,research_task_id,content_hash",
                    "research_task_step_inputs": "id,research_task_id,step_id,content_hash",
                    "research_task_command_receipts": "id,project_id,actor_id,command_id,command_name,research_task_id,request_hash,hash_scheme,material_version,resulting_row_version,completed_at",
                }[table]
                if table == "research_task_step_dependencies":
                    conn.execute(
                        text(f"INSERT INTO {table}({columns}) VALUES (:t,:a,:b)"),
                        {"t": task, "a": graph.nodes[0].id, "b": graph.nodes[1].id},
                    )
                elif table == "research_task_inputs":
                    conn.execute(
                        text(f"INSERT INTO {table}({columns}) VALUES (:id,:t,:hash)"),
                        {"id": new_uuid7(), "t": task, "hash": "a" * 64},
                    )
                elif table == "research_task_step_inputs":
                    conn.execute(
                        text(f"INSERT INTO {table}({columns}) VALUES (:id,:t,:s,:hash)"),
                        {"id": new_uuid7(), "t": task, "s": graph.nodes[0].id, "hash": "a" * 64},
                    )
                else:
                    conn.execute(
                        text(
                            f"INSERT INTO {table}({columns}) SELECT {columns} FROM {table} WHERE research_task_id=:t LIMIT 1"
                        ),
                        {"t": task},
                    )
    assert (
        getattr(getattr(caught.value.orig, "diag", None), "constraint_name", None)
        == "pr301_immutable"
    )


@pytest.mark.parametrize(
    "table",
    (
        "research_task_events",
        "research_task_step_events",
        "research_task_command_receipts",
        "research_task_receipt_events",
        "research_task_receipt_step_events",
    ),
)
@pytest.mark.parametrize("operation", ("UPDATE", "DELETE", "INSERT"))
def test_committed_history_cannot_change_or_grow(planning, normal_engine, table, operation):
    task, cmd = planning.plan()
    with pytest.raises(DBAPIError):
        with normal_engine.begin() as conn:
            if operation == "UPDATE":
                col = (
                    "receipt_id"
                    if "receipt_" in table and table != "research_task_command_receipts"
                    else "id"
                )
                conn.execute(
                    text(f"UPDATE {table} SET {col}={col} WHERE research_task_id=:t"), {"t": task}
                )
            elif operation == "DELETE":
                conn.execute(text(f"DELETE FROM {table} WHERE research_task_id=:t"), {"t": task})
            else:
                conn.execute(
                    text(
                        f"INSERT INTO {table} SELECT * FROM {table} WHERE research_task_id=:t LIMIT 1"
                    ),
                    {"t": task},
                )


@pytest.mark.parametrize(
    "table", ("research_tasks", "research_task_steps", "research_task_step_dependencies")
)
@pytest.mark.parametrize("sealed", (False, True))
def test_material_immutable_and_delete_denied(planning, normal_engine, table, sealed):
    task, _ = planning.plan()
    graph = planning.service.get_task_graph(planning.principal, planning.project, task)
    planning.service.execute(
        planning.principal,
        planning.command(
            "add_task_step_dependency",
            task,
            2,
            {"predecessor_id": str(graph.nodes[0].id), "dependent_id": str(graph.nodes[1].id)},
        ),
    )
    if sealed:
        planning.service.execute(planning.principal, planning.command("seal_task_plan", task, 3))
    for op in ("UPDATE", "DELETE"):
        with pytest.raises(DBAPIError):
            with normal_engine.begin() as conn:
                if op == "UPDATE":
                    if table == "research_tasks":
                        conn.execute(
                            text("UPDATE research_tasks SET objective=objective WHERE id=:t"),
                            {"t": task},
                        )
                    elif table == "research_task_steps":
                        conn.execute(
                            text(
                                "UPDATE research_task_steps SET ordinal=ordinal WHERE research_task_id=:t"
                            ),
                            {"t": task},
                        )
                    else:
                        graph = planning.service.get_task_graph(
                            planning.principal, planning.project, task
                        )
                        conn.execute(
                            text("INSERT INTO research_task_step_dependencies VALUES (:t,:a,:b)"),
                            {"t": task, "a": graph.nodes[0].id, "b": graph.nodes[1].id},
                        )
                else:
                    # Empty dependency relation receives an edge before the test in the other cases.
                    conn.execute(
                        text(
                            f"DELETE FROM {table} WHERE "
                            + ("id" if table == "research_tasks" else "research_task_id")
                            + "=:t"
                        ),
                        {"t": task},
                    )


def test_1024_edge_commit_timing_and_one_final_firing(planning, normal_engine, tmp_path):
    task = planning.create()
    nodes = [(new_uuid7(), i + 1, None) for i in range(256)]
    edges = [(nodes[i][0], nodes[j][0]) for i in range(256) for j in range(i + 1, 256)][:1024]
    # pg_stat_xact_user_functions provides actual firing counts in this transaction.
    with Session(normal_engine) as session, session.begin():
        repo = SqlAlchemyResearchTaskRepository(session)
        repo.lock_write(planning.project, planning.principal.actor_id, new_uuid7(), task)
        baseline = _function_counts(
            session.execute(
                text(
                    "SELECT funcname,calls FROM pg_stat_xact_user_functions WHERE funcname IN ('pr301_graph_final_guard','pr301_receipt_complete')"
                )
            ).all()
        )
        raw_plan(repo, planning, task, nodes, edges, prepare=False)
        start = monotonic()
        repo.force_constraints()
        elapsed = monotonic() - start
        assert elapsed < 10
        # Exactly one deferred task and receipt trigger is queued: one task write/receipt.
        task_writes = session.execute(
            text(
                "SELECT count(*) FROM research_task_events WHERE research_task_id=:t AND task_row_version=2"
            ),
            {"t": task},
        ).scalar_one()
        receipts = session.execute(
            text(
                "SELECT count(*) FROM research_task_command_receipts WHERE research_task_id=:t AND resulting_row_version=2"
            ),
            {"t": task},
        ).scalar_one()
        assert task_writes == receipts == 1
        calls = _function_counts(
            session.execute(
                text(
                    "SELECT funcname,calls FROM pg_stat_xact_user_functions WHERE funcname IN ('pr301_graph_final_guard','pr301_receipt_complete')"
                )
            ).all()
        )
        assert {name: count - baseline.get(name, 0) for name, count in calls.items()} == {
            "pr301_graph_final_guard": 1,
            "pr301_receipt_complete": 1,
        }
    commit_elapsed = monotonic() - start
    assert commit_elapsed < 10
    (tmp_path / "maximum-plan-timing.txt").write_text(
        f"256 nodes; 1024 edges; SET CONSTRAINTS ALL IMMEDIATE={elapsed:.6f}s; bound=10s\n"
    )
    print(
        f"PR301_MAXIMUM_PLAN: nodes=256 edges=1024 deferred_seconds={elapsed:.6f} commit_seconds={commit_elapsed:.6f} bound_seconds=10"
    )


@pytest.mark.parametrize(
    "kind",
    (
        "RESEARCH_QUESTION_VERSION",
        "HYPOTHESIS_VERSION",
        "CLAIM_VERSION",
        "SOURCE_VERSION",
        "ARTIFACT_VERSION",
        "MANUSCRIPT_VERSION",
    ),
)
@pytest.mark.parametrize("step", (False, True), ids=("task-input", "step-input"))
def test_six_families_at_both_owners(planning, scientific_inputs, kind, step):
    binding = {"type": kind, "id": str(scientific_inputs[kind])}
    cmd = planning.command(
        arguments={
            "task_type": "ANALYSIS",
            "objective": "Inspect exact history",
            "strategy_id": "human_guided_research",
            "strategy_version": "1.0.0",
            "inputs": [] if step else [binding],
        }
    )
    planning.service.execute(planning.principal, cmd)
    task = cmd.task_id
    if step:
        planning.plan(
            task,
            nodes=[
                {
                    "step_id": str(new_uuid7()),
                    "step_type": "ANALYZE",
                    "ordinal": 1,
                    "inputs": [binding],
                }
            ],
        )
    else:
        planning.plan(task)
    planning.service.execute(planning.principal, planning.command("seal_task_plan", task, 2))
    graph = planning.service.get_task_graph(planning.principal, planning.project, task)
    inputs = graph.nodes[0].inputs if step else graph.task.inputs
    assert len(inputs) == 1 and inputs[0].id == scientific_inputs[kind]
    assert (inputs[0].hash_scheme == "sha256-cjson-v1") == (
        kind in {"SOURCE_VERSION", "MANUSCRIPT_VERSION"}
    )


@pytest.mark.parametrize(
    "kind",
    (
        "RESEARCH_QUESTION_VERSION",
        "HYPOTHESIS_VERSION",
        "CLAIM_VERSION",
        "SOURCE_VERSION",
        "ARTIFACT_VERSION",
        "MANUSCRIPT_VERSION",
    ),
)
@pytest.mark.parametrize("step", (False, True))
@pytest.mark.parametrize("case", ("zero", "multiple", "hash", "scheme", "duplicate"))
def test_input_constraints_adversarial_sql(
    planning, normal_engine, scientific_inputs, kind, step, case
):
    from researchbase.persistence.research_task_queries import INPUT_FAMILIES

    task = planning.create()
    node = new_uuid7()
    with pytest.raises(DBAPIError):
        with Session(normal_engine) as session, session.begin():
            repo = SqlAlchemyResearchTaskRepository(session)
            raw_plan(repo, planning, task, [(node, 1, None)], [])
            column = INPUT_FAMILIES[kind][0]
            version = repo.input_version(kind, scientific_inputs[kind], planning.project)
            assert version is not None
            row = {
                "id": new_uuid7(),
                "research_task_id": task,
                column: scientific_inputs[kind],
                "content_hash": version["content_hash"],
                "hash_scheme": version.get("hash_scheme")
                if kind in {"SOURCE_VERSION", "MANUSCRIPT_VERSION"}
                else None,
            }
            if step:
                row["step_id"] = node
            if case == "zero":
                row[column] = None
            elif case == "multiple":
                other = "CLAIM_VERSION" if kind != "CLAIM_VERSION" else "HYPOTHESIS_VERSION"
                row[INPUT_FAMILIES[other][0]] = scientific_inputs[other]
            elif case == "hash":
                row["content_hash"] = "0" * 64
            elif case == "scheme":
                row["hash_scheme"] = None if row["hash_scheme"] else "sha256-cjson-v1"
            table = "research_task_step_inputs" if step else "research_task_inputs"
            repo.insert(table, row)
            if case == "duplicate":
                repo.insert(table, {**row, "id": new_uuid7()})
            repo.force_constraints()


@pytest.mark.parametrize(
    "kind",
    (
        "RESEARCH_QUESTION_VERSION",
        "HYPOTHESIS_VERSION",
        "CLAIM_VERSION",
        "SOURCE_VERSION",
        "ARTIFACT_VERSION",
        "MANUSCRIPT_VERSION",
    ),
)
def test_all_input_families_cross_project_or_unlinked_source_denied(
    planning, normal_engine, scientific_inputs, kind
):
    from researchbase.persistence.research_task_queries import INPUT_FAMILIES

    project = new_uuid7()
    with planning.engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO projects(id,name,created_by,created_at) VALUES (:id,'Foreign project',:actor,clock_timestamp())"
            ),
            {"id": project, "actor": planning.principal.actor_id},
        )
    task = new_uuid7()
    with pytest.raises(DBAPIError) as caught:
        with Session(normal_engine) as session, session.begin():
            repo = SqlAlchemyResearchTaskRepository(session)
            repo.lock_write(project, planning.principal.actor_id, new_uuid7(), task)
            at = repo.at()
            repo.insert(
                "research_tasks",
                {
                    "id": task,
                    "project_id": project,
                    "requested_by": planning.principal.actor_id,
                    "task_type": "OTHER",
                    "objective": "Foreign",
                    "strategy_id": "fixed",
                    "strategy_version": "1",
                    "autonomy_level": "A0",
                    "status": "CREATED",
                    "created_at": at,
                    "row_version": 1,
                },
            )
            version = repo.input_version(kind, scientific_inputs[kind], planning.project)
            assert version is not None
            repo.insert(
                "research_task_inputs",
                {
                    "id": new_uuid7(),
                    "research_task_id": task,
                    INPUT_FAMILIES[kind][0]: scientific_inputs[kind],
                    "content_hash": version["content_hash"],
                    "hash_scheme": version.get("hash_scheme")
                    if kind in {"SOURCE_VERSION", "MANUSCRIPT_VERSION"}
                    else None,
                },
            )
    assert (
        getattr(getattr(caught.value.orig, "diag", None), "constraint_name", None) == "pr301_scope"
    )


def test_null_artifact_project_never_grants_input_scope(planning):
    from tests.integration.phase2.test_pr2_10_binding_contract import _artifact

    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    artifact = _artifact(
        planning.factory, planning.store, planning.principal, None, b"global input"
    )
    cmd = planning.command(
        arguments={
            "task_type": "OTHER",
            "objective": "Global artifact",
            "strategy_id": "fixed",
            "strategy_version": "1",
            "inputs": [{"type": "ARTIFACT_VERSION", "id": str(artifact)}],
        }
    )
    with pytest.raises(ResearchBaseError) as caught:
        planning.service.execute(planning.principal, cmd)
    assert caught.value.code == ErrorCode.FORBIDDEN


@pytest.mark.parametrize(
    "kind",
    (
        "RESEARCH_QUESTION_VERSION",
        "HYPOTHESIS_VERSION",
        "CLAIM_VERSION",
        "SOURCE_VERSION",
        "ARTIFACT_VERSION",
        "MANUSCRIPT_VERSION",
    ),
)
@pytest.mark.parametrize("step", (False, True))
def test_missing_frozen_timestamp_or_hash_is_rejected(
    planning, normal_engine, draft_inputs, kind, step
):
    from researchbase.persistence.research_task_queries import INPUT_FAMILIES

    task = planning.create()
    node = new_uuid7()
    with pytest.raises(DBAPIError) as caught:
        with Session(normal_engine) as session, session.begin():
            repo = SqlAlchemyResearchTaskRepository(session)
            raw_plan(repo, planning, task, [(node, 1, None)], [])
            row = {
                "id": new_uuid7(),
                "research_task_id": task,
                INPUT_FAMILIES[kind][0]: draft_inputs[kind],
                "content_hash": "a" * 64,
                "hash_scheme": "sha256-cjson-v1"
                if kind in {"SOURCE_VERSION", "MANUSCRIPT_VERSION"}
                else None,
            }
            if step:
                row["step_id"] = node
            repo.insert("research_task_step_inputs" if step else "research_task_inputs", row)
    assert (
        getattr(getattr(caught.value.orig, "diag", None), "constraint_name", None)
        == "pr301_not_frozen"
    )


def test_parent_same_task_fk_rejects_foreign_parent(planning, normal_engine):
    foreign, _ = planning.plan()
    parent = (
        planning.service.get_task_graph(planning.principal, planning.project, foreign).nodes[0].id
    )
    task = planning.create()
    with pytest.raises(DBAPIError):
        with Session(normal_engine) as session, session.begin():
            repo = SqlAlchemyResearchTaskRepository(session)
            raw_plan(repo, planning, task, [(new_uuid7(), 1, parent)], [])
            repo.force_constraints()


@pytest.mark.parametrize("command", ("seal_task_plan", "add_task_step_dependency"))
def test_success_history_requires_the_named_effect(planning, normal_engine, monkeypatch, command):
    from tests.integration.phase3.conftest import raw_edge

    task, _ = planning.plan()
    graph = planning.service.get_task_graph(planning.principal, planning.project, task)
    insert = SqlAlchemyResearchTaskRepository.insert

    def forged(self, table, row):
        if table == "research_task_step_dependencies":
            return
        if table == "research_task_command_receipts":
            row = {**row, "command_name": command}
        if table == "research_task_events" and command == "seal_task_plan":
            row = {**row, "event_type": "PLAN_SEALED"}
        insert(self, table, row)

    monkeypatch.setattr(SqlAlchemyResearchTaskRepository, "insert", forged)
    with pytest.raises(DBAPIError):
        with Session(normal_engine) as session, session.begin():
            raw_edge(
                SqlAlchemyResearchTaskRepository(session),
                planning,
                task,
                graph.nodes[0].id,
                graph.nodes[1].id,
            )
