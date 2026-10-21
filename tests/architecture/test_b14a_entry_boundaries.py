"""Entry uses existing Application, event and concrete provenance boundaries."""

import ast
import importlib.util
from pathlib import Path

from researchbase.application.publication import PublicationService
from researchbase.persistence.approval_repository import B13_SNAPSHOT_TABLES
from researchbase.persistence.publication_repository import B14A_SNAPSHOT_TABLES

ROOT = Path(__file__).resolve().parents[2]


def test_entry_reuses_existing_boundary_and_literal_inventory():
    assert callable(PublicationService.transition_publication_internal_review)
    assert callable(PublicationService.get_publication_internal_review_entry)
    assert B14A_SNAPSHOT_TABLES == B13_SNAPSHOT_TABLES
    assert "publications" not in B14A_SNAPSHOT_TABLES
    path = ROOT / "migrations/versions/0062_b14a_publication_entry.py"
    spec = importlib.util.spec_from_file_location("b14a", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.down_revision == "0061_b16_consent_withdrawal"
    sql = module.UPGRADE_SQL
    assert "CREATE TABLE" not in sql.upper()
    assert "REFERENCES manuscript_versions(publication_id,id) ON DELETE RESTRICT" in sql
    assert "pg_current_xact_id()::xid" in sql and "xmin::text::bigint" not in sql
    assert "ON DELETE CASCADE" not in sql
    assert "pr212_publication_guard" in sql and "b14a_complete_entry_event" in sql


def test_historical_paths_have_no_exclusion_or_write_calls():
    tree = ast.parse((ROOT / "src/researchbase/application/publication.py").read_text())
    owner = next(
        n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "PublicationService"
    )
    methods = {n.name: n for n in owner.body if isinstance(n, ast.FunctionDef)}
    for name in ("_entry_readback", "_read_entry", "get_publication_internal_review_entry"):
        body = ast.unparse(methods[name])
        for forbidden in (
            "lock_request(",
            "lock_project(",
            "lock_entry_target(",
            "transition_entry(",
            ".commit(",
            ".create(",
            "self._authorize(",
        ):
            assert forbidden not in body
    assert "readonly=True" in ast.unparse(methods["_read_entry"])
    assert "verify_saved_seal_in_uow" in ast.unparse(methods["_entry_readback"])
    for name in ("_entry_readback", "_enter_review_once"):
        body = ast.unparse(methods[name])
        assert "Session" not in body and "sqlalchemy" not in body
        for forbidden in (
            "record_decision",
            "create_request",
            "consume_grant",
            "external_effect",
            "prepare_submission",
        ):
            assert forbidden not in body
