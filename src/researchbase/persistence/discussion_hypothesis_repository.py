"""B03 PostgreSQL snapshot and immutable admission relation operations."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

B03_SNAPSHOT_TABLES = (
    "actor_subject_bindings",
    "actors",
    "artifact_versions",
    "artifacts",
    "claim_versions",
    "claims",
    "discussion_session_claim_inputs",
    "discussion_session_question_inputs",
    "discussion_session_source_inputs",
    "discussion_sessions",
    "discussion_turn_claim_citations",
    "discussion_turn_source_citations",
    "discussion_turns",
    "literature_source_project_links",
    "literature_sources",
    "project_membership_events",
    "project_memberships",
    "project_role_assignments",
    "projects",
    "research_question_versions",
    "research_questions",
    "source_versions",
)
B03_SNAPSHOT_SQL = """LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts,
claim_versions, claims, discussion_session_claim_inputs, discussion_session_question_inputs,
discussion_session_source_inputs, discussion_sessions, discussion_turn_claim_citations,
discussion_turn_source_citations, discussion_turns, literature_source_project_links,
literature_sources, project_membership_events, project_memberships, project_role_assignments,
projects, research_question_versions, research_questions, source_versions IN SHARE MODE"""


class SqlAlchemyDiscussionHypothesisRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def prepare(self, *, read_only: bool) -> None:
        self._session.autoflush = False
        self._session.connection(
            execution_options={
                "isolation_level": "REPEATABLE READ" if read_only else "READ COMMITTED",
                "postgresql_readonly": read_only,
            }
        )
        if not read_only:
            self._session.execute(text(B03_SNAPSHOT_SQL))
            self._session.execute(text("SET LOCAL lock_timeout='10s'"))
            self._session.execute(text("SET LOCAL statement_timeout='30s'"))

    def lock_candidate(self, session, turn, digest) -> None:
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"b03:discussion-hypothesis:{session}:{turn}:{digest}"},
        )

    def duplicate(self, session, turn, digest) -> bool:
        return bool(
            self._session.execute(
                text("""SELECT EXISTS(SELECT 1 FROM
          discussion_hypothesis_admissions WHERE session_id=:session AND turn_id=:turn
          AND candidate_hash=:digest)"""),
                {"session": session, "turn": turn, "digest": digest},
            ).scalar_one()
        )

    def save(self, row) -> None:
        columns = tuple(row)
        self._session.execute(
            text(
                f"INSERT INTO discussion_hypothesis_admissions ({','.join(columns)}) "
                f"VALUES ({','.join(':' + column for column in columns)})"
            ),
            row,
        )

    def admission(self, project, receipt):
        row = (
            self._session.execute(
                text("""SELECT a.*,r.actor_id AS admitted_by,
          r.completed_at AS admitted_at,r.command_name,r.result_session_id,r.result_turn_id,
          r.project_id AS receipt_project,r.input_hash,v.hypothesis_id,v.version_number,
          v.created_by AS version_creator,v.created_at AS version_created_at,
          h.created_by AS hypothesis_creator,h.created_at AS hypothesis_created_at,
          h.project_id AS output_project,h.research_question_id
          FROM discussion_hypothesis_admissions a
          JOIN discussion_command_receipts r ON r.id=a.receipt_id
          JOIN hypothesis_versions v ON v.id=a.hypothesis_version_id
          JOIN hypotheses h ON h.id=v.hypothesis_id
          WHERE a.project_id=:project AND a.receipt_id=:receipt"""),
                {"project": project, "receipt": receipt},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def exact_receipt(self, project, receipt):
        row = (
            self._session.execute(
                text("""SELECT * FROM discussion_command_receipts
          WHERE project_id=:project AND id=:receipt"""),
                {"project": project, "receipt": receipt},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def force_constraints(self) -> None:
        self._session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
