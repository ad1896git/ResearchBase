from __future__ import annotations

from pathlib import Path

from researchbase.application.governance import TargetResolverRegistry
from researchbase.domain.governance import GovernanceTargetType

ROOT = Path(__file__).resolve().parents[2]


def test_pr14_has_closed_registry_and_no_generic_graph_or_later_governance() -> None:
    assert TargetResolverRegistry().supported_types == frozenset(GovernanceTargetType)
    source = "\n".join(
        path.read_text() for path in (ROOT / "src/researchbase").rglob("*.py")
    ).lower()
    for forbidden in (
        "load_any(",
        "find_any_target",
        "decisionrecord",
        "approvalrequest",
        "approvaldecision",
        "approvalgrant",
        "networkx",
        "graph cache",
    ):
        assert forbidden not in source


def test_pr14_migration_has_exactly_four_business_tables() -> None:
    migration = (ROOT / "migrations/versions/0015_governance_audit.py").read_text()
    assert migration.count("op.create_table(") == 4
    for table in (
        "audit_findings",
        "impact_assessments",
        "impact_targets",
        "correction_records",
    ):
        assert f'"{table}"' in migration
    assert 'ondelete="CASCADE"' not in migration
