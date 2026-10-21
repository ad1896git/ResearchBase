from __future__ import annotations

from pathlib import Path

from tests.architecture.test_pr14_boundaries import _dependencies

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


PHASE1_CLAIM_ROOTS = frozenset(
    {
        "researchbase.domain.claim",
        "researchbase.persistence.repositories",
        "researchbase.application.commands",
        "researchbase.application.closure",
        "researchbase.application.provenance_queries",
    }
)


def _claim_boundary_violations(
    sources: dict[str, str], packages: frozenset[str] = frozenset()
) -> list[str]:
    """Keep Phase 1 Claim independent of authorized Phase 2 literature support."""
    assert PHASE1_CLAIM_ROOTS <= sources.keys(), "missing protected Phase 1 Claim module"
    violations = []
    # These structural escape hatches were never authorized in any phase.
    for module, source in sources.items():
        for forbidden in ("claimversionversion", "generic evidencerepository"):
            if forbidden in source.lower():
                violations.append(f"{module}: {forbidden}")
    for root in sorted(PHASE1_CLAIM_ROOTS):
        pending: list[tuple[str, tuple[str, ...]]] = [(root, (root,))]
        seen: set[str] = set()
        while pending:
            module, route = pending.pop()
            if module in seen:
                continue
            seen.add(module)
            if "literatureevidence" in sources[module].lower():
                violations.append(f"{' -> '.join(route)}: literatureevidence")
            dependencies = _dependencies(sources[module], module, module in packages)
            parents = {
                package
                for package in packages
                if module.startswith(package + ".")
                or any(dependency.startswith(package + ".") for dependency in dependencies)
            }
            for dependency in sorted(dependencies | parents):
                if dependency in sources:
                    pending.append((dependency, (*route, dependency)))
    return violations


def test_pr12_does_not_leak_pr13_or_later_implementation() -> None:
    # R2 gap closure §2 authorizes separate Phase 2 literature support while
    # explicitly preserving Phase 1 Claim tables, commands and support hashes.
    # Follow shared modules and package initializers; no blanket exclusions.
    sources = {}
    packages: set[str] = set()
    for path in sorted(SRC.rglob("*.py")):
        parts = path.relative_to(ROOT / "src").with_suffix("").parts
        module = ".".join(parts[:-1] if parts[-1] == "__init__" else parts)
        sources[module] = path.read_text()
        if parts[-1] == "__init__":
            packages.add(module)
    assert _claim_boundary_violations(sources, frozenset(packages)) == []
