"""Fixed dependency paths for scoped context preflight, before owner hydration.

These are read paths over existing concrete relations, not new input families.
Every node is scoped before its outgoing relations are read.
"""

from __future__ import annotations

from typing import Any, NoReturn

from sqlalchemy import text

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.research_task_queries import INPUT_FAMILIES

# table -> (owner table, owner FK, whether the owning contract permits NULL project)
OWNERS = {value[1]: (value[2], value[3], False) for value in INPUT_FAMILIES.values()} | {
    "experiment_spec_versions": ("experiment_specs", "experiment_spec_id", False),
    "dataset_snapshots": ("datasets", "dataset_id", True),
    "metric_definition_versions": ("metric_definitions", "metric_definition_id", True),
    "scientific_conclusion_versions": ("scientific_conclusions", "scientific_conclusion_id", False),
}
DIRECT = frozenset(
    {"runs", "statistical_results", "literature_evidence", "literature_support_snapshots"}
)
# Single-row concrete edges; identity-owner/current pointers are deliberately absent.
EDGES = {
    "source_versions": (
        ("predecessor_source_version_id", "source_versions"),
        ("fulltext_artifact_version_id", "artifact_versions"),
        ("correction_basis_artifact_version_id", "artifact_versions"),
    ),
    "manuscript_versions": (("document_artifact_version_id", "artifact_versions"),),
    "measurements": (
        ("run_id", "runs"),
        ("metric_definition_version_id", "metric_definition_versions"),
    ),
    "runs": (("experiment_spec_version_id", "experiment_spec_versions"),),
    "literature_evidence": (("source_version_id", "source_versions"),),
    "literature_support_snapshots": (
        ("previous_snapshot_id", "literature_support_snapshots"),
        ("claim_version_id", "claim_versions"),
        ("research_question_version_id", "research_question_versions"),
        ("hypothesis_version_id", "hypothesis_versions"),
    ),
}
# owner table -> (relation table, owner FK, ((target FK, target table), ...))
RELATIONS = {
    "claim_versions": (
        (
            "evidence_relations",
            "claim_version_id",
            (
                ("measurement_id", "measurements"),
                ("statistical_result_id", "statistical_results"),
            ),
        ),
    ),
    "statistical_results": (
        (
            "statistical_result_inputs",
            "statistical_result_id",
            (("measurement_id", "measurements"),),
        ),
    ),
    "runs": (
        ("run_artifact_inputs", "run_id", (("artifact_version_id", "artifact_versions"),)),
        ("run_dataset_inputs", "run_id", (("dataset_snapshot_id", "dataset_snapshots"),)),
        ("measurements", "run_id", (("id", "measurements"),)),
    ),
    "manuscript_versions": (
        (
            "manuscript_claim_placements",
            "manuscript_version_id",
            (
                ("claim_version_id", "claim_versions"),
                ("scientific_conclusion_version_id", "scientific_conclusion_versions"),
            ),
        ),
        (
            "manuscript_citation_placements",
            "manuscript_version_id",
            (("source_version_id", "source_versions"),),
        ),
        (
            "manuscript_artifact_placements",
            "manuscript_version_id",
            (("artifact_version_id", "artifact_versions"),),
        ),
    ),
    "scientific_conclusion_versions": (
        (
            "scientific_conclusion_claim_inputs",
            "conclusion_version_id",
            (
                ("claim_version_id", "claim_versions"),
                ("literature_support_snapshot_id", "literature_support_snapshots"),
            ),
        ),
        (
            "scientific_conclusion_literature_inputs",
            "conclusion_version_id",
            (("literature_evidence_id", "literature_evidence"),),
        ),
    ),
    "literature_support_snapshots": (
        (
            "literature_evidence_relations",
            "literature_support_snapshot_id",
            (("literature_evidence_id", "literature_evidence"),),
        ),
    ),
}


def failure(code=ErrorCode.PROVENANCE_CLOSURE_VIOLATION) -> NoReturn:
    raise ResearchBaseError(code, "required context dependency unavailable")


def scoped_node(session, table, identity, project) -> dict[str, Any]:
    """Private raw rows stay inside persistence. All SQL names are fixed above."""
    if table in OWNERS:
        owner, fk, global_allowed = OWNERS[table]
        scope = "o.project_id=:project"
        if table == "source_versions":
            scope = (
                "EXISTS(SELECT 1 FROM literature_source_project_links l "
                "WHERE l.literature_source_id=o.id AND l.project_id=:project)"
            )
        elif global_allowed:
            scope = "(o.project_id=:project OR o.project_id IS NULL)"
        query = (
            f"SELECT v.*, {scope} AS scoped FROM {table} v "
            f"JOIN {owner} o ON o.id=v.{fk} WHERE v.id=:id"
        )
    elif table == "measurements":
        query = (
            "SELECT v.*, r.project_id=:project AS scoped FROM measurements v "
            "JOIN runs r ON r.id=v.run_id WHERE v.id=:id"
        )
    elif table in DIRECT:
        query = f"SELECT v.*, v.project_id=:project AS scoped FROM {table} v WHERE v.id=:id"
    else:
        raise ValueError("unsupported context path")
    row = session.execute(text(query), {"id": identity, "project": project}).mappings().first()
    if row is None:
        failure()
    if not row["scoped"]:
        failure(ErrorCode.FORBIDDEN)
    return dict(row)


def preflight(session, table, identity, project):
    """Iterative complete scope walk. Cycles are checked by owning closure verifiers."""
    pending = [(table, identity)]
    checked: dict[tuple[str, Any], dict[str, Any]] = {}
    while pending:
        kind, key = pending.pop()
        if (kind, key) in checked:
            continue
        row = scoped_node(session, kind, key, project)
        checked[kind, key] = row
        for column, target in EDGES.get(kind, ()):
            if row[column] is not None:
                pending.append((target, row[column]))
        for relation, fk, targets in RELATIONS.get(kind, ()):
            rows = session.execute(
                text(f"SELECT * FROM {relation} WHERE {fk}=:id"), {"id": key}
            ).mappings()
            for edge in rows:
                for column, target in targets:
                    if edge[column] is not None:
                        pending.append((target, edge[column]))
    return checked
