"""Approved relation admission, literal hashes and bounded Application scope."""

import ast
import inspect
from pathlib import Path

from researchbase.application.decision import DecisionService
from researchbase.application.revision_action import RevisionActionService
from researchbase.persistence.revision_action_repository import REVISION_SNAPSHOT_TABLES

ROOT = Path(__file__).resolve().parents[2]


def test_owner_adr_admits_both_concrete_relations_and_additive_field_contract():
    adr = (
        ROOT / "docs/architecture/adr/ADR-0015-b07-revision-decisions-concern-carry-forward.md"
    ).read_text()
    draft = (ROOT / "docs/proposals/B07_Revision_Decisions_Contract_DRAFT.md").read_text()
    assert "APPROVED by owner 2026-10-16" in adr
    assert "Status: APPROVED by owner 2026-10-16" in draft
    assert "ADR-0015" in draft and "11.4 Architecture Questions — APPROVED" in draft
    for relation in ("decision_revision_concerns", "revision_action_re_reviews"):
        assert relation in adr
    assert "Registry 03" in adr and "Field Contract 13" in adr
    assert "not cryptographically bound" in adr


def test_forward_admission_only_concrete_relations_and_no_scientific_effects():
    source = (ROOT / "migrations/versions/0052_b07_revision_decisions.py").read_text()
    for table in (
        "decision_basis_claims",
        "decision_revision_concerns",
        "revision_action_re_reviews",
    ):
        assert f"CREATE TABLE {table}" in source
    for forbidden in (
        "ON DELETE CASCADE",
        "target_type VARCHAR",
        "CREATE TABLE b07_",
        "INSERT INTO review_issue_events",
        "UPDATE review_issues",
        "DELETE FROM",
        "ADD COLUMN",
    ):
        assert forbidden not in source
    assert 'down_revision = "0051_b06_revision_action"' in source
    assert "DEFERRABLE INITIALLY DEFERRED" in source
    assert "new revision history" not in source  # B07 has its own guarded downgrade.


def test_pure_policy_and_exact_snapshot_read_entrypoints():
    for name in ("decision", "revision_action"):
        tree = ast.parse((ROOT / f"src/researchbase/domain/{name}.py").read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not any(
                    x in (node.module or "")
                    for x in ("persistence", "sqlalchemy", "application", "fastapi")
                )
    for method in (
        DecisionService.get_revision_decision,
        RevisionActionService.read_revision_action,
        RevisionActionService.get_concern_carry_forward,
    ):
        source = inspect.getsource(method)
        assert source.index("configure_revision_transaction(readonly=True)") < source.index(
            "_authorize"
        )
        assert "lock_" not in source and source.count("self._factory()") == 1
    assert len(REVISION_SNAPSHOT_TABLES) == 26
    assert REVISION_SNAPSHOT_TABLES == tuple(sorted(REVISION_SNAPSHOT_TABLES))
    assert "internal_review_records" in REVISION_SNAPSHOT_TABLES
    assert "claim_versions" not in REVISION_SNAPSHOT_TABLES
