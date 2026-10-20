"""B04 fixed snapshot inventory and guarded exact-version persistence."""

# SQL preserves the fixed relational contract.
# ruff: noqa: E501

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Select, event, text
from sqlalchemy.orm import ORMExecuteState, Session

from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

B04_SNAPSHOT_TABLES = tuple(
    sorted(
        """actor_subject_bindings actors artifact_versions artifacts audit_findings
claim_versions claims correction_records dataset_snapshots datasets
evidence_relations experiment_spec_versions experiment_specs impact_assessments
impact_targets literature_evidence literature_evidence_review_events
literature_evidence_relations literature_source_project_links literature_sources
literature_support_snapshots manuscript_artifact_placements
manuscript_citation_placements manuscript_claim_placements measurements
metric_definition_versions metric_definitions project_membership_events
project_memberships project_role_assignments projects run_artifact_inputs
run_dataset_inputs runs scientific_conclusion_claim_inputs
scientific_conclusion_literature_inputs scientific_conclusion_versions
scientific_conclusions source_versions statistical_result_inputs statistical_results""".split()
    )
)
M1_EDIT_TABLES = (
    "manuscript_artifact_placements",
    "manuscript_citation_placements",
    "manuscript_claim_placements",
    "manuscript_versions",
    "publications",
)
M1_SNAPSHOT_TABLES = tuple(t for t in B04_SNAPSHOT_TABLES if t not in M1_EDIT_TABLES)
M1_SHARE_SQL = "LOCK TABLE " + ",".join(M1_SNAPSHOT_TABLES) + " IN SHARE MODE"
M1_EDIT_SQL = "LOCK TABLE " + ",".join(M1_EDIT_TABLES) + " IN EXCLUSIVE MODE"

B04_SHARE_SQL = "LOCK TABLE " + ",".join(B04_SNAPSHOT_TABLES) + " IN SHARE MODE"


def _bounded_audit_select(state: ORMExecuteState):
    statement = state.statement
    sql = str(statement).lstrip()
    if sql.upper().startswith(("SELECT", "WITH")):
        statement = (
            text("SELECT * FROM (" + sql + ") AS b25_bounded_read LIMIT 10001")
            if not state.is_select
            else cast(Select[Any], statement).limit(10001)
        )
        result = state.invoke_statement(statement=statement)
        frozen = result.freeze()
        if len(frozen.data) > 10000:
            raise ResearchBaseError(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "complete manuscript audit exceeds fixed row ceiling",
            )
        return frozen()
    return state.invoke_statement()


class SqlAlchemyManuscriptFreezeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def prepare_revision_write(self) -> None:
        self._session.execute(text(M1_SHARE_SQL))
        self._session.execute(text(M1_EDIT_SQL))
        self._session.execute(text("SET LOCAL lock_timeout='10s'"))
        self._session.execute(text("SET LOCAL statement_timeout='30s'"))

    def prepare_write(self) -> None:
        """B04's original inventory; successor editing uses prepare_revision_write."""
        if not self._session.in_transaction():
            self._session.connection(execution_options={"isolation_level": "READ COMMITTED"})
        self._session.execute(text(B04_SHARE_SQL))
        self._session.execute(text("SET LOCAL lock_timeout='10s'"))
        self._session.execute(text("SET LOCAL statement_timeout='30s'"))

    def prepare_read(self, *, bounded: bool = False) -> None:
        self._session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        if bounded:
            # B25-only guard: bound every owner SELECT before DBAPI materialization.
            # The listener lives on this fresh Session, never on the factory/engine.
            event.listen(self._session, "do_orm_execute", _bounded_audit_select, retval=True)

    def authority(self, principal: VerifiedPrincipal, project: UUID) -> list[dict]:
        return [
            dict(row)
            for row in self._session.execute(
                text("""SELECT a.actor_type,a.retired_at,m.status AS membership_status,
          r.role,r.effective_from,r.effective_until,b.status AS binding_status,b.bound_at,b.revoked_at,
          p.lifecycle_status AS project_status
          FROM actors a JOIN project_memberships m ON m.actor_id=a.id
          JOIN projects p ON p.id=m.project_id
          JOIN project_role_assignments r ON r.membership_id=m.id AND r.project_id=m.project_id AND r.actor_id=m.actor_id
          JOIN actor_subject_bindings b ON b.actor_id=a.id
          WHERE a.id=:actor AND m.project_id=:project AND b.deployment_id=:deployment
            AND b.subject_kind=:kind AND b.subject_value=:value AND b.subject_credential_id=:credential
          ORDER BY a.id,m.id,r.id,b.id"""),
                {
                    "actor": principal.actor_id,
                    "project": project,
                    "deployment": principal.deployment_id,
                    "kind": principal.subject_kind,
                    "value": principal.subject_value,
                    "credential": principal.credential_id,
                },
            ).mappings()
        ]

    def version(self, identity: UUID, publication: UUID, *, lock: bool = False) -> dict | None:
        row = (
            self._session.execute(
                text(
                    "SELECT * FROM manuscript_versions WHERE id=:id AND publication_id=:publication"
                    + (" FOR UPDATE" if lock else "")
                ),
                {"id": identity, "publication": publication},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def artifact(self, identity: UUID, project: UUID) -> dict | None:
        row = (
            self._session.execute(
                text(
                    """SELECT v.*,a.project_id,a.artifact_type FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id WHERE v.id=:id AND a.project_id=:project"""
                ),
                {"id": identity, "project": project},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def conclusion_parent(self, identity: UUID, project: UUID) -> UUID | None:
        return self._session.execute(
            text(
                """SELECT v.scientific_conclusion_id FROM scientific_conclusion_versions v JOIN scientific_conclusions c ON c.id=v.scientific_conclusion_id WHERE v.id=:id AND c.project_id=:project"""
            ),
            {"id": identity, "project": project},
        ).scalar_one_or_none()

    def at(self) -> datetime:
        return self._session.execute(text("SELECT clock_timestamp()")).scalar_one().astimezone(UTC)

    def seal(self, row: dict, parent: dict, placement: str, content: str, at: datetime) -> None:
        result = self._session.execute(
            text(
                """UPDATE manuscript_versions SET status='FROZEN',placement_set_hash=:placement,content_hash=:content,frozen_at=:at,row_version=row_version+1 WHERE id=:id AND status='DRAFT' AND row_version=:version"""
            ),
            {
                "id": row["id"],
                "version": row["row_version"],
                "placement": placement,
                "content": content,
                "at": at,
            },
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, "manuscript changed")
        result = self._session.execute(
            text(
                """UPDATE publications SET current_manuscript_version_id=:manuscript,row_version=row_version+1 WHERE id=:id AND row_version=:version AND lifecycle_status IN ('DRAFTING','INTERNAL_REVIEW') AND current_manuscript_version_id IS NOT DISTINCT FROM :predecessor"""
            ),
            {
                "id": parent["id"],
                "version": parent["row_version"],
                "manuscript": row["id"],
                "predecessor": parent["current_manuscript_version_id"],
            },
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, "publication changed")

    def force_constraints(self) -> None:
        self._session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
