from importlib import import_module
from typing import cast

from researchbase.domain.governance import GovernanceTargetType

MIGRATION_MODULE = "migrations.versions.0017_persisted_canonical_enum_normalization"


def test_0017_is_append_only_after_0016() -> None:
    migration = import_module(MIGRATION_MODULE)
    assert migration.revision == "0017_persisted_canonical_enum_normalization"
    assert migration.down_revision == "0016_pr17d_history_protection"


def test_0017_contains_only_explicit_mappings_and_excludes_roles() -> None:
    migration = import_module(MIGRATION_MODULE)
    assert migration.LEGACY_TO_CANONICAL["active"] == "ACTIVE"
    assert migration.LEGACY_TO_CANONICAL["experiment_spec_version"] == ("EXPERIMENT_SPEC_VERSION")
    assert set(migration.NORMALIZED_COLUMNS) == {
        ("actors", "actor_type"),
        ("projects", "lifecycle_status"),
        ("workspaces", "lifecycle_status"),
        ("datasets", "lifecycle_status"),
        ("evidence_relations", "relation_type"),
        ("audit_findings", "severity"),
        ("audit_findings", "target_type"),
        ("audit_findings", "status"),
        ("impact_assessments", "conclusion"),
        ("impact_targets", "target_type"),
        ("impact_targets", "impact_kind"),
        ("correction_records", "target_type"),
        ("correction_records", "correction_type"),
    }
    assert migration.TARGET_TYPE_CANONICAL == tuple(GovernanceTargetType.__members__)
    assert "run_dataset_inputs" not in {table for table, _ in migration.NORMALIZED_COLUMNS}
    assert "run_artifact_inputs" not in {table for table, _ in migration.NORMALIZED_COLUMNS}


def test_0017_has_no_generic_case_conversion() -> None:
    migration = import_module(MIGRATION_MODULE)
    migration_file = cast(str, migration.__file__)
    assert "UPPER(" not in open(migration_file, encoding="utf-8").read()


def test_0017_restores_lowercase_audit_transition_on_downgrade() -> None:
    migration = import_module(MIGRATION_MODULE)
    assert "OLD.status='open'" in migration.LEGACY_AUDIT_TRANSITION_FUNCTION
    assert "OLD.status='OPEN'" in migration.CANONICAL_AUDIT_TRANSITION_FUNCTION
