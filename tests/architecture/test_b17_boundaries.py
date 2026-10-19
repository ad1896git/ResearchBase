"""B17 literal prefix and Application-only package/consumption ownership."""

import ast
from pathlib import Path

from researchbase.persistence.prepared_submission_repository import (
    B16_SNAPSHOT_TABLES,
    B17_SNAPSHOT_TABLES,
)

ROOT = Path(__file__).resolve().parents[2]


def test_literal_inventory_matches_authorized_b16_prefix():
    assert B17_SNAPSHOT_TABLES == B16_SNAPSHOT_TABLES == tuple(sorted(set(B17_SNAPSHOT_TABLES)))
    migration = ast.parse(
        (ROOT / "migrations/versions/0067_b17_prepared_package_freeze.py").read_text()
    )
    value = next(
        n.value
        for n in migration.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "B17_SNAPSHOT_TABLES" for t in n.targets)
    )
    assert ast.literal_eval(value) == B17_SNAPSHOT_TABLES
    assert not {
        "publications",
        "prepared_submission_versions",
        "author_consents",
        "approval_grants",
    } & set(B17_SNAPSHOT_TABLES)


def test_no_new_schema_transport_or_domain_dependency():
    migration = (ROOT / "migrations/versions/0067_b17_prepared_package_freeze.py").read_text()
    assert "CREATE TABLE" not in migration and "ON DELETE CASCADE" not in migration
    for file in (
        "domain/prepared_submission.py",
        "domain/approval.py",
        "application/prepared_submission.py",
    ):
        source = (ROOT / "src/researchbase" / file).read_text()
        for forbidden in ("sqlalchemy", "fastapi", "typer", "researchbase.persistence"):
            assert forbidden not in source
    for file in ("api/routes.py", "cli/commands/governance.py"):
        assert "freeze_prepared_submission" not in (ROOT / "src/researchbase" / file).read_text()


def test_freeze_prefix_and_chain_before_grant():
    source = (ROOT / "src/researchbase/persistence/prepared_submission_repository.py").read_text()
    tree = ast.parse(source)
    node = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "prepare_freeze_write"
    )
    code = ast.get_source_segment(source, node)
    assert code is not None
    assert (
        code.index("text(B17_SHARE_SQL)")
        < code.index("LOCK TABLE publications")
        < code.index("LOCK TABLE prepared_submission_versions")
        < code.index("approval_decisions,")
        < code.index("self._timeouts()")
    )
    assert '"isolation_level": "SERIALIZABLE"' in code
    app = (
        (ROOT / "src/researchbase/application/prepared_submission.py")
        .read_text()
        .split("    def freeze_prepared_submission", 1)[1]
    )
    assert (
        app.index("lock_chain(") < app.index("lock_consumption_request(") < app.index("lock_grant(")
    )
    assert "_consume_package_in_uow" in app and "novelty" not in app
