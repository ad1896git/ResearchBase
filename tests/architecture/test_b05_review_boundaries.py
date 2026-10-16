"""B05 transaction protocols and review-only extension boundaries."""

import ast
import inspect
from pathlib import Path
from typing import Any, cast

from alembic.config import Config
from alembic.script import ScriptDirectory

from researchbase.application.internal_review import InternalReviewService
from researchbase.persistence.internal_review_repository import (
    B05_SHARE_SQL,
    B05_SNAPSHOT_TABLES,
    SqlAlchemyInternalReviewRepository,
)
from researchbase.persistence.manuscript_freeze_repository import B04_SNAPSHOT_TABLES

ROOT = Path(__file__).resolve().parents[2]


def test_inventory_and_first_sql():
    assert B05_SNAPSHOT_TABLES == B04_SNAPSHOT_TABLES == tuple(sorted(B05_SNAPSHOT_TABLES))
    assert not {"review_issues", "internal_review_records", "review_issue_events"} & set(
        B05_SNAPSHOT_TABLES
    )

    class Session:
        def __init__(self):
            self.statements = []

        def connection(self, **kwargs):
            assert kwargs["execution_options"]["isolation_level"] == "READ COMMITTED"

        def execute(self, sql):
            self.statements.append(str(sql))

    session = Session()
    SqlAlchemyInternalReviewRepository(cast(Any, session)).prepare_write()
    assert session.statements[0] == B05_SHARE_SQL
    assert session.statements[1:] == [
        "SET LOCAL lock_timeout='10s'",
        "SET LOCAL statement_timeout='30s'",
    ]


def test_read_prepares_before_dispatch_authority_no_locking_helpers():
    source = inspect.getsource(InternalReviewService.read)
    assert (
        source.index("configure_revision_transaction(readonly=True)")
        < source.index("_authorize_snapshot")
        < source.index(".review(")
    )
    assert source.count("self._factory()") == 1
    assert not any(
        token in source
        for token in ("_auth._authorize", "lock_project", "lock_manuscript", "prepare_write")
    )
    source = inspect.getsource(InternalReviewService._authorize_snapshot)
    assert "_authorize(" not in source and "lock_" not in source
    assert "FOR " not in inspect.getsource(SqlAlchemyInternalReviewRepository.authority)
    assert "FOR " not in inspect.getsource(SqlAlchemyInternalReviewRepository.manuscript_target)


def test_pure_domain_and_no_new_schema():
    source = (ROOT / "src/researchbase/domain/internal_review.py").read_text()
    imports = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.ImportFrom)]
    assert all(
        not any(x in (node.module or "") for x in ("persistence", "sqlalchemy", "fastapi"))
        for node in imports
    )
    scripts = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    assert scripts.get_heads() == ["0053_b08_issue_disposition"]
    assert (
        scripts.get_revision("0049_b05_manuscript_review").down_revision
        == "0048_b04_manuscript_freeze"
    )
    ddl = (ROOT / "migrations/versions/0049_b05_manuscript_review.py").read_text()
    assert "CREATE TABLE" not in ddl and "ALTER TABLE manuscript_versions" not in ddl
    assert "b05_complete_review" in ddl and "b05_complete_issue_event" in ddl
    # Both ordinary INSERT guards lock manuscript before parent/review.
    upgrade = ddl[ddl.index("def upgrade") : ddl.index("def downgrade")]
    assert upgrade.index("WHERE id=NEW.manuscript_version_id FOR UPDATE") < upgrade.index(
        "FOR SHARE OF p"
    )
    assert upgrade.index("WHERE id=manuscript_id FOR UPDATE") < upgrade.index(
        "INTO review_project,checked_target,checked_manuscript"
    )


def test_basis_does_not_open_uow_or_implement_readiness():
    source = inspect.getsource(InternalReviewService.collect_manuscript_review_basis)
    assert "self._factory" not in source and ".commit(" not in source
    assert "require_write_prepared" in source and "manuscript_reviews" in source
    assert not any(
        x in source for x in ("READY_FOR_SUBMISSION", "insert_decision", "consume_grant")
    )
