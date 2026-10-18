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
        # PR2-05: owns LiteratureEvidence and its review/support relations.
        "migrations/versions/0030_literature_evidence.py": {"literature_evidence"},
        # PR2-05: M3 support-snapshot relation cardinality guard.
        "migrations/versions/0031_m3_snapshot_relation_cardinality.py": {"literature_evidence"},
        # PR2-10: exact LiteratureEvidence references in discussion turns.
        "migrations/versions/0032_pr2_10_discussion.py": {"literature_evidence"},
        # PR2-11: owns ScientificConclusion and exact LiteratureEvidence inputs.
        "migrations/versions/0033_pr2_11_r2_scientific_conclusion.py": {
            "literature_evidence",
            "scientific_conclusions",
        },
        # PR2-13: exact ScientificConclusion placement targets.
        "migrations/versions/0037_pr2_13_claim_placement.py": {"scientific_conclusions"},
        # PR2-14: exact frozen ScientificConclusion review targets.
        "migrations/versions/0040_pr2_14_initial_internal_review.py": {"scientific_conclusions"},
        # PR2-15: coordination locks on exact ScientificConclusion review targets.
        "migrations/versions/0041_pr2_15_review_coordination.py": {"scientific_conclusions"},
        # PR2-15: exact ScientificConclusion targets for the minimal decision command.
        "migrations/versions/0042_pr2_15_minimal_decision.py": {"scientific_conclusions"},
        # Task 13: approved RevisionAction exact conclusion result and scope guards.
        "migrations/versions/0044_pr2_15_revision_action.py": {"scientific_conclusions"},
        "migrations/versions/0045_pr2_16_basic_approval.py": {
            "scientific_conclusions",
            "literature_evidence",
        },
    }
    authorized_tables["migrations/versions/0047_pr2_18_novelty_prior_art.py"] = {
        "literature_evidence",
        "scientific_conclusions",
    }
    authorized_tables["migrations/versions/0048_b04_manuscript_freeze.py"] = {
        "scientific_conclusions"
    }
    authorized_tables["migrations/versions/0049_b05_manuscript_review.py"] = {
        "scientific_conclusions"
    }
    authorized_tables["migrations/versions/0051_b06_revision_action.py"] = {
        "literature_evidence",
        "scientific_conclusions",
    }
    authorized_tables["migrations/versions/0052_b07_revision_decisions.py"] = {
        "literature_evidence",
        "scientific_conclusions",
    }
    authorized_tables["migrations/versions/0053_b08_issue_disposition.py"] = {
        "literature_evidence",
        "scientific_conclusions",
    }
    authorized_tables["migrations/versions/0054_b11_ready_for_submission.py"] = {
        "literature_evidence",
        "scientific_conclusions",
        "manuscripts",  # registered decision_basis_manuscripts relation
    }
    authorized_tables["migrations/versions/0055_b09_approval_tuples.py"] = {
        "literature_evidence",
        "scientific_conclusions",
    }
    authorized_tables["migrations/versions/0056_b10_reconsideration.py"] = {
        "literature_evidence",
        "scientific_conclusions",
        "manuscripts",  # retain B11 typed Decision dispatch
    }
    # Owner-approved representation fix reuses existing evidence guards only.
    authorized_tables["migrations/versions/0057_xid_wraparound_guards.py"] = {
        "literature_evidence",
        "scientific_conclusions",
        "manuscripts",
    }
    authorized_tables["migrations/versions/0058_b12_prepare_submission.py"] = {
        "literature_evidence",
        "scientific_conclusions",
        "manuscripts",
    }
    authorized_tables["migrations/versions/0059_b13_grant_consumption.py"] = {
        "literature_evidence",
        "scientific_conclusions",
    }
    authorized_tables["migrations/versions/0060_b15_package_preparation.py"] = {
        "literature_evidence",
        "scientific_conclusions",
        "manuscripts",
    }
    authorized_tables["migrations/versions/0062_b14a_publication_entry.py"] = {
        "literature_evidence",
        "scientific_conclusions",
        "manuscripts",
    }
    authorized_tables["migrations/versions/0061_b16_consent_withdrawal.py"] = {
        "literature_evidence",
        "scientific_conclusions",
        "manuscripts",
    }
    authorized_tables["migrations/versions/0063_b14r_ready_approval.py"] = {
        "literature_evidence",
        "scientific_conclusions",
        "manuscripts",
    }
    authorized_tables["migrations/versions/0064_b14_publication_ready.py"] = {
        "literature_evidence",
        "scientific_conclusions",
    }
    for path in _python_files(ROOT / "migrations"):
        contents = path.read_text()
        permitted = authorized_tables.get(path.relative_to(ROOT).as_posix(), set())
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
