from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]
SRC = ROOT / "src" / "researchbase"


def _python_files(path: Path) -> list[Path]:
    return sorted(path.rglob("*.py"))


def test_pr02_domain_slice_is_present() -> None:
    assert (SRC / "domain").is_dir()
    assert (SRC / "domain" / "identity.py").is_file()
    assert (SRC / "domain" / "organization.py").is_file()


def test_persistence_does_not_import_framework_adapters() -> None:
    forbidden = ("fastapi", "typer")
    for path in _python_files(SRC / "persistence"):
        contents = path.read_text()
        assert not any(
            f"import {name}" in contents or f"from {name}" in contents for name in forbidden
        )


def test_no_forbidden_runtime_dependencies_or_parallel_manifests() -> None:
    project = (ROOT / "pyproject.toml").read_text().lower()
    for forbidden in ("redis", "celery", "rq", "langgraph", "storm", "evoscientist", "vector"):
        assert forbidden not in project
    assert not (ROOT / "requirements.txt").exists()
    assert not (ROOT / "Pipfile").exists()
    assert not (ROOT / "poetry.lock").exists()


def test_phase1_has_no_unauthorized_later_business_schema_migration() -> None:
    # Exact accepted Phase 2 ownership/references; future migrations get no exemption.
    authorized_tables = {
        "0030_literature_evidence.py": {"literature_evidence"},
        "0031_m3_snapshot_relation_cardinality.py": {"literature_evidence"},
        "0032_pr2_10_discussion.py": {"literature_evidence"},
        "0033_pr2_11_r2_scientific_conclusion.py": {
            "literature_evidence",
            "scientific_conclusions",
        },
        "0037_pr2_13_claim_placement.py": {"scientific_conclusions"},
        "0040_pr2_14_initial_internal_review.py": {"scientific_conclusions"},
        "0041_pr2_15_review_coordination.py": {"scientific_conclusions"},
        "0042_pr2_15_minimal_decision.py": {"scientific_conclusions"},
    }
    for path in _python_files(ROOT / "migrations"):
        contents = path.read_text()
        permitted = authorized_tables.get(path.name, set())
        for table in ("literature_evidence", "scientific_conclusions", "manuscripts"):
            assert table in permitted or table not in contents, (path.name, table)
        assert "run_versions" not in contents, path.name


def test_pr12_adds_only_claim_evidence_schema_slice() -> None:
    migration = (ROOT / "migrations" / "versions" / "0014_claim_evidence.py").read_text()
    assert '"claims"' in migration
    assert '"claim_versions"' in migration
    assert '"evidence_relations"' in migration
    assert "StatisticalResultVersion" not in migration
    assert "generic source_type/source_id" not in migration
    assert "claim_version_versions" not in migration


def test_pr10_adds_only_the_measurement_schema_slice() -> None:
    migration = (ROOT / "migrations" / "versions" / "0010_measurement.py").read_text()
    assert '"measurements"' in migration
    assert "MeasurementVersion" not in migration
    assert "statistical_results" not in migration
    assert "claims" not in migration


def test_pr11_adds_only_statistical_result_schema_slice() -> None:
    migration = (ROOT / "migrations" / "versions" / "0011_statistical_result.py").read_text()
    assert '"statistical_results"' in migration
    assert '"statistical_result_inputs"' in migration
    assert "StatisticalResultVersion" not in migration
    assert "claims" not in migration
    assert "evidence_relations" not in migration


def test_pr11r_adds_only_the_narrow_statistical_result_guard() -> None:
    migration = (
        ROOT / "migrations" / "versions" / "0012_statistical_result_input_guard.py"
    ).read_text()
    assert "0011_statistical_result" in migration
    assert "CREATE CONSTRAINT TRIGGER statistical_result_requires_input" in migration
    assert "CREATE TABLE" not in migration
    assert "statistical_result_version" not in migration.lower()


def test_pr06_does_not_add_dataset_version_or_pr07_business_schema() -> None:
    source_text = "\n".join(path.read_text() for path in _python_files(SRC))
    migration_text = "\n".join(path.read_text() for path in _python_files(ROOT / "migrations"))
    assert "DatasetVersion" not in source_text
    assert "dataset_versions" not in migration_text
    assert "artifact_versions" in migration_text


def test_pr07_does_not_add_run_roles_or_generic_version_schema() -> None:
    source_text = "\n".join(path.read_text() for path in _python_files(SRC))
    assert "GenericVersion" not in source_text


def test_dataset_snapshot_repository_has_no_mutating_surface() -> None:
    from researchbase.persistence.repositories import SqlAlchemyDatasetSnapshotRepository

    public_methods = {
        name for name in dir(SqlAlchemyDatasetSnapshotRepository) if not name.startswith("_")
    }

    assert {"add", "get", "find_by_dataset_and_content_hash"} <= public_methods
    assert not public_methods & {"update", "save", "delete", "relocate"}


def test_measurement_domain_and_repository_preserve_immutable_boundary() -> None:
    domain_text = (SRC / "domain" / "measurement.py").read_text()
    assert "sqlalchemy" not in domain_text.lower()
    assert "fastapi" not in domain_text.lower()
    assert "typer" not in domain_text.lower()

    from researchbase.persistence.repositories import SqlAlchemyMeasurementRepository

    public_methods = {
        name for name in dir(SqlAlchemyMeasurementRepository) if not name.startswith("_")
    }
    assert {"add", "get", "list_by_run"} <= public_methods
    assert not public_methods & {"update", "save", "delete"}
