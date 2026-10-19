"""B15 fixed SHARE-first write inventory and plain exact snapshot reads."""

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import text

from researchbase.persistence.authorship_repository import SqlAlchemyAuthorshipRepository

B15_SNAPSHOT_TABLES = tuple(
    sorted(
        """
actor_subject_bindings actors artifact_versions artifacts audit_findings
authorship_snapshot_authors authorship_snapshot_contributions
authorship_snapshot_corresponding_authors authorship_snapshot_equal_groups
authorship_snapshots claim_versions claims contribution_records correction_records
dataset_snapshots datasets evidence_relations experiment_spec_versions experiment_specs
impact_assessments impact_targets internal_review_records literature_evidence
literature_evidence_relations literature_evidence_review_events literature_source_project_links
literature_sources literature_support_snapshots manuscript_artifact_placements
manuscript_citation_placements manuscript_claim_placements manuscript_versions
measurements metric_definition_versions metric_definitions project_membership_events
project_memberships project_role_assignments projects publications review_issue_events
review_issues run_artifact_inputs run_dataset_inputs runs scientific_conclusion_claim_inputs
scientific_conclusion_literature_inputs scientific_conclusion_versions scientific_conclusions
source_versions statistical_result_inputs statistical_results
""".split()
    )
)
B15_SHARE_SQL = "LOCK TABLE " + ",".join(B15_SNAPSHOT_TABLES) + " IN SHARE MODE"


B16_SNAPSHOT_TABLES = tuple(
    sorted(
        """
actor_subject_bindings actors artifact_versions artifacts audit_findings
authorship_snapshot_authors authorship_snapshot_contributions
authorship_snapshot_corresponding_authors authorship_snapshot_equal_groups
authorship_snapshots claim_versions claims contribution_records correction_records
dataset_snapshots datasets evidence_relations experiment_spec_versions experiment_specs
impact_assessments impact_targets internal_review_records literature_evidence
literature_evidence_relations literature_evidence_review_events literature_source_project_links
literature_sources literature_support_snapshots manuscript_artifact_placements
manuscript_citation_placements manuscript_claim_placements manuscript_versions
measurements metric_definition_versions metric_definitions project_membership_events
project_memberships project_role_assignments projects review_issue_events
review_issues run_artifact_inputs run_dataset_inputs runs scientific_conclusion_claim_inputs
scientific_conclusion_literature_inputs scientific_conclusion_versions scientific_conclusions
source_versions statistical_result_inputs statistical_results
""".split()
    )
)
B16_SHARE_SQL = "LOCK TABLE " + ",".join(B16_SNAPSHOT_TABLES) + " IN SHARE MODE"


B17_SNAPSHOT_TABLES = tuple(
    sorted(
        """
actor_subject_bindings actors artifact_versions artifacts audit_findings
authorship_snapshot_authors authorship_snapshot_contributions
authorship_snapshot_corresponding_authors authorship_snapshot_equal_groups
authorship_snapshots claim_versions claims contribution_records correction_records
dataset_snapshots datasets evidence_relations experiment_spec_versions experiment_specs
impact_assessments impact_targets internal_review_records literature_evidence
literature_evidence_relations literature_evidence_review_events literature_source_project_links
literature_sources literature_support_snapshots manuscript_artifact_placements
manuscript_citation_placements manuscript_claim_placements manuscript_versions
measurements metric_definition_versions metric_definitions project_membership_events
project_memberships project_role_assignments projects review_issue_events
review_issues run_artifact_inputs run_dataset_inputs runs scientific_conclusion_claim_inputs
scientific_conclusion_literature_inputs scientific_conclusion_versions scientific_conclusions
source_versions statistical_result_inputs statistical_results
""".split()
    )
)
B17_SHARE_SQL = "LOCK TABLE " + ",".join(B17_SNAPSHOT_TABLES) + " IN SHARE MODE"


class SqlAlchemyPreparedSubmissionRepository(SqlAlchemyAuthorshipRepository):
    def prepare_write(self) -> None:
        self._session.autoflush = False
        self._session.connection(execution_options={"isolation_level": "READ COMMITTED"})
        self._session.execute(text(B15_SHARE_SQL))
        self._timeouts()

    def prepare_freeze_write(self) -> None:
        self._session.autoflush = False
        connection = self._session.connection(execution_options={"isolation_level": "SERIALIZABLE"})
        from researchbase.persistence.database import configure_revision_connection

        # Connection configuration occurs in driver autocommit before BEGIN.
        configure_revision_connection(connection)
        self._session.execute(text(B17_SHARE_SQL))
        self._session.execute(text("LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE"))
        self._session.execute(
            text("LOCK TABLE prepared_submission_versions IN SHARE ROW EXCLUSIVE MODE")
        )
        self._session.execute(
            text(
                "LOCK TABLE "
                "approval_decisions,approval_request_reviews,approval_requests IN "
                "SHARE MODE"
            )
        )
        self._timeouts()

    def frozen_packages(self, publication, *, lock=False):
        return self._many(
            "SELECT * FROM prepared_submission_versions WHERE publication_id=:id AND "
            "status='FROZEN' ORDER BY id" + (" FOR UPDATE" if lock else ""),
            {"id": publication},
        )

    def package_consumption(self, identity):
        return self._one(
            "SELECT * FROM approval_grant_consumptions WHERE "
            "result_prepared_submission_version_id=:id",
            {"id": identity},
        )

    def ready_consumption(self, publication):
        return self._one(
            "SELECT c.* FROM publication_lifecycle_events e JOIN "
            "approval_grant_consumptions c ON c.id=e.basis_grant_consumption_id "
            "WHERE e.publication_id=:id AND e.new_status='READY'",
            {"id": publication},
        )

    def seal(self, identity, manifest_hash, content_hash, at):
        self._session.execute(
            text(
                "UPDATE prepared_submission_versions SET "
                "status='FROZEN',row_version=row_version+1,package_manifest_hash=:manifest,"
                "content_hash=:content,frozen_at=:at WHERE id=:id"
            ),
            {"id": identity, "manifest": manifest_hash, "content": content_hash, "at": at},
        )

    def supersede(self, identity):
        self._session.execute(
            text(
                "UPDATE prepared_submission_versions SET "
                "status='SUPERSEDED',row_version=row_version+1 WHERE id=:id"
            ),
            {"id": identity},
        )

    def prepare_consent_write(self) -> None:
        self._session.autoflush = False
        self._session.connection(execution_options={"isolation_level": "READ COMMITTED"})
        self._session.execute(text(B16_SHARE_SQL))
        self._session.execute(text("LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE"))
        self._session.execute(
            text(
                "LOCK TABLE approval_decisions,approval_request_reviews,"
                "approval_requests IN SHARE MODE"
            )
        )
        self._timeouts()

    def lock_chain(self, package, actor):
        return self._many(
            "SELECT * FROM author_consents WHERE prepared_submission_version_id=:package "
            "AND actor_id=:actor ORDER BY id FOR UPDATE",
            {"package": package, "actor": actor},
        )

    def related_grants(self, package, project, *, contradiction=False):
        rows = self._many(
            """SELECT g.id FROM prepared_submission_versions p
            JOIN publications pub ON pub.id=p.publication_id
            JOIN approval_requests r ON r.manuscript_version_id=p.manuscript_version_id
              AND r.project_id=pub.project_id AND r.approval_purpose='PREPARE_SUBMISSION'
            JOIN approval_decisions d ON d.approval_request_id=r.id
            JOIN approval_grants g ON g.approval_decision_id=d.id
            WHERE p.id=:package AND pub.project_id=:project AND g.project_id=pub.project_id
              AND g.purpose='PREPARE_SUBMISSION' AND g.status='ACTIVE' AND """
            + ("EXISTS" if contradiction else "NOT EXISTS")
            + " (SELECT 1 FROM approval_grant_consumptions c WHERE c.grant_id=g.id) ORDER BY g.id",
            {"package": package, "project": project},
        )
        return tuple(r["id"] for r in rows)

    def prepare_read(self) -> None:
        self._session.autoflush = False
        self._session.connection(
            execution_options={
                "isolation_level": "REPEATABLE READ",
                "postgresql_readonly": True,
            }
        )

    def coordinate(self, key: str) -> None:
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": key}
        )

    def package(self, identity: UUID, *, lock: bool = False):
        return self._one(
            "SELECT * FROM prepared_submission_versions WHERE id=:id"
            + (" FOR UPDATE" if lock else ""),
            {"id": identity},
        )

    def consent(self, identity: UUID):
        return self._one("SELECT * FROM author_consents WHERE id=:id", {"id": identity})

    def items(self, identity: UUID):
        return self._many(
            "SELECT * FROM prepared_submission_manifest_items "
            "WHERE prepared_submission_version_id=:id "
            'ORDER BY category COLLATE "C",ordinal',
            {"id": identity},
        )

    def consents(self, identity: UUID):
        return self._many(
            "SELECT c.* FROM author_consents c "
            "LEFT JOIN prepared_submission_versions p ON p.id=c.prepared_submission_version_id "
            "LEFT JOIN authorship_snapshot_authors a ON "
            "a.authorship_snapshot_id=p.authorship_snapshot_id AND "
            "a.actor_id=c.actor_id "
            "WHERE c.prepared_submission_version_id=:id ORDER BY a.ordinal NULLS "
            "LAST,c.actor_id,c.id",
            {"id": identity},
        )

    def heads(self, package: UUID, actor: UUID):
        return self._many(
            "SELECT c.* FROM author_consents c "
            "WHERE c.prepared_submission_version_id=:package AND c.actor_id=:actor "
            "AND c.consent_scope='PREPARED_PACKAGE' AND NOT EXISTS "
            "(SELECT 1 FROM author_consents successor WHERE successor.prior_consent_id=c.id)",
            {"package": package, "actor": actor},
        )

    def events(self, identity: UUID):
        return self._many(
            "SELECT * FROM prepared_submission_events WHERE prepared_submission_version_id=:id "
            "ORDER BY CASE WHEN prior_status IS NULL THEN 0 ELSE 1 END,occurred_at,id",
            {"id": identity},
        )

    def manuscript(self, identity: UUID, *, lock: bool = False):
        return self._one(
            "SELECT * FROM manuscript_versions WHERE id=:id" + (" FOR UPDATE" if lock else ""),
            {"id": identity},
        )

    def parent(self, identity: UUID, *, lock: bool = False):
        return self._one(
            "SELECT * FROM publications WHERE id=:id" + (" FOR UPDATE" if lock else ""),
            {"id": identity},
        )

    def next_version(self, publication: UUID):
        return self._session.execute(
            text(
                "SELECT coalesce(max(version_number)::bigint,0)+1 "
                "FROM prepared_submission_versions "
                "WHERE publication_id=:id"
            ),
            {"id": publication},
        ).scalar_one()

    def target(self, table: str, identity: UUID):
        if table not in {
            "artifact_versions",
            "source_versions",
            "claim_versions",
            "scientific_conclusion_versions",
            "author_consents",
        }:
            raise ValueError("closed target table required")
        return self._one(f"SELECT * FROM {table} WHERE id=:id", {"id": identity})

    def insert_package(self, row: dict) -> None:
        self._insert("prepared_submission_versions", row)

    def insert_item(self, row: dict) -> None:
        self._insert("prepared_submission_manifest_items", row)

    def insert_consent(self, row: dict) -> None:
        self._insert("author_consents", row)

    def insert_event(self, row: dict) -> None:
        if row["new_status"] == "WITHDRAWN":
            # The guarded UPDATE creates the immutable observation atomically.
            # Verify the requested append exactly; never hide changed material.
            saved = self._one(
                "SELECT * FROM prepared_submission_events "
                "WHERE prepared_submission_version_id=:id AND new_status='WITHDRAWN'",
                {"id": row["prepared_submission_version_id"]},
            )
            if saved is None or any(
                saved[key] != value for key, value in row.items() if key != "id"
            ):
                from researchbase.foundation.errors import ErrorCode, ResearchBaseError

                raise ResearchBaseError(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                    "withdrawal event differs from observed transition",
                )
            return
        self._insert("prepared_submission_events", row)

    def withdraw(self, identity: UUID, actor: UUID, at: datetime, reason: str) -> None:
        # Transient command context binds the deferred event to this observed effect.
        self._session.execute(
            text("SELECT set_config('researchbase.b15_withdrawal', :context, true)"),
            {
                "context": json.dumps(
                    {
                        "package": str(identity),
                        "actor": str(actor),
                        "at": at.isoformat(),
                        "reason": reason,
                    }
                )
            },
        )
        self._session.execute(
            text(
                "UPDATE prepared_submission_versions SET status='WITHDRAWN',"
                "row_version=row_version+1 "
                "WHERE id=:id AND status IN ('PREPARED','FROZEN')"
            ),
            {"id": identity},
        )

    def force_constraints(self) -> None:
        self._session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
