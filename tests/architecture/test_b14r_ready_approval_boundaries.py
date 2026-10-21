"""READY permission extends the existing boundary without owning an effect."""

import importlib.util
import inspect
from pathlib import Path

from researchbase.application.approval import ApprovalService
from researchbase.persistence.approval_repository import B09_SNAPSHOT_TABLES

ROOT = Path(__file__).resolve().parents[2]


def migration():
    spec = importlib.util.spec_from_file_location(
        "b14r", ROOT / "migrations/versions/0063_b14r_ready_approval.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_inventory_no_schema_or_hash_expansion():
    module = migration()
    assert module.down_revision == "0062_b14a_publication_entry"
    assert module.B14R_SNAPSHOT_TABLES == B09_SNAPSHOT_TABLES
    assert (
        len(B09_SNAPSHOT_TABLES) == 46 and tuple(sorted(B09_SNAPSHOT_TABLES)) == B09_SNAPSHOT_TABLES
    )
    sql = module.UPGRADE_SQL.upper()
    for forbidden in (
        "CREATE TABLE",
        "ADD COLUMN",
        "CREATE INDEX",
        "ON DELETE CASCADE",
        "XMIN::TEXT::BIGINT",
        "B11_COMPLETE(",
    ):
        assert forbidden not in sql
    assert "PG_CURRENT_XACT_ID()::XID" in sql
    assert "B14A_VERIFY_ENTRY" in sql and "B04_VERIFY_STRUCTURE" in sql


def test_shared_boundary_prefix_and_distinct_records():
    source = inspect.getsource(ApprovalService._once)
    assert (
        source.index('repo.lock_snapshot(deciding=kind == "decision")')
        < source.index("repo.lock_request(")
        < source.index("repo.lock_scope(")
        < source.index("repo.lock_target(")
    )
    assert source.index("repo.force_constraints()") < source.index("exclude_rejection=")
    assert 'repo.insert("approval_decisions"' in source
    for forbidden in (
        "transition_entry",
        "consume_grant",
        "publication_lifecycle_events",
        "prepared_submission",
        "external_effect",
    ):
        assert forbidden not in source
    domain = (ROOT / "src/researchbase/domain/approval.py").read_text()
    for forbidden in ("sqlalchemy", "fastapi", "typer", "application.approval"):
        assert forbidden not in domain


def test_historical_helpers_have_no_explicit_exclusion_or_writes():
    for method in (
        ApprovalService._prepare_read,
        ApprovalService._ready_entry,
        ApprovalService._basis,
        ApprovalService._prepare_basis,
        ApprovalService._manuscript_gate,
        ApprovalService._request_view,
        ApprovalService._replay,
        ApprovalService._read,
    ):
        source = inspect.getsource(method)
        for forbidden in (
            "lock_snapshot(",
            "lock_project(",
            "lock_target(",
            "lock_request(",
            ".insert(",
            ".commit(",
            "admission=True",
        ):
            assert forbidden not in source
    assert "readonly=True" in inspect.getsource(ApprovalService._prepare_read)
    assert 'dependency = request.get("manuscript_version_id") is None' in inspect.getsource(
        ApprovalService._evaluate_in_uow
    )
