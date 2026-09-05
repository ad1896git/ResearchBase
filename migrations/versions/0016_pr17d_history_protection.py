"""Install the PR-17D PostgreSQL history-protection policy."""

# SQL function bodies are kept legible as PostgreSQL source strings.
# ruff: noqa: E501

from __future__ import annotations

from alembic import op

revision: str = "0016_pr17d_history_protection"
down_revision: str | None = "0015_governance_audit"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

FUNCTION_NAMES = (
    "pr17d_guard_research_question_version",
    "pr17d_guard_hypothesis_version",
    "pr17d_guard_experiment_spec_version",
    "pr17d_guard_artifact_version",
    "pr17d_guard_metric_definition_version",
    "pr17d_guard_claim_version",
    "pr17d_reject_dataset_snapshot_mutation",
    "pr17d_reject_measurement_mutation",
    "pr17d_reject_statistical_result_mutation",
    "pr17d_reject_statistical_result_input_mutation",
    "pr17d_guard_run",
    "pr17d_guard_run_input_parent",
    "pr17d_guard_evidence_relation_parent",
    "pr17d_reject_audit_finding_mutation",
    "pr17d_guard_audit_finding_transition",
    "pr17d_reject_impact_assessment_mutation",
    "pr17d_reject_impact_target_mutation",
    "pr17d_reject_correction_record_mutation",
)

TRIGGER_DEFINITIONS = (
    (
        "pr17d_research_question_version_update",
        "research_question_versions",
        "UPDATE",
        "pr17d_guard_research_question_version",
    ),
    (
        "pr17d_research_question_version_delete",
        "research_question_versions",
        "DELETE",
        "pr17d_guard_research_question_version",
    ),
    (
        "pr17d_hypothesis_version_update",
        "hypothesis_versions",
        "UPDATE",
        "pr17d_guard_hypothesis_version",
    ),
    (
        "pr17d_hypothesis_version_delete",
        "hypothesis_versions",
        "DELETE",
        "pr17d_guard_hypothesis_version",
    ),
    (
        "pr17d_experiment_spec_version_update",
        "experiment_spec_versions",
        "UPDATE",
        "pr17d_guard_experiment_spec_version",
    ),
    (
        "pr17d_experiment_spec_version_delete",
        "experiment_spec_versions",
        "DELETE",
        "pr17d_guard_experiment_spec_version",
    ),
    (
        "pr17d_artifact_version_update",
        "artifact_versions",
        "UPDATE",
        "pr17d_guard_artifact_version",
    ),
    (
        "pr17d_artifact_version_delete",
        "artifact_versions",
        "DELETE",
        "pr17d_guard_artifact_version",
    ),
    (
        "pr17d_metric_definition_version_update",
        "metric_definition_versions",
        "UPDATE",
        "pr17d_guard_metric_definition_version",
    ),
    (
        "pr17d_metric_definition_version_delete",
        "metric_definition_versions",
        "DELETE",
        "pr17d_guard_metric_definition_version",
    ),
    ("pr17d_claim_version_update", "claim_versions", "UPDATE", "pr17d_guard_claim_version"),
    ("pr17d_claim_version_delete", "claim_versions", "DELETE", "pr17d_guard_claim_version"),
    (
        "pr17d_dataset_snapshot_update",
        "dataset_snapshots",
        "UPDATE",
        "pr17d_reject_dataset_snapshot_mutation",
    ),
    (
        "pr17d_dataset_snapshot_delete",
        "dataset_snapshots",
        "DELETE",
        "pr17d_reject_dataset_snapshot_mutation",
    ),
    ("pr17d_measurement_update", "measurements", "UPDATE", "pr17d_reject_measurement_mutation"),
    ("pr17d_measurement_delete", "measurements", "DELETE", "pr17d_reject_measurement_mutation"),
    (
        "pr17d_statistical_result_update",
        "statistical_results",
        "UPDATE",
        "pr17d_reject_statistical_result_mutation",
    ),
    (
        "pr17d_statistical_result_delete",
        "statistical_results",
        "DELETE",
        "pr17d_reject_statistical_result_mutation",
    ),
    (
        "pr17d_statistical_result_input_update",
        "statistical_result_inputs",
        "UPDATE",
        "pr17d_reject_statistical_result_input_mutation",
    ),
    (
        "pr17d_statistical_result_input_delete",
        "statistical_result_inputs",
        "DELETE",
        "pr17d_reject_statistical_result_input_mutation",
    ),
    ("pr17d_run_update", "runs", "UPDATE", "pr17d_guard_run"),
    ("pr17d_run_delete", "runs", "DELETE", "pr17d_guard_run"),
    (
        "pr17d_run_dataset_input_insert",
        "run_dataset_inputs",
        "INSERT",
        "pr17d_guard_run_input_parent",
    ),
    (
        "pr17d_run_dataset_input_update",
        "run_dataset_inputs",
        "UPDATE",
        "pr17d_guard_run_input_parent",
    ),
    (
        "pr17d_run_dataset_input_delete",
        "run_dataset_inputs",
        "DELETE",
        "pr17d_guard_run_input_parent",
    ),
    (
        "pr17d_run_artifact_input_insert",
        "run_artifact_inputs",
        "INSERT",
        "pr17d_guard_run_input_parent",
    ),
    (
        "pr17d_run_artifact_input_update",
        "run_artifact_inputs",
        "UPDATE",
        "pr17d_guard_run_input_parent",
    ),
    (
        "pr17d_run_artifact_input_delete",
        "run_artifact_inputs",
        "DELETE",
        "pr17d_guard_run_input_parent",
    ),
    (
        "pr17d_evidence_relation_insert",
        "evidence_relations",
        "INSERT",
        "pr17d_guard_evidence_relation_parent",
    ),
    (
        "pr17d_evidence_relation_update",
        "evidence_relations",
        "UPDATE",
        "pr17d_guard_evidence_relation_parent",
    ),
    (
        "pr17d_evidence_relation_delete",
        "evidence_relations",
        "DELETE",
        "pr17d_guard_evidence_relation_parent",
    ),
    (
        "pr17d_audit_finding_update",
        "audit_findings",
        "UPDATE",
        "pr17d_reject_audit_finding_mutation",
    ),
    (
        "pr17d_audit_finding_delete",
        "audit_findings",
        "DELETE",
        "pr17d_reject_audit_finding_mutation",
    ),
    (
        "pr17d_audit_finding_transition",
        "audit_findings",
        "UPDATE",
        "pr17d_guard_audit_finding_transition",
    ),
    (
        "pr17d_impact_assessment_update",
        "impact_assessments",
        "UPDATE",
        "pr17d_reject_impact_assessment_mutation",
    ),
    (
        "pr17d_impact_assessment_delete",
        "impact_assessments",
        "DELETE",
        "pr17d_reject_impact_assessment_mutation",
    ),
    (
        "pr17d_impact_target_update",
        "impact_targets",
        "UPDATE",
        "pr17d_reject_impact_target_mutation",
    ),
    (
        "pr17d_impact_target_delete",
        "impact_targets",
        "DELETE",
        "pr17d_reject_impact_target_mutation",
    ),
    (
        "pr17d_correction_record_update",
        "correction_records",
        "UPDATE",
        "pr17d_reject_correction_record_mutation",
    ),
    (
        "pr17d_correction_record_delete",
        "correction_records",
        "DELETE",
        "pr17d_reject_correction_record_mutation",
    ),
)

_CLOSED_RULES = (
    ("actors", "actor_type", ("human", "agent", "service")),
    ("projects", "lifecycle_status", ("active", "archived", "retired")),
    ("workspaces", "lifecycle_status", ("active", "archived", "retired")),
    ("datasets", "lifecycle_status", ("active", "archived", "retired")),
    *(
        (table, "status", ("DRAFT", "FROZEN", "SUPERSEDED", "ABANDONED"))
        for table in (
            "research_question_versions",
            "hypothesis_versions",
            "experiment_spec_versions",
            "artifact_versions",
            "metric_definition_versions",
            "claim_versions",
        )
    ),
    ("runs", "status", ("PLANNED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED")),
    (
        "run_dataset_inputs",
        "role",
        ("train", "validation", "test", "calibration", "auxiliary", "other"),
    ),
    (
        "run_artifact_inputs",
        "role",
        (
            "source_code",
            "model",
            "checkpoint",
            "configuration",
            "environment_manifest",
            "script",
            "dependency_lock",
            "other",
        ),
    ),
    ("evidence_relations", "relation_type", ("supports", "contradicts", "qualifies", "context")),
    ("audit_findings", "severity", ("info", "minor", "major", "critical")),
    (
        "audit_findings",
        "target_type",
        (
            "experiment_spec_version",
            "dataset_snapshot",
            "artifact_version",
            "run",
            "metric_definition_version",
            "measurement",
            "statistical_result",
            "claim_version",
        ),
    ),
    ("audit_findings", "status", ("open", "confirmed", "dismissed", "resolved")),
    (
        "impact_assessments",
        "conclusion",
        ("no_impact", "stale", "invalid", "requires_review", "unknown"),
    ),
    (
        "impact_targets",
        "target_type",
        (
            "experiment_spec_version",
            "dataset_snapshot",
            "artifact_version",
            "run",
            "metric_definition_version",
            "measurement",
            "statistical_result",
            "claim_version",
        ),
    ),
    (
        "impact_targets",
        "impact_kind",
        ("direct", "downstream", "stale", "invalid", "requires_review"),
    ),
    (
        "correction_records",
        "target_type",
        (
            "experiment_spec_version",
            "dataset_snapshot",
            "artifact_version",
            "run",
            "metric_definition_version",
            "measurement",
            "statistical_result",
            "claim_version",
        ),
    ),
    (
        "correction_records",
        "correction_type",
        ("factual", "metadata", "computational", "attribution", "other"),
    ),
)
_OPEN_RULES = (
    ("runs", "run_type", 32),
    ("artifacts", "artifact_type", 32),
    ("statistical_results", "analysis_type", 64),
    ("statistical_result_inputs", "input_role", 32),
    ("audit_findings", "finding_type", 64),
)


def _preflight() -> None:
    for table, column, values in _CLOSED_RULES:
        quoted = ", ".join("'" + value.replace("'", "''") + "'" for value in values)
        op.execute(
            f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM {table} WHERE {column} IS NULL OR {column} NOT IN ({quoted})) THEN RAISE EXCEPTION 'PR-17D migration preflight failed for {table}.{column}' USING ERRCODE='P17D4', CONSTRAINT='pr17d_migration_preflight'; END IF; END $$;"
        )
    for table, column, limit in _OPEN_RULES:
        op.execute(
            f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM {table} WHERE {column} IS NULL OR btrim({column}) = '' OR char_length({column}) > {limit}) THEN RAISE EXCEPTION 'PR-17D migration preflight failed for {table}.{column}' USING ERRCODE='P17D4', CONSTRAINT='pr17d_migration_preflight'; END IF; END $$;"
        )


def _create_function(name: str, body: str) -> None:
    op.execute(f"CREATE FUNCTION {name}() RETURNS trigger LANGUAGE plpgsql AS $$\n{body}\n$$;")


def _reject_mutation(table: str, identifier: str) -> str:
    return f"""BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'PR-17D immutable historical record' USING ERRCODE='P17D1', CONSTRAINT='{identifier}_delete';
    END IF;
    RAISE EXCEPTION 'PR-17D immutable historical record' USING ERRCODE='P17D1', CONSTRAINT='{identifier}_immutable';
END;"""


def _version_guard(table: str) -> str:
    return f"""BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'PR-17D version deletion forbidden' USING ERRCODE='P17D1', CONSTRAINT='pr17d_{table}_delete';
    END IF;
    IF NEW.status = OLD.status AND OLD.status = 'DRAFT' THEN
        RETURN NEW;
    END IF;
    IF NOT ((OLD.status = 'DRAFT' AND NEW.status IN ('FROZEN','ABANDONED')) OR
            (OLD.status = 'FROZEN' AND NEW.status = 'SUPERSEDED')) THEN
        RAISE EXCEPTION 'PR-17D illegal version transition' USING ERRCODE='P17D2', CONSTRAINT='pr17d_{table}_transition';
    END IF;
    IF to_jsonb(NEW) - 'status' - 'row_version' - 'frozen_at' - 'content_hash' - 'support_set_hash'
       IS DISTINCT FROM to_jsonb(OLD) - 'status' - 'row_version' - 'frozen_at' - 'content_hash' - 'support_set_hash' THEN
        RAISE EXCEPTION 'PR-17D finalized version material is immutable' USING ERRCODE='P17D1', CONSTRAINT='pr17d_{table}_immutable';
    END IF;
    IF NEW.row_version <> OLD.row_version + 1 THEN
        RAISE EXCEPTION 'PR-17D stale version write' USING ERRCODE='P17D5', CONSTRAINT='pr17d_{table}_transition';
    END IF;
    RETURN NEW;
END;"""


def _run_guard() -> str:
    return """BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'PR-17D Run deletion forbidden' USING ERRCODE='P17D1', CONSTRAINT='pr17d_run_delete';
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id OR NEW.project_id IS DISTINCT FROM OLD.project_id OR
       NEW.experiment_spec_version_id IS DISTINCT FROM OLD.experiment_spec_version_id OR
       NEW.run_type IS DISTINCT FROM OLD.run_type OR NEW.created_by IS DISTINCT FROM OLD.created_by OR
       NEW.created_at IS DISTINCT FROM OLD.created_at OR NEW.row_version <> OLD.row_version + 1 THEN
        RAISE EXCEPTION 'PR-17D Run identity or stale mutation' USING ERRCODE='P17D1', CONSTRAINT='pr17d_run_immutable';
    END IF;
    IF NEW.status = OLD.status AND OLD.status = 'PLANNED' AND
       to_jsonb(NEW) - 'row_version' IS NOT DISTINCT FROM to_jsonb(OLD) - 'row_version' THEN
        RETURN NEW;
    END IF;
    IF OLD.status = 'PLANNED' AND NEW.status = 'RUNNING' AND
       NEW.inputs_sealed_at IS NOT NULL AND NEW.started_at = NEW.inputs_sealed_at AND
       NEW.finished_at IS NULL AND NEW.exit_code IS NULL AND NEW.failure_reason IS NULL THEN
        RETURN NEW;
    END IF;
    IF OLD.status = 'PLANNED' AND NEW.status = 'CANCELLED' AND
       NEW.inputs_sealed_at IS NOT NULL AND NEW.finished_at = NEW.inputs_sealed_at AND
       NEW.started_at IS NULL AND NEW.exit_code IS NULL AND NEW.failure_reason IS NULL THEN
        RETURN NEW;
    END IF;
    IF OLD.status = 'RUNNING' AND NEW.status IN ('SUCCEEDED','FAILED','CANCELLED') AND
       NEW.inputs_sealed_at = OLD.inputs_sealed_at AND NEW.started_at = OLD.started_at AND
       NEW.finished_at IS NOT NULL AND OLD.finished_at IS NULL THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'PR-17D illegal Run transition or field combination' USING ERRCODE='P17D2', CONSTRAINT='pr17d_run_transition';
END;"""


def _run_input_guard() -> str:
    return """DECLARE
    run_status text;
    run_sealed timestamptz;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'PR-17D RunInput in-place mutation forbidden' USING ERRCODE='P17D1', CONSTRAINT='pr17d_run_input_update';
    END IF;
    SELECT status, inputs_sealed_at INTO run_status, run_sealed FROM runs
      WHERE id = CASE WHEN TG_OP = 'DELETE' THEN OLD.run_id ELSE NEW.run_id END FOR UPDATE;
    IF run_status IS NULL THEN
        RAISE EXCEPTION 'PR-17D Run parent missing' USING ERRCODE='P17D3', CONSTRAINT='pr17d_run_input_parent_state';
    END IF;
    IF run_status <> 'PLANNED' OR run_sealed IS NOT NULL THEN
        RAISE EXCEPTION 'PR-17D RunInput parent is protected' USING ERRCODE='P17D1', CONSTRAINT='pr17d_run_input_parent_state';
    END IF;
    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;"""


def _evidence_guard() -> str:
    return """DECLARE parent_status text;
BEGIN
    SELECT status INTO parent_status FROM claim_versions
      WHERE id = CASE WHEN TG_OP = 'DELETE' THEN OLD.claim_version_id ELSE NEW.claim_version_id END FOR UPDATE;
    IF parent_status IS DISTINCT FROM 'DRAFT' THEN
        RAISE EXCEPTION 'PR-17D evidence parent is protected' USING ERRCODE='P17D1', CONSTRAINT='pr17d_evidence_relation_parent_state';
    END IF;
    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;"""


def _audit_material_guard() -> str:
    return """BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'PR-17D AuditFinding deletion forbidden' USING ERRCODE='P17D1', CONSTRAINT='pr17d_audit_finding_delete';
    END IF;
    IF to_jsonb(NEW) - 'status' - 'row_version' IS DISTINCT FROM to_jsonb(OLD) - 'status' - 'row_version' THEN
        RAISE EXCEPTION 'PR-17D AuditFinding material is immutable' USING ERRCODE='P17D1', CONSTRAINT='pr17d_audit_finding_immutable';
    END IF;
    RETURN NEW;
END;"""


def _audit_transition_guard() -> str:
    return """BEGIN
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


def upgrade() -> None:
    _preflight()
    for name, table in zip(
        FUNCTION_NAMES[:6],
        (
            "research_question_versions",
            "hypothesis_versions",
            "experiment_spec_versions",
            "artifact_versions",
            "metric_definition_versions",
            "claim_versions",
        ),
        strict=True,
    ):
        _create_function(name, _version_guard(table))
    _create_function(
        FUNCTION_NAMES[6], _reject_mutation("dataset_snapshots", "pr17d_dataset_snapshot")
    )
    _create_function(FUNCTION_NAMES[7], _reject_mutation("measurements", "pr17d_measurement"))
    _create_function(
        FUNCTION_NAMES[8], _reject_mutation("statistical_results", "pr17d_statistical_result")
    )
    _create_function(
        FUNCTION_NAMES[9],
        _reject_mutation("statistical_result_inputs", "pr17d_statistical_result_input"),
    )
    _create_function(FUNCTION_NAMES[10], _run_guard())
    _create_function(FUNCTION_NAMES[11], _run_input_guard())
    _create_function(FUNCTION_NAMES[12], _evidence_guard())
    _create_function(FUNCTION_NAMES[13], _audit_material_guard())
    _create_function(FUNCTION_NAMES[14], _audit_transition_guard())
    _create_function(
        FUNCTION_NAMES[15], _reject_mutation("impact_assessments", "pr17d_impact_assessment")
    )
    _create_function(FUNCTION_NAMES[16], _reject_mutation("impact_targets", "pr17d_impact_target"))
    _create_function(
        FUNCTION_NAMES[17], _reject_mutation("correction_records", "pr17d_correction_record")
    )
    for trigger, table, event, function in TRIGGER_DEFINITIONS:
        op.execute(
            f"CREATE TRIGGER {trigger} BEFORE {event} ON {table} FOR EACH ROW EXECUTE FUNCTION {function}();"
        )


def downgrade() -> None:
    for trigger, table, _event, _function in reversed(TRIGGER_DEFINITIONS):
        op.execute(f"DROP TRIGGER IF EXISTS {trigger} ON public.{table};")
    for function in reversed(FUNCTION_NAMES):
        op.execute(f"DROP FUNCTION IF EXISTS {function}();")
