"""Normalize Phase 1 persisted canonical enum lexemes."""

# SQL function bodies and exact legacy CHECK expressions intentionally remain
# close to their database representation.
# ruff: noqa: E501

from __future__ import annotations

import logging

from alembic import op
from sqlalchemy import text

revision: str = "0017_persisted_canonical_enum_normalization"
down_revision: str | None = "0016_pr17d_history_protection"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

logger = logging.getLogger(__name__)

TARGET_TYPE_CANONICAL = (
    "EXPERIMENT_SPEC_VERSION",
    "DATASET_SNAPSHOT",
    "ARTIFACT_VERSION",
    "RUN",
    "METRIC_DEFINITION_VERSION",
    "MEASUREMENT",
    "STATISTICAL_RESULT",
    "CLAIM_VERSION",
)
_TARGET_TYPE_LEGACY = {
    "experiment_spec_version": "EXPERIMENT_SPEC_VERSION",
    "dataset_snapshot": "DATASET_SNAPSHOT",
    "artifact_version": "ARTIFACT_VERSION",
    "run": "RUN",
    "metric_definition_version": "METRIC_DEFINITION_VERSION",
    "measurement": "MEASUREMENT",
    "statistical_result": "STATISTICAL_RESULT",
    "claim_version": "CLAIM_VERSION",
}

LEGACY_TO_CANONICAL = {
    "human": "HUMAN",
    "agent": "AGENT",
    "service": "SERVICE",
    "active": "ACTIVE",
    "archived": "ARCHIVED",
    "retired": "RETIRED",
    "supports": "SUPPORTS",
    "contradicts": "CONTRADICTS",
    "qualifies": "QUALIFIES",
    "context": "CONTEXT",
    "info": "INFO",
    "minor": "MINOR",
    "major": "MAJOR",
    "critical": "CRITICAL",
    **_TARGET_TYPE_LEGACY,
    "open": "OPEN",
    "confirmed": "CONFIRMED",
    "dismissed": "DISMISSED",
    "resolved": "RESOLVED",
    "no_impact": "NO_IMPACT",
    "stale": "STALE",
    "invalid": "INVALID",
    "requires_review": "REQUIRES_REVIEW",
    "unknown": "UNKNOWN",
    "direct": "DIRECT",
    "downstream": "DOWNSTREAM",
    "factual": "FACTUAL",
    "metadata": "METADATA",
    "computational": "COMPUTATIONAL",
    "attribution": "ATTRIBUTION",
    "other": "OTHER",
}

_COLUMN_MAPPINGS = {
    ("actors", "actor_type"): {"human": "HUMAN", "agent": "AGENT", "service": "SERVICE"},
    ("projects", "lifecycle_status"): {
        "active": "ACTIVE",
        "archived": "ARCHIVED",
        "retired": "RETIRED",
    },
    ("workspaces", "lifecycle_status"): {
        "active": "ACTIVE",
        "archived": "ARCHIVED",
        "retired": "RETIRED",
    },
    ("datasets", "lifecycle_status"): {
        "active": "ACTIVE",
        "archived": "ARCHIVED",
        "retired": "RETIRED",
    },
    ("evidence_relations", "relation_type"): {
        "supports": "SUPPORTS",
        "contradicts": "CONTRADICTS",
        "qualifies": "QUALIFIES",
        "context": "CONTEXT",
    },
    ("audit_findings", "severity"): {
        "info": "INFO",
        "minor": "MINOR",
        "major": "MAJOR",
        "critical": "CRITICAL",
    },
    ("audit_findings", "target_type"): _TARGET_TYPE_LEGACY,
    ("audit_findings", "status"): {
        "open": "OPEN",
        "confirmed": "CONFIRMED",
        "dismissed": "DISMISSED",
        "resolved": "RESOLVED",
    },
    ("impact_assessments", "conclusion"): {
        "no_impact": "NO_IMPACT",
        "stale": "STALE",
        "invalid": "INVALID",
        "requires_review": "REQUIRES_REVIEW",
        "unknown": "UNKNOWN",
    },
    ("impact_targets", "target_type"): _TARGET_TYPE_LEGACY,
    ("impact_targets", "impact_kind"): {
        "direct": "DIRECT",
        "downstream": "DOWNSTREAM",
        "stale": "STALE",
        "invalid": "INVALID",
        "requires_review": "REQUIRES_REVIEW",
    },
    ("correction_records", "target_type"): _TARGET_TYPE_LEGACY,
    ("correction_records", "correction_type"): {
        "factual": "FACTUAL",
        "metadata": "METADATA",
        "computational": "COMPUTATIONAL",
        "attribution": "ATTRIBUTION",
        "other": "OTHER",
    },
}
NORMALIZED_COLUMNS = tuple(_COLUMN_MAPPINGS)

_CHECKS = (
    ("actors", "ck_actors_actor_type", "actor_type IN ('HUMAN', 'AGENT', 'SERVICE')"),
    (
        "projects",
        "ck_projects_lifecycle_status",
        "lifecycle_status IN ('ACTIVE', 'ARCHIVED', 'RETIRED')",
    ),
    (
        "workspaces",
        "ck_workspaces_lifecycle_status",
        "lifecycle_status IN ('ACTIVE', 'ARCHIVED', 'RETIRED')",
    ),
    (
        "datasets",
        "ck_datasets_lifecycle_status",
        "lifecycle_status IN ('ACTIVE', 'ARCHIVED', 'RETIRED')",
    ),
    (
        "evidence_relations",
        "ck_evidence_relations_relation_type",
        "relation_type IN ('SUPPORTS', 'CONTRADICTS', 'QUALIFIES', 'CONTEXT')",
    ),
    (
        "audit_findings",
        "ck_audit_findings_severity",
        "severity IN ('INFO', 'MINOR', 'MAJOR', 'CRITICAL')",
    ),
    (
        "audit_findings",
        "ck_audit_findings_status",
        "status IN ('OPEN', 'CONFIRMED', 'DISMISSED', 'RESOLVED')",
    ),
    (
        "impact_assessments",
        "ck_impact_assessments_conclusion",
        "conclusion IN ('NO_IMPACT', 'STALE', 'INVALID', 'REQUIRES_REVIEW', 'UNKNOWN')",
    ),
    (
        "impact_targets",
        "ck_impact_targets_kind",
        "impact_kind IN ('DIRECT', 'DOWNSTREAM', 'STALE', 'INVALID', 'REQUIRES_REVIEW')",
    ),
    (
        "correction_records",
        "ck_correction_records_type",
        "correction_type IN ('FACTUAL', 'METADATA', 'COMPUTATIONAL', 'ATTRIBUTION', 'OTHER')",
    ),
)
_TARGET_TYPE_CHECKS = (
    ("audit_findings", "ck_audit_findings_target_type"),
    ("impact_targets", "ck_impact_targets_target_type"),
    ("correction_records", "ck_correction_records_target_type"),
)
_TRIGGER_TABLES = (
    "evidence_relations",
    "audit_findings",
    "impact_assessments",
    "impact_targets",
    "correction_records",
)

CANONICAL_AUDIT_TRANSITION_FUNCTION = """BEGIN
    IF to_jsonb(NEW) - 'status' - 'row_version' IS DISTINCT FROM to_jsonb(OLD) - 'status' - 'row_version' THEN
        RAISE EXCEPTION 'PR-17D AuditFinding material is immutable' USING ERRCODE='P17D1', CONSTRAINT='pr17d_audit_finding_immutable';
    END IF;
    IF NEW.row_version <> OLD.row_version + 1 OR NOT (
       (OLD.status='OPEN' AND NEW.status IN ('CONFIRMED','DISMISSED')) OR
       (OLD.status='CONFIRMED' AND NEW.status IN ('RESOLVED','DISMISSED'))
    ) THEN
        RAISE EXCEPTION 'PR-17D illegal AuditFinding transition' USING ERRCODE='P17D2', CONSTRAINT='pr17d_audit_finding_transition';
    END IF;
    RETURN NEW;
END;"""
LEGACY_AUDIT_TRANSITION_FUNCTION = """BEGIN
    IF to_jsonb(NEW) - 'status' - 'row_version' IS DISTINCT FROM to_jsonb(OLD) - 'status' - 'row_version' THEN
        RAISE EXCEPTION 'PR-17D AuditFinding material is immutable' USING ERRCODE='P17D1', CONSTRAINT='pr17d_audit_finding_immutable';
    END IF;
    IF NEW.row_version <> OLD.row_version + 1 OR NOT (
       (OLD.status='open' AND NEW.status IN ('confirmed','dismissed')) OR
       (OLD.status='confirmed' AND NEW.status IN ('resolved','dismissed'))
    ) THEN
        RAISE EXCEPTION 'PR-17D illegal AuditFinding transition' USING ERRCODE='P17D2', CONSTRAINT='pr17d_audit_finding_transition';
    END IF;
    RETURN NEW;
END;"""


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _preflight(*, canonical_only: bool) -> None:
    bind = op.get_bind()
    for (table, column), mapping in _COLUMN_MAPPINGS.items():
        allowed = set(mapping.values()) if canonical_only else set(mapping) | set(mapping.values())
        rows = bind.execute(
            text(f"SELECT {column}, count(*) FROM public.{table} GROUP BY {column}")
        ).all()
        for value, count in rows:
            if value is None or value not in allowed:
                raise RuntimeError(f"0017 preflight failed for {table}.{column}: {value!r}")
            logger.info("0017 preflight %s.%s value=%s rows=%s", table, column, value, count)


def _set_triggers(*, enabled: bool) -> None:
    command = "ENABLE" if enabled else "DISABLE"
    for table in _TRIGGER_TABLES:
        op.execute(f"ALTER TABLE public.{table} {command} TRIGGER USER")


def _convert_columns(*, to_canonical: bool) -> None:
    bind = op.get_bind()
    for (table, column), mapping in _COLUMN_MAPPINGS.items():
        conversion = mapping if to_canonical else {new: old for old, new in mapping.items()}
        case_branches = " ".join(
            f"WHEN {_quote(old)} THEN {_quote(new)}" for old, new in conversion.items()
        )
        source_sql = ", ".join(_quote(value) for value in conversion)
        result = bind.execute(
            text(
                f"UPDATE public.{table} SET {column} = CASE {column} {case_branches} ELSE {column} END "
                f"WHERE {column} IN ({source_sql})"
            )
        )
        logger.info(
            "0017 converted %s.%s direction=%s rows=%s",
            table,
            column,
            "canonical" if to_canonical else "legacy",
            result.rowcount,
        )


def _drop_old_checks() -> None:
    for table, name, _expression in _CHECKS:
        op.drop_constraint(name, table, type_="check")


def _create_canonical_checks() -> None:
    for table, name, expression in _CHECKS:
        op.create_check_constraint(name, table, expression)


def _drop_canonical_checks() -> None:
    for table, name in _TARGET_TYPE_CHECKS:
        op.drop_constraint(name, table, type_="check")
    _drop_old_checks()


def _create_target_type_checks() -> None:
    values = ", ".join(_quote(value) for value in TARGET_TYPE_CANONICAL)
    for table, name in _TARGET_TYPE_CHECKS:
        op.create_check_constraint(name, table, f"target_type IN ({values})")


def _replace_audit_transition_function(body: str) -> None:
    op.execute(
        "CREATE OR REPLACE FUNCTION public.pr17d_guard_audit_finding_transition() "
        "RETURNS trigger LANGUAGE plpgsql AS $$\n" + body + "\n$$;"
    )


def upgrade() -> None:
    _preflight(canonical_only=False)
    _drop_old_checks()
    _set_triggers(enabled=False)
    try:
        _convert_columns(to_canonical=True)
        op.alter_column("projects", "lifecycle_status", server_default=text("'ACTIVE'"))
        op.alter_column("workspaces", "lifecycle_status", server_default=text("'ACTIVE'"))
        op.alter_column("datasets", "lifecycle_status", server_default=text("'ACTIVE'"))
        op.alter_column("audit_findings", "status", server_default=text("'OPEN'"))
        _replace_audit_transition_function(CANONICAL_AUDIT_TRANSITION_FUNCTION)
    finally:
        _set_triggers(enabled=True)
    _create_canonical_checks()
    _create_target_type_checks()
    _preflight(canonical_only=True)


def _legacy_check_expression(name: str) -> str:
    return {
        "ck_actors_actor_type": "actor_type IN ('human', 'agent', 'service')",
        "ck_projects_lifecycle_status": "lifecycle_status IN ('active', 'archived', 'retired')",
        "ck_workspaces_lifecycle_status": "lifecycle_status IN ('active', 'archived', 'retired')",
        "ck_datasets_lifecycle_status": "lifecycle_status IN ('active', 'archived', 'retired')",
        "ck_evidence_relations_relation_type": "relation_type IN ('supports', 'contradicts', 'qualifies', 'context')",
        "ck_audit_findings_severity": "severity IN ('info','minor','major','critical')",
        "ck_audit_findings_status": "status IN ('open','confirmed','dismissed','resolved')",
        "ck_impact_assessments_conclusion": "conclusion IN ('no_impact','stale','invalid','requires_review','unknown')",
        "ck_impact_targets_kind": "impact_kind IN ('direct','downstream','stale','invalid','requires_review')",
        "ck_correction_records_type": "correction_type IN ('factual','metadata','computational','attribution','other')",
    }[name]


def downgrade() -> None:
    _preflight(canonical_only=True)
    _drop_canonical_checks()
    _set_triggers(enabled=False)
    try:
        _convert_columns(to_canonical=False)
        op.alter_column("projects", "lifecycle_status", server_default=text("'active'"))
        op.alter_column("workspaces", "lifecycle_status", server_default=text("'active'"))
        op.alter_column("datasets", "lifecycle_status", server_default=text("'active'"))
        op.alter_column("audit_findings", "status", server_default=text("'open'"))
        _replace_audit_transition_function(LEGACY_AUDIT_TRANSITION_FUNCTION)
    finally:
        _set_triggers(enabled=True)
    for table, name, _expression in _CHECKS:
        op.create_check_constraint(name, table, _legacy_check_expression(name))
    _preflight(canonical_only=False)
