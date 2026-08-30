from __future__ import annotations

from pathlib import Path

from researchbase.persistence.repositories import SqlAlchemyClaimRepository

ROOT = Path(__file__).parents[2]
SRC = ROOT / "src" / "researchbase"
MIGRATION = ROOT / "migrations" / "versions" / "0014_claim_evidence.py"


def test_claim_domain_is_framework_neutral() -> None:
    text = (SRC / "domain" / "claim.py").read_text().lower()
    assert "sqlalchemy" not in text
    assert "researchbase.persistence" not in text
    assert "fastapi" not in text
    assert "typer" not in text


def test_claim_repository_has_no_transaction_or_generic_persistence_surface() -> None:
    public = {name for name in dir(SqlAlchemyClaimRepository) if not name.startswith("_")}
    assert not public & {"commit", "save", "delete", "get_any", "save_any"}


def test_pr12_migration_keeps_hard_typed_evidence_and_restrict_deletes() -> None:
    text = MIGRATION.read_text()
    assert "source_type" not in text
    assert "source_id" not in text
    assert "object_type" not in text
    assert "object_id" not in text
    assert "ON DELETE CASCADE" not in text.upper()
    assert "UNIQUE(content_hash)" not in text
    assert "UNIQUE(support_set_hash)" not in text
    assert "measurement_id" in text and "statistical_result_id" in text


def test_pr12_does_not_leak_pr13_or_later_implementation() -> None:
    excluded = {"governance.py", "governance_queries.py"}
    source_text = "\n".join(
        path.read_text() for path in (SRC / "domain").rglob("*.py") if path.name not in excluded
    )
    source_text += "\n" + "\n".join(
        path.read_text()
        for path in (SRC / "application").rglob("*.py")
        if path.name not in excluded
    )
    for forbidden in (
        "literatureevidence",
        "claimversionversion",
        "generic evidencerepository",
    ):
        assert forbidden not in source_text.lower()
