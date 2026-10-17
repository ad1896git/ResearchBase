"""B11 Application boundary and fixed transaction inventory."""

import ast
import inspect
from pathlib import Path
from typing import Any, cast

from researchbase.application.decision import DecisionService
from researchbase.persistence.decision_repository import (
    B11_SHARE_SQL,
    B11_SNAPSHOT_TABLES,
    SqlAlchemyDecisionRepository,
)
from researchbase.persistence.manuscript_freeze_repository import B04_SNAPSHOT_TABLES

ROOT = Path(__file__).resolve().parents[2]


def test_fixed_inventory_and_first_statement():
    expected = tuple(
        sorted(
            set(B04_SNAPSHOT_TABLES)
            | {
                "internal_review_records",
                "manuscript_versions",
                "publications",
                "review_issue_events",
                "review_issues",
            }
        )
    )
    assert B11_SNAPSHOT_TABLES == expected
    tree = ast.parse((ROOT / "migrations/versions/0054_b11_ready_for_submission.py").read_text())
    inventory = ast.literal_eval(
        next(
            n.value
            for n in tree.body
            if isinstance(n, ast.Assign)
            and isinstance(n.targets[0], ast.Name)
            and n.targets[0].id == "_TABLES"
        )
    )
    assert inventory == expected
    assert not any(t.startswith("decision_") for t in inventory)

    class Session:
        def __init__(self):
            self.sql = []

        def execute(self, statement):
            self.sql.append(str(statement))

    session = Session()
    repo = SqlAlchemyDecisionRepository(cast(Any, session))
    repo.prepare_readiness_write()
    assert session.sql == [
        B11_SHARE_SQL,
        "SET LOCAL lock_timeout='10s'",
        "SET LOCAL statement_timeout='30s'",
    ]
    session.sql.clear()
    repo.prepare_readiness_read()
    assert session.sql == ["SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"]


def test_application_order_and_only_authorized_writes():
    source = inspect.getsource(DecisionService._record_readiness_once)
    names = (
        "configure_revision_transaction",
        "prepare_readiness_write",
        "lock_readiness_request",
        "lock_readiness_target",
        "lock_readiness_project",
        "lock_publication",
        "_readiness_authorize",
        "insert_decision",
        "insert_manuscript_basis",
        "insert_review_basis",
        "force_readiness_constraints",
        "uow.commit",
    )
    assert [source.index(n) for n in names] == sorted(source.index(n) for n in names)
    assert "lock_project(" not in source
    assert "current_manuscript_version_id" not in source
    assert not any(
        t in source
        for t in (
            "approval.",
            "insert_issue",
            "transition_publication",
            "ExternalEffect",
            "supersedes_decision_id=command",
        )
    )


def test_lock_free_exact_read_and_domain():
    source = inspect.getsource(DecisionService.get_ready_for_submission_decision)
    assert (
        source.index("prepare_readiness_read")
        < source.index("_readiness_authorize")
        < source.index(".decision(")
    )
    assert "lock_" not in source and ".commit(" not in source
    source = inspect.getsource(DecisionService._readiness_authorize)
    assert "lock_" not in source
    tree = ast.parse((ROOT / "src/researchbase/domain/decision.py").read_text())
    imports = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert not any(
        any(p in n for p in ("sqlalchemy", "persistence", "fastapi", "typer")) for n in imports
    )
    ddl = (ROOT / "migrations/versions/0054_b11_ready_for_submission.py").read_text()
    assert ddl.count("CREATE TABLE ") == 1
    assert "target_type" not in ddl and "CREATE TABLE decision_basis_manuscripts" in ddl
