"""Enforce same-parent ownership for all Phase 1 current-version pointers."""

from __future__ import annotations

from alembic import op
from sqlalchemy import Connection, text

revision: str = "0018_current_pointer_same_parent_integrity"
down_revision: str | None = "0017_persisted_canonical_enum_normalization"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


POINTER_PAIRS = (
    (
        "research_questions",
        "research_question_versions",
        "research_question_id",
        "fk_research_questions_current_version_same_parent",
        "uq_research_question_versions_parent_id_id",
    ),
    (
        "hypotheses",
        "hypothesis_versions",
        "hypothesis_id",
        "fk_hypotheses_current_version_same_parent",
        "uq_hypothesis_versions_parent_id_id",
    ),
    (
        "experiment_specs",
        "experiment_spec_versions",
        "experiment_spec_id",
        "fk_experiment_specs_current_version_same_parent",
        "uq_experiment_spec_versions_parent_id_id",
    ),
    (
        "artifacts",
        "artifact_versions",
        "artifact_id",
        "fk_artifacts_current_version_same_parent",
        "uq_artifact_versions_parent_id_id",
    ),
    (
        "metric_definitions",
        "metric_definition_versions",
        "metric_definition_id",
        "fk_metric_definitions_current_version_same_parent",
        "uq_metric_definition_versions_parent_id_id",
    ),
    (
        "claims",
        "claim_versions",
        "claim_id",
        "fk_claims_current_version_same_parent",
        "uq_claim_versions_parent_id_id",
    ),
)


def _corrupt_pointers(bind: Connection) -> list[tuple[str, str, str, str, str]]:
    corrupt: list[tuple[str, str, str, str, str]] = []
    for identity_table, version_table, parent_column, _fk_name, _unique_name in POINTER_PAIRS:
        rows = bind.execute(
            text(
                f"SELECT identity.id AS identity_id, identity.current_version_id, "
                f"version.id AS version_id, version.{parent_column} AS actual_parent "
                f"FROM {identity_table} AS identity "
                f"LEFT JOIN {version_table} AS version "
                "ON version.id = identity.current_version_id "
                "WHERE identity.current_version_id IS NOT NULL "
                f"AND (version.id IS NULL OR version.{parent_column} IS DISTINCT FROM identity.id) "
                "ORDER BY identity.id"
            )
        ).all()
        for row in rows:
            failure_type = "MISSING_TARGET" if row.version_id is None else "CROSS_PARENT"
            corrupt.append(
                (
                    identity_table,
                    str(row.identity_id),
                    str(row.current_version_id),
                    str(row.actual_parent) if row.actual_parent is not None else "<missing>",
                    failure_type,
                )
            )
    return corrupt


def _preflight(bind: Connection) -> None:
    corrupt = _corrupt_pointers(bind)
    if corrupt:
        details = "; ".join(
            f"table={table}, identity={identity_id}, current_version_id={version_id}, "
            f"actual_parent={actual_parent}, failure_type={failure_type}"
            for table, identity_id, version_id, actual_parent, failure_type in corrupt
        )
        raise RuntimeError(
            f"P1-FCR3 current-pointer preflight failed; no DDL was applied; corrupt_rows={details}"
        )


def _constraint_columns(
    bind: Connection, name: str
) -> tuple[str, list[str], str | None, list[str]]:
    row = bind.execute(
        text(
            "SELECT c.contype, c.convalidated, c.confrelid::regclass::text AS target_table, "
            "ARRAY(SELECT a.attname FROM unnest(c.conkey) WITH ORDINALITY AS key(attnum, ord) "
            "JOIN pg_attribute AS a ON a.attrelid = c.conrelid AND a.attnum = key.attnum "
            "ORDER BY key.ord) AS local_columns, "
            "ARRAY(SELECT a.attname FROM unnest(c.confkey) WITH ORDINALITY AS key(attnum, ord) "
            "JOIN pg_attribute AS a ON a.attrelid = c.confrelid AND a.attnum = key.attnum "
            "ORDER BY key.ord) AS target_columns "
            "FROM pg_constraint AS c "
            "JOIN pg_namespace AS n ON n.oid = c.connamespace "
            "WHERE n.nspname = 'public' AND c.conname = :name"
        ),
        {"name": name},
    ).one_or_none()
    if row is None:
        raise RuntimeError(f"P1-FCR3 missing constraint: {name}")
    if not row.convalidated:
        raise RuntimeError(f"P1-FCR3 constraint is not validated: {name}")
    local_columns = list(row.local_columns)
    if row.contype != "f":
        return row.contype, local_columns, None, []
    return row.contype, local_columns, row.target_table, list(row.target_columns)


def _verify_catalog(bind: Connection) -> None:
    for _identity_table, version_table, parent_column, fk_name, unique_name in POINTER_PAIRS:
        unique_type, unique_columns, unique_target, unique_target_columns = _constraint_columns(
            bind, unique_name
        )
        if unique_type != "u" or unique_columns != [parent_column, "id"]:
            raise RuntimeError(
                f"P1-FCR3 invalid unique constraint {unique_name}: "
                f"type={unique_type}, columns={unique_columns}"
            )
        if unique_target is not None or unique_target_columns:
            raise RuntimeError(
                f"P1-FCR3 unique constraint unexpectedly references a table: {unique_name}"
            )

        fk_type, fk_columns, fk_target, fk_target_columns = _constraint_columns(bind, fk_name)
        target_table = version_table
        if (
            fk_type != "f"
            or fk_columns != ["id", "current_version_id"]
            or fk_target is None
            or fk_target.split(".")[-1] != target_table
            or fk_target_columns != [parent_column, "id"]
        ):
            raise RuntimeError(
                f"P1-FCR3 invalid composite FK {fk_name}: "
                f"source={fk_columns}, target={fk_target}({fk_target_columns})"
            )


def upgrade() -> None:
    bind = op.get_bind()
    _preflight(bind)
    for _identity_table, version_table, parent_column, _fk_name, unique_name in POINTER_PAIRS:
        op.create_unique_constraint(unique_name, version_table, [parent_column, "id"])
    for identity_table, version_table, parent_column, fk_name, _unique_name in POINTER_PAIRS:
        op.create_foreign_key(
            fk_name,
            identity_table,
            version_table,
            ["id", "current_version_id"],
            [parent_column, "id"],
            ondelete="RESTRICT",
        )
    _verify_catalog(bind)


def downgrade() -> None:
    for identity_table, _version_table, _parent_column, fk_name, _unique_name in reversed(
        POINTER_PAIRS
    ):
        op.drop_constraint(fk_name, identity_table, type_="foreignkey")
    for _identity_table, version_table, _parent_column, _fk_name, unique_name in reversed(
        POINTER_PAIRS
    ):
        op.drop_constraint(unique_name, version_table, type_="unique")
