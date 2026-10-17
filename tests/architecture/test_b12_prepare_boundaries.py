"""B12 fixed SQL inventories, transaction boundaries and bounded effects."""

import ast
import inspect
from pathlib import Path
from typing import Any, cast

from researchbase.application.approval import ApprovalService
from researchbase.application.decision import DecisionService
from researchbase.persistence.approval_repository import (
    B09_SNAPSHOT_TABLES,
    SqlAlchemyApprovalRepository,
)
from researchbase.persistence.decision_repository import (
    B11_SNAPSHOT_TABLES,
    SqlAlchemyDecisionRepository,
)
from researchbase.persistence.manuscript_freeze_repository import B04_SNAPSHOT_TABLES

ROOT = Path(__file__).resolve().parents[2]


def test_exact_fixed_inventories_and_share_first():
    common = set(B04_SNAPSHOT_TABLES) | {"manuscript_versions", "publications"}
    assert B11_SNAPSHOT_TABLES == tuple(
        sorted(common | {"internal_review_records", "review_issues", "review_issue_events"})
    )
    assert B09_SNAPSHOT_TABLES == B11_SNAPSHOT_TABLES
    tree = ast.parse((ROOT / "migrations/versions/0058_b12_prepare_submission.py").read_text())
    values = {
        n.targets[0].id: ast.literal_eval(n.value)
        for n in tree.body
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
    }
    assert values["B12_SNAPSHOT_TABLES"] == B11_SNAPSHOT_TABLES

    class Session:
        def __init__(self):
            self.sql = []

        def execute(self, statement):
            self.sql.append(str(statement))

    for repo, method, inventory in (
        (SqlAlchemyDecisionRepository, "prepare_readiness_write", B11_SNAPSHOT_TABLES),
        (SqlAlchemyApprovalRepository, "lock_snapshot", B09_SNAPSHOT_TABLES),
    ):
        session = Session()
        getattr(repo(cast(Any, session)), method)()
        assert session.sql == [
            "LOCK TABLE " + ",".join(inventory) + " IN SHARE MODE",
            "SET LOCAL lock_timeout='10s'",
            "SET LOCAL statement_timeout='30s'",
        ]


def test_no_new_schema_or_effects_and_preserved_xid_guard():
    source = (ROOT / "migrations/versions/0058_b12_prepare_submission.py").read_text()
    assert "CREATE TABLE" not in source and "ADD COLUMN" not in source
    assert "xmin=pg_current_xact_id()::xid" in source
    assert "b12:decision:" in source
    for method in (DecisionService._record_prepare_submission_once,):
        code = inspect.getsource(method)
        assert code.index("prepare_readiness_write") < code.index("lock_prepare_submission_request")
        assert (
            code.index("force_readiness_constraints")
            < code.rindex("_readiness_authorize")
            < code.index("uow.commit")
        )
        assert not any(
            x in code
            for x in ("insert_grant", "insert_publication", "consent", "receipt", "external_effect")
        )


def test_read_and_replay_use_snapshot_without_explicit_exclusion():
    for method in (
        DecisionService.get_prepare_submission_decision,
        DecisionService._prepare_submission_replay,
        DecisionService._recover_prepare_submission_collision,
    ):
        source = inspect.getsource(method)
        assert "readonly=True" in source
        assert "enable_revision_action_snapshot_reads" in source
        assert "prepare_readiness_write" not in source
        assert "lock_prepare_submission_request" not in source
        assert "uow.commit" not in source


def test_approval_purposes_share_one_writer_inventory_without_routing_uow():
    # Full B is independent of request purpose, so routing needs no extra read UoW.
    execute = inspect.getsource(ApprovalService._execute)
    assert "self._factory" not in execute
    write = inspect.getsource(ApprovalService._once)
    assert write.index("repo.lock_snapshot()") < write.index("repo.lock_request(command.id)")
    assert "lock_prepare_snapshot" not in write and "purpose_hint" not in write
