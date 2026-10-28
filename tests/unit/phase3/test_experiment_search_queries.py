"""Synthetic retained history verifies reads only; no production node writer exists."""

from copy import deepcopy
from dataclasses import asdict, replace
from datetime import timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest
from tests.unit.phase3.search_fixtures import NOW, Fixture, Repository

from researchbase.agent_runtime.application.experiment_search import ExperimentSearchService
from researchbase.agent_runtime.application.search_contracts import (
    BranchLineageRequest,
    SearchReadRequest,
    parse_search_read,
)
from researchbase.agent_runtime.domain.task_safety import ADDITIVE
from researchbase.agent_runtime.ports.search_repository import StoredSearchHistory
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7


class ReadRepository(Repository):
    def search_session(self, identity):
        self.f.trace.append("session_read")
        return next(
            (
                deepcopy(r)
                for r in self.f.tables["experiment_search_sessions"]
                if r["id"] == identity
            ),
            None,
        )

    def retained_history(self, session):
        self.f.trace.append("history_read")
        return StoredSearchHistory(
            tuple(deepcopy(self.f.tables["experiment_search_nodes"])),
            tuple(deepcopy(self.f.tables["experiment_search_events"])),
            tuple(deepcopy(self.f.links)),
        )


class ReadFixture(Fixture):
    def __init__(self):
        super().__init__()
        self.repo = ReadRepository(self)
        self.session = self.run().session_id
        self.tables["human_checkpoints"].clear()
        self.links = []
        self.writes.clear()
        self.trace.clear()
        self.commits = 0
        self.request = SearchReadRequest(self.project, self.task, self.session)

    def tree(self):
        return self.service.get_experiment_search_tree(self.principal, self.request)

    def lineage(self, node):
        return self.service.get_branch_lineage(
            self.principal, BranchLineageRequest(self.project, self.task, self.session, node)
        )

    def node(self, parent=None):
        identity, reservation, receipt = (new_uuid7() for _ in range(3))
        row = dict(
            id=identity,
            research_task_id=self.task,
            search_session_id=self.session,
            parent_node_id=parent["id"] if parent else None,
            depth=parent["depth"] + 1 if parent else 0,
            branch_kind="NEW_DIRECTION",
            mutation_reason="Retained unexecuted branch",
            hypothesis_version_id=None,
            hypothesis_content_hash=None,
            experiment_spec_version_id=None,
            experiment_spec_content_hash=None,
            reservation_id=reservation,
            created_by=self.actor,
            created_at=NOW,
            receipt_id=receipt,
        )
        self.tables["experiment_search_nodes"].append(row)
        self.tables["experiment_search_events"].append(
            dict(
                id=new_uuid7(),
                research_task_id=self.task,
                search_session_id=self.session,
                node_id=identity,
                sequence=len(self.tables["experiment_search_events"]) + 1,
                event_type="NODE_APPENDED",
                reason="Retained branch",
                actor_id=self.actor,
                occurred_at=NOW,
                receipt_id=receipt,
            )
        )
        self.tables["budget_reservations"].append(
            dict(
                id=reservation,
                research_task_id=self.task,
                budget_id=self.task_row["budget_policy_id"],
                operation_id=identity,
                created_at=NOW,
                deadline=NOW + timedelta(seconds=60),
                observed_depth=row["depth"],
                **dict.fromkeys(ADDITIVE, 0),
            )
        )
        return row


def denied(call, code):
    with pytest.raises(ResearchBaseError) as exc:
        call()
    assert exc.value.code == code
    assert exc.value.details is None
    assert str(exc.value) == str(
        ResearchBaseError(
            code,
            {
                ErrorCode.VALIDATION_ERROR: "Search request invalid.",
                ErrorCode.NOT_FOUND: "Search target not found.",
                ErrorCode.FORBIDDEN: "Search access denied.",
                ErrorCode.REFERENTIAL_INTEGRITY_ERROR: "Search reference invalid.",
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION: "Search provenance invalid.",
                ErrorCode.VERSION_NOT_FROZEN: "Search version not frozen.",
            }[code],
        )
    )


@pytest.mark.parametrize("kind", ["HUMAN", "AGENT"])
def test_current_run_seal_labels_and_empty_tree(kind):
    f = ReadFixture()
    f.actor_type = kind
    before = deepcopy(f.tables)
    result = f.tree()
    assert result.nodes == result.events[1:] == result.run_links == ()
    assert result.session.status == "ACTIVE"
    assert result.events[0].event_type == "SESSION_CREATED"
    assert not hasattr(result, "success") and not result.task_safety.execution_enabled
    assert f.tables == before and not f.writes and f.commits == 0
    assert f.trace.count("read_begin") == 1
    assert f.trace.index("authority") < f.trace.index("task_read")


def test_scope_hash_and_ordering_follow_frozen_read_contract():
    f = ReadFixture()
    root = f.node()
    child = f.node(root)
    sibling = f.node(root)
    leaf = f.node(child)
    f.tables["experiment_search_nodes"].reverse()
    f.tables["experiment_search_events"].reverse()
    tree = f.tree()
    assert [n.id for n in tree.nodes] == [
        n["id"] for n in sorted([root, child, sibling, leaf], key=lambda n: (n["depth"], n["id"]))
    ]
    assert [e.sequence for e in tree.events] == list(range(1, 6))
    path = f.lineage(leaf["id"])
    assert [n.id for n in path.path] == [root["id"], child["id"], leaf["id"]]
    assert [e.node_id for e in path.events] == [leaf["id"]]
    ref = new_uuid7()
    root = next(n for n in f.tables["experiment_search_nodes"] if n["id"] == root["id"])
    root.update(hypothesis_version_id=ref, hypothesis_content_hash="a" * 64)
    f.references[ref] = dict(
        id=ref, project_id=f.project, status="SUPERSEDED", frozen_at=NOW, content_hash="a" * 64
    )
    f.owners[ref] = SimpleNamespace(content_hash="a" * 64)
    assert f.tree().nodes[0].hypothesis_content_hash == "a" * 64
    root = next(n for n in f.tables["experiment_search_nodes"] if n["id"] == root["id"])
    root["hypothesis_content_hash"] = "b" * 64
    denied(f.tree, ErrorCode.PROVENANCE_CLOSURE_VIOLATION)


def test_budget_projection_uses_same_uow():
    f = ReadFixture()
    root = f.node()
    for _ in range(3):
        f.node(root)
    # Historical siblings do not consume the parallel-reader/branch count.
    for reservation in f.tables["budget_reservations"][:-1]:
        f.tables["budget_usage_records"].append(
            dict(
                reservation_id=reservation["id"],
                is_final=True,
                failure_streak=0,
                no_improvement_streak=0,
                **dict.fromkeys(ADDITIVE, 0),
            )
        )
    before = deepcopy(f.tables)
    budget = f.service.get_search_budget(f.principal, f.request)
    assert budget.task_safety.parallel_branches == 1
    assert budget.task_safety.budget_policy_id == budget.budget_id
    assert f.trace.count("read_begin") == 1 and not f.writes and f.commits == 0
    assert f.tables == before
    f.tables["execution_budgets"][0]["max_tree_nodes"] += 1
    denied(f.tree, ErrorCode.PROVENANCE_CLOSURE_VIOLATION)


@pytest.mark.parametrize("root", [True, False])
@pytest.mark.parametrize("hypothesis", [True, False])
@pytest.mark.parametrize(
    "fault,code",
    [
        ("absent", ErrorCode.REFERENTIAL_INTEGRITY_ERROR),
        ("foreign", ErrorCode.REFERENTIAL_INTEGRITY_ERROR),
        ("draft", ErrorCode.VERSION_NOT_FROZEN),
        ("null_hash", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        ("null_ref", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        ("saved_hash", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        ("owner_hash", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
    ],
)
def test_saved_exact_reference_presence_status_scope_and_owning_hash(root, hypothesis, fault, code):
    f = ReadFixture()
    node = f.node()
    row = f.tables["experiment_search_sessions"][0] if root else node
    prefix = ("root_" if root else "") + ("hypothesis" if hypothesis else "experiment_spec")
    identity = new_uuid7()
    row[prefix + "_version_id"] = identity
    row[prefix + "_content_hash"] = "a" * 64
    f.references[identity] = dict(
        id=identity, project_id=f.project, status="FROZEN", frozen_at=NOW, content_hash="a" * 64
    )
    f.owners[identity] = SimpleNamespace(content_hash="a" * 64)
    if fault == "absent":
        f.references.clear()
    elif fault == "foreign":
        f.references[identity]["project_id"] = new_uuid7()
    elif fault == "draft":
        f.references[identity]["status"] = "DRAFT"
    elif fault == "null_hash":
        row[prefix + "_content_hash"] = None
    elif fault == "null_ref":
        row[prefix + "_version_id"] = None
    elif fault == "saved_hash":
        row[prefix + "_content_hash"] = "b" * 64
    else:
        f.owners[identity].content_hash = "b" * 64
    before = deepcopy(f.tables)
    denied(f.tree, code)
    assert f.tables == before and not f.writes


def test_goal_projection_and_response_bounds():
    f = ReadFixture()
    assert asdict(f.tree().session.objective_definition) == dict(
        source="RESEARCH_TASK", research_task_id=f.task, text="  Owning task objective e\u0301  "
    )
    root = f.node()
    for _ in range(9):
        f.node(root)
    assert len(f.tree().nodes) == 10 and len(f.tree().events) == 11
    f.node(root)
    denied(f.tree, ErrorCode.VALIDATION_ERROR)
    assert f.service.get_search_budget(f.principal, f.request).task_id == f.task
    # Lineage bounds cover the requested path, without sibling truncation.
    assert len(f.lineage(root["id"]).path) == 1


@pytest.mark.parametrize("overflow", ["depth", "events", "links"])
def test_separate_response_overflows(overflow):
    f = ReadFixture()
    root = f.node()
    if overflow == "depth":
        for _ in range(4):
            root = f.node(root)
    elif overflow == "events":
        f.tables["experiment_search_events"] *= 6
    else:
        f.links.append(dict(research_task_id=f.task, search_session_id=f.session))
    denied(f.tree, ErrorCode.VALIDATION_ERROR)
    assert not f.writes and f.commits == 0


@pytest.mark.parametrize(
    "fault", ["cycle", "orphan", "foreign", "depth", "event", "terminal", "reservation", "branch"]
)
def test_corrupt_or_unsupported_history_fails_closed(fault):
    f = ReadFixture()
    root, other = f.node(), None
    other = f.node(root)
    if fault == "cycle":
        root["parent_node_id"] = other["id"]
    elif fault == "orphan":
        other["parent_node_id"] = new_uuid7()
    elif fault == "foreign":
        other["research_task_id"] = new_uuid7()
    elif fault == "depth":
        other["depth"] = 0
    elif fault == "event":
        f.tables["experiment_search_events"][1]["node_id"] = new_uuid7()
    elif fault == "terminal":
        f.tables["experiment_search_events"][1]["event_type"] = "NODE_PRUNED"
    elif fault == "reservation":
        f.tables["budget_reservations"][0]["operation_id"] = new_uuid7()
    else:
        other["branch_kind"] = "SCIENTIFIC_SUCCESS"
    before = deepcopy(f.tables)
    denied(f.tree, ErrorCode.REFERENTIAL_INTEGRITY_ERROR)
    assert f.tables == before and not f.writes


@pytest.mark.parametrize("target", ["task", "session", "node", "foreign_task", "foreign_session"])
def test_entitled_absence_and_scope_do_not_disclose_targets(target):
    f = ReadFixture()
    if target == "task":
        f.request = replace(f.request, task_id=new_uuid7())
    elif target == "session":
        f.request = replace(f.request, session_id=new_uuid7())
    elif target == "node":
        denied(lambda: f.lineage(new_uuid7()), ErrorCode.NOT_FOUND)
        return
    elif target == "foreign_task":
        f.task_row["project_id"] = new_uuid7()
    else:
        f.tables["experiment_search_sessions"][0]["research_task_id"] = new_uuid7()
    denied(f.tree, ErrorCode.NOT_FOUND)


@pytest.mark.parametrize(
    "verifier", [None, SimpleNamespace(), SimpleNamespace(is_valid=lambda p, at: 1)]
)
def test_missing_unsupported_verifier_denies_before_target_reads(verifier):
    f = ReadFixture()
    f.service = ExperimentSearchService(f.factory, verifier)
    denied(f.tree, ErrorCode.FORBIDDEN)
    assert "task_read" not in f.trace and "session_read" not in f.trace


@pytest.mark.parametrize("kind", ["HUMAN", "AGENT"])
def test_current_revocation_denies_before_any_target_lookup(kind):
    f = ReadFixture()
    f.actor_type, f.valid = kind, False
    denied(f.tree, ErrorCode.FORBIDDEN)
    f.request = replace(f.request, task_id=new_uuid7(), session_id=new_uuid7())
    denied(f.tree, ErrorCode.FORBIDDEN)
    assert "task_read" not in f.trace


@pytest.mark.parametrize("field", ["objective_definition", "expected_row_version", "node_id"])
def test_read_requests_are_closed(field):
    f = ReadFixture()
    raw = {k: str(v) for k, v in asdict(f.request).items()}
    assert parse_search_read("get_experiment_search_tree", raw) == f.request
    denied(
        lambda: f.service.get_experiment_search_tree(f.principal, cast(Any, raw)),
        ErrorCode.VALIDATION_ERROR,
    )
    with pytest.raises(ResearchBaseError) as exc:
        parse_search_read("get_experiment_search_tree", {**raw, field: "unexpected"})
    assert exc.value.code == ErrorCode.VALIDATION_ERROR
