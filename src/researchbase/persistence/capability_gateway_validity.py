"""Gateway-only validity snapshots; two statements per nonempty target set."""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import text

from researchbase.application.governance_queries import ValidityProjection, ValidityState
from researchbase.domain.governance import GovernanceTargetType
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

# Closed resolver ownership paths, matching SqlAlchemyGovernanceRepository.
_TARGETS = {
    "experiment_spec_version": (
        "experiment_spec_versions",
        "experiment_specs",
        "experiment_spec_id",
    ),
    "dataset_snapshot": ("dataset_snapshots", "datasets", "dataset_id"),
    "artifact_version": ("artifact_versions", "artifacts", "artifact_id"),
    "run": ("runs", None, None),
    "metric_definition_version": (
        "metric_definition_versions",
        "metric_definitions",
        "metric_definition_id",
    ),
    "measurement": ("measurements", "runs", "run_id"),
    "statistical_result": ("statistical_results", None, None),
    "claim_version": ("claim_versions", "claims", "claim_id"),
}


def validity_projections(
    session, project: UUID, targets: Sequence[tuple[str, UUID]], *, defer_errors=False
):
    """Return shared DTOs; optionally defer resolver errors to ordered gateway traversal."""
    keys = tuple(
        dict.fromkeys((GovernanceTargetType(kind), identity) for kind, identity in targets)
    )
    if not keys:
        return {}
    params: dict[str, Any] = {"project": project}
    values = []
    for i, (kind, identity) in enumerate(keys):
        params[f"kind{i}"] = kind.value.upper()
        params[f"id{i}"] = identity
        values.append(f"(CAST(:kind{i} AS text), CAST(:id{i} AS uuid))")
    requested = "WITH requested(kind,id) AS (VALUES " + ",".join(values) + ") "
    branches = []
    for kind in dict.fromkeys(kind for kind, _ in keys):
        table, parent, fk = _TARGETS[kind]
        owner = "o" if parent else "v"
        join = f" JOIN {parent} o ON o.id=v.{fk}" if parent else ""
        branches.append(
            f"SELECT r.kind,r.id,{owner}.project_id FROM requested r "
            f"JOIN {table} v ON v.id=r.id{join} WHERE r.kind='{kind.value.upper()}'"
        )
    resolved = {
        (GovernanceTargetType(row[0].lower()), row[1]): row[2]
        for row in session.execute(text(requested + " UNION ALL ".join(branches)), params)
    }
    errors = {}
    for key in keys:
        if resolved.get(key) is None:
            errors[key] = ResearchBaseError(ErrorCode.NOT_FOUND, f"{key[0].value} target not found")
        elif resolved[key] != project:
            errors[key] = ResearchBaseError(
                ErrorCode.VALIDATION_ERROR, "governance target belongs to another project"
            )
        if key in errors and not defer_errors:
            raise errors[key]
    rows = session.execute(
        text(
            requested
            + """
        SELECT r.kind,r.id,a.id,lower(a.conclusion),f.id,lower(f.status),NULL::uuid
        FROM requested r JOIN impact_targets t ON t.target_type=r.kind AND t.target_id=r.id
        JOIN impact_assessments a ON a.id=t.impact_assessment_id
        LEFT JOIN audit_findings f ON f.id=a.audit_finding_id
        WHERE a.project_id=:project
        UNION ALL
        SELECT r.kind,r.id,NULL::uuid,NULL::text,NULL::uuid,NULL::text,c.id
        FROM requested r JOIN correction_records c ON c.target_type=r.kind AND c.target_id=r.id
        WHERE c.project_id=:project
    """
        ),
        params,
    )
    active = {key: [] for key in keys}
    corrections = {key: set() for key in keys}
    for kind, identity, assessment, conclusion, finding, status, correction in rows:
        key = (GovernanceTargetType(kind.lower()), identity)
        if correction is not None:
            corrections[key].add(correction)
        elif status != "dismissed":
            active[key].append((assessment, conclusion, finding))
    states = {
        "no_impact": ValidityState.UNAFFECTED,
        "unknown": ValidityState.UNKNOWN,
        "requires_review": ValidityState.REQUIRES_REVIEW,
        "stale": ValidityState.STALE,
        "invalid": ValidityState.INVALID,
    }
    precedence = {state: i for i, state in enumerate(states.values())}
    result = {}
    for kind, identity in keys:
        key = (kind, identity)
        items = active[key]
        result[key] = (
            errors[key]
            if key in errors
            else ValidityProjection(
                kind,
                identity,
                max((states[row[1]] for row in items), key=precedence.__getitem__)
                if items
                else ValidityState.NOT_ASSESSED,
                tuple(sorted({row[2] for row in items if row[2] is not None}, key=str)),
                tuple(sorted({row[0] for row in items}, key=str)),
                tuple(sorted(corrections[key], key=str)),
            )
        )
    return result
