"""Narrow PostgreSQL adapter for immutable PR2-14 initial reviews."""

# SQL preserves the literal relational contract.
# ruff: noqa: E501

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.decision_repository import SqlAlchemyDecisionRepository
from researchbase.persistence.manuscript_freeze_repository import B04_SNAPSHOT_TABLES
from researchbase.persistence.novelty_repository import N

B23_SNAPSHOT_TABLES = N

# Same fixed inventory as B04; review tables are coordinated through the target.
B05_SNAPSHOT_TABLES = B04_SNAPSHOT_TABLES
B05_SHARE_SQL = "LOCK TABLE " + ",".join(B05_SNAPSHOT_TABLES) + " IN SHARE MODE"


class SqlAlchemyInternalReviewRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._write_prepared = False

    def prepare_novelty_write(self, kind: str, key: str) -> None:
        self._session.connection(execution_options={"isolation_level": "READ COMMITTED"})
        self._session.execute(
            text("LOCK TABLE " + ",".join(B23_SNAPSHOT_TABLES) + " IN SHARE MODE")
        )
        owners = {
            "review": "internal_review_records,review_issue_events,review_issues",
            "revision": "revision_actions",
            "link": "revision_action_re_reviews",
        }
        self._session.execute(text("LOCK TABLE " + owners[kind] + " IN ROW EXCLUSIVE MODE"))
        self._session.execute(text("SET LOCAL lock_timeout='10s'"))
        self._session.execute(text("SET LOCAL statement_timeout='30s'"))
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": key}
        )

    def lock_novelty_targets(self, claim: UUID, assessments: tuple[UUID, ...]) -> None:
        self._session.execute(
            text("SELECT id FROM claim_versions WHERE id=:id FOR UPDATE"), {"id": claim}
        )
        self._session.execute(
            text("SELECT id FROM novelty_assessments WHERE id=ANY(:ids) ORDER BY id FOR SHARE"),
            {"ids": list(assessments)},
        )

    def force_novelty_constraints(self) -> None:
        self._session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

    def prepare_insert(self) -> None:
        # Reserve the INSERT table mode before target/authority row locks. B07's
        # SHARE inventory must exclude us before either side can take FK locks.
        # Review writers remain mutually compatible; no SHARE upgrade is needed.
        self._session.execute(text("LOCK TABLE internal_review_records IN ROW EXCLUSIVE MODE"))

    def lock_request(self, identity: UUID) -> None:
        # B10's N inventory includes this owning table. Reserve our ordinary
        # write lock before taking a target row, so an N-first writer cannot hold
        # SHARE while waiting for a target held by a not-yet-inserted review.
        self._session.execute(text("LOCK TABLE internal_review_records IN ROW EXCLUSIVE MODE"))
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"pr214:review:{identity}"},
        )

    def review(self, identity: UUID, project: UUID) -> dict | None:
        row = (
            self._session.execute(
                text("""SELECT * FROM internal_review_records
          WHERE id=:id AND project_id=:project"""),
                {"id": identity, "project": project},
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row else None

    def conclusion_target(
        self, identity: UUID, project: UUID, *, lock: bool = False
    ) -> dict | None:
        if lock:
            # Lock exact target before the parent; a joined locking query cannot
            # guarantee that order. The subsequent statement rereads after waits.
            self._session.execute(
                text("""SELECT id FROM scientific_conclusion_versions
              WHERE id=:id FOR UPDATE"""),
                {"id": identity},
            ).one_or_none()
        suffix = " FOR UPDATE OF c" if lock else ""
        row = (
            self._session.execute(
                text(
                    """SELECT v.id,v.scientific_conclusion_id,
          v.status,v.frozen_at,v.content_hash,v.created_by
          FROM scientific_conclusion_versions v
          JOIN scientific_conclusions c ON c.id=v.scientific_conclusion_id
          WHERE v.id=:id AND c.project_id=:project"""
                    + suffix
                ),
                {"id": identity, "project": project},
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row else None

    def issues(self, identity: UUID) -> list[dict]:
        rows = (
            self._session.execute(
                text("""SELECT * FROM review_issues
          WHERE review_record_id=:id ORDER BY ordinal,id"""),
                {"id": identity},
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    def insert_review(self, values: dict[str, object]) -> None:
        if "novelty_assessment_id" not in values and values.get("material_version", 1) == 1:
            # The accepted v1 writer also runs against historical migration points.
            self._session.execute(
                text("""INSERT INTO internal_review_records
                (id,project_id,manuscript_version_id,claim_version_id,scientific_conclusion_version_id,
                 target_content_hash,reviewer_actor_id,review_type,recommendation,summary,
                 created_at,content_hash,hash_scheme)
                VALUES (:id,:project_id,:manuscript_version_id,:claim_version_id,
                 :scientific_conclusion_version_id,:target_content_hash,:reviewer_actor_id,
                 :review_type,:recommendation,:summary,:created_at,:content_hash,:hash_scheme)"""),
                {"manuscript_version_id": None, **values},
            )
            return
        values = {
            "manuscript_version_id": None,
            "novelty_assessment_id": None,
            "material_version": 1,
            **values,
        }
        self._session.execute(
            text("""INSERT INTO internal_review_records
          (id,project_id,manuscript_version_id,claim_version_id,scientific_conclusion_version_id,novelty_assessment_id,material_version,
           target_content_hash,reviewer_actor_id,
           review_type,recommendation,summary,created_at,content_hash,hash_scheme)
          VALUES (:id,:project_id,:manuscript_version_id,:claim_version_id,:scientific_conclusion_version_id,:novelty_assessment_id,:material_version,
           :target_content_hash,
           :reviewer_actor_id,:review_type,:recommendation,:summary,:created_at,
           :content_hash,:hash_scheme)"""),
            values,
        )

    def insert_issue(self, values: dict[str, object]) -> None:
        self._session.execute(
            text("""INSERT INTO review_issues
          (id,review_record_id,severity,issue_type,target_locator,description,
           related_claim_version_id,related_source_version_id,related_run_id,
           status,created_at,ordinal)
          VALUES (:id,:review_record_id,:severity,:issue_type,NULL,:description,
            NULL,NULL,NULL,'OPEN',GREATEST(:created_at,
              (SELECT created_at FROM internal_review_records WHERE id=:review_record_id)),:ordinal)"""),
            values,
        )

    def prepare_write(self) -> None:
        # Application UoWs configure isolation before their first statement.
        # Preserve the legacy direct-repository entry point on a fresh Session.
        if not self._session.in_transaction():
            self._session.connection(execution_options={"isolation_level": "READ COMMITTED"})
        self._session.execute(text(B05_SHARE_SQL))
        self._session.execute(text("SET LOCAL lock_timeout='10s'"))
        self._session.execute(text("SET LOCAL statement_timeout='30s'"))
        self._write_prepared = True

    def prepare_read(self) -> None:
        self._session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))

    def lock_manuscript(self, identity: UUID) -> None:
        self._session.execute(
            text("SELECT id FROM manuscript_versions WHERE id=:id FOR UPDATE"), {"id": identity}
        )

    def lock_publication(self, identity: UUID, project: UUID) -> None:
        self._session.execute(
            text("""SELECT p.id FROM publications p JOIN manuscript_versions m ON m.publication_id=p.id
            WHERE m.id=:id AND p.project_id=:project FOR SHARE OF p"""),
            {"id": identity, "project": project},
        )

    def manuscript_target(self, identity: UUID, project: UUID) -> dict | None:
        row = (
            self._session.execute(
                text("""SELECT m.* FROM manuscript_versions m
            JOIN publications p ON p.id=m.publication_id WHERE m.id=:id AND p.project_id=:project"""),
                {"id": identity, "project": project},
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row else None

    def manuscript_reviews(self, identity: UUID, project: UUID) -> list[dict]:
        return [
            dict(row)
            for row in self._session.execute(
                text("""SELECT * FROM internal_review_records
            WHERE manuscript_version_id=:id AND project_id=:project ORDER BY id FOR SHARE"""),
                {"id": identity, "project": project},
            ).mappings()
        ]

    def manuscript_reviews_snapshot(self, identity: UUID, project: UUID) -> list[dict]:
        return [
            dict(row)
            for row in self._session.execute(
                text(
                    "SELECT * FROM internal_review_records WHERE manuscript_version_id=:id "
                    "AND project_id=:project ORDER BY id"
                ),
                {"id": identity, "project": project},
            ).mappings()
        ]

    def issue_events(self, identity: UUID) -> list[dict]:
        return [
            dict(row)
            for row in self._session.execute(
                text("""SELECT e.* FROM review_issue_events e
            JOIN review_issues i ON i.id=e.issue_id WHERE i.review_record_id=:id ORDER BY i.ordinal,i.id,e.id"""),
                {"id": identity},
            ).mappings()
        ]

    def scoped_reviews(
        self,
        project: UUID,
        manuscript: UUID,
        claims: tuple[UUID, ...],
        conclusions: tuple[UUID, ...],
    ) -> list[dict]:
        return [
            dict(row)
            for row in self._session.execute(
                text("""
            SELECT r.* FROM internal_review_records r
            LEFT JOIN manuscript_versions m ON m.id=r.manuscript_version_id
            LEFT JOIN publications p ON p.id=m.publication_id
            LEFT JOIN claim_versions cv ON cv.id=r.claim_version_id
            LEFT JOIN claims c ON c.id=cv.claim_id
            LEFT JOIN scientific_conclusion_versions sv ON sv.id=r.scientific_conclusion_version_id
            LEFT JOIN scientific_conclusions sc ON sc.id=sv.scientific_conclusion_id
            WHERE r.project_id=:project AND (
                (r.manuscript_version_id=:manuscript AND p.project_id=:project) OR
                (r.claim_version_id=ANY(CAST(:claims AS uuid[])) AND c.project_id=:project) OR
                (r.scientific_conclusion_version_id=ANY(CAST(:conclusions AS uuid[])) AND sc.project_id=:project))
            ORDER BY r.id LIMIT 10001
        """),
                {
                    "project": project,
                    "manuscript": manuscript,
                    "claims": list(claims),
                    "conclusions": list(conclusions),
                },
            ).mappings()
        ]

    def audit_issues(self, identity: UUID) -> list[dict]:
        return [
            dict(row)
            for row in self._session.execute(
                text("""
            SELECT * FROM review_issues WHERE review_record_id=:id
            ORDER BY ordinal,id LIMIT 10001
        """),
                {"id": identity},
            ).mappings()
        ]

    def audit_issue_events(self, identity: UUID) -> list[dict]:
        return [
            dict(row)
            for row in self._session.execute(
                text("""
            SELECT e.* FROM review_issue_events e JOIN review_issues i ON i.id=e.issue_id
            WHERE i.review_record_id=:id ORDER BY i.ordinal,i.id,e.id LIMIT 10001
        """),
                {"id": identity},
            ).mappings()
        ]

    def material_authors(self, identity: UUID) -> frozenset[UUID]:
        return SqlAlchemyDecisionRepository(self._session).material_authors(
            identity, manuscript=True
        )

    def review_creation_authorized(self, row: dict) -> bool:
        return SqlAlchemyDecisionRepository(self._session).review_creation_authorized(row)

    def force_constraints(self) -> None:
        self._session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

    def require_write_prepared(self) -> None:
        if not self._write_prepared:
            raise ResearchBaseError(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "SHARE-first write UoW required"
            )

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
            AND a.created_at<=clock_timestamp() AND m.started_at<=clock_timestamp()
            AND (SELECT e.new_status FROM project_membership_events e
                 WHERE e.membership_id=m.id AND e.occurred_at<=clock_timestamp()
                 ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
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

    def prepare_disposition(self, identity: UUID) -> None:
        from researchbase.persistence.revision_action_repository import REVISION_SNAPSHOT_TABLES

        # M1 §12.2: B09 minus the two issue tables written by disposition.
        self._session.execute(
            text("LOCK TABLE " + ",".join(REVISION_SNAPSHOT_TABLES) + " IN SHARE MODE")
        )
        self._session.execute(text("SET LOCAL lock_timeout='10s'"))
        self._session.execute(text("SET LOCAL statement_timeout='30s'"))
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"b08:disposition:{identity}"},
        )

    def issue(self, identity: UUID, project: UUID) -> dict | None:
        row = (
            self._session.execute(
                text("""SELECT i.*,r.project_id,r.claim_version_id,
            r.scientific_conclusion_version_id,r.manuscript_version_id,r.target_content_hash,
            r.reviewer_actor_id FROM review_issues i JOIN internal_review_records r
            ON r.id=i.review_record_id WHERE i.id=:id AND r.project_id=:project"""),
                {"id": identity, "project": project},
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row else None

    def disposition_event(self, identity: UUID) -> dict | None:
        row = (
            self._session.execute(
                text("""SELECT e.*,r.project_id FROM review_issue_events e
            JOIN review_issues i ON i.id=e.issue_id JOIN internal_review_records r
            ON r.id=i.review_record_id WHERE e.id=:id"""),
                {"id": identity},
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row else None

    def lock_disposition_issues(
        self, primary: UUID, reviews: tuple[UUID, ...], selected: UUID
    ) -> None:
        for identity in sorted(set(reviews), key=str):
            self._session.execute(
                text("SELECT id FROM internal_review_records WHERE id=:id FOR SHARE"),
                {"id": identity},
            )
        identities = {primary, *(row["id"] for row in self.issues(selected))}
        for identity in sorted(identities, key=str):
            mode = "UPDATE" if identity == primary else "SHARE"
            self._session.execute(
                text("SELECT id FROM review_issues WHERE id=:id FOR " + mode), {"id": identity}
            )

    def insert_disposition(self, values: dict) -> None:
        self._session.execute(
            text("""INSERT INTO review_issue_events
            (id,issue_id,actor_id,prior_status,new_status,revision_action_id,re_review_record_id,decision_id,rationale,occurred_at)
            VALUES (:id,:review_issue_id,:actor_id,'OPEN',:disposition,:revision_action_id,:re_review_record_id,:decision_id,:rationale,clock_timestamp())"""),
            values,
        )

    def validate_issue_history(self, identity: UUID) -> None:
        # Historical SQL functions contain only snapshot reads, including nested closure checks.
        self._session.execute(text("SELECT b08_check_history(:id)"), {"id": identity})

    def entry_review_independent(self, row: dict) -> bool:
        if row.get("manuscript_version_id") is not None:
            return row["reviewer_actor_id"] not in self.material_authors(
                row["manuscript_version_id"]
            )
        return bool(
            self._session.execute(
                text("""SELECT NOT EXISTS(
          SELECT 1 FROM claim_versions WHERE id=:claim AND created_by=:actor
          UNION ALL SELECT 1 FROM scientific_conclusion_versions WHERE id=:conclusion AND created_by=:actor
          UNION ALL SELECT 1 FROM artifact_versions WHERE id=:artifact AND created_by=:actor)"""),
                {
                    "claim": row["claim_version_id"],
                    "conclusion": row["scientific_conclusion_version_id"],
                    "artifact": row["artifact_version_id"],
                    "actor": row["reviewer_actor_id"],
                },
            ).scalar_one()
        )
