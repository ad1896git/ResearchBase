# ruff: noqa: E501
"""SQL adapter for ADR-0023 S1; literal lock prefix precedes all Application SQL."""

from datetime import datetime

from sqlalchemy import text

from researchbase.agent_runtime.application.agent_contracts import AgentCommandResult
from researchbase.foundation.time import to_utc
from researchbase.persistence.agent_version_queries import version
from researchbase.persistence.literature_search_plan_repository import (
    SqlAlchemyLiteratureSearchPlanRepository,
)

ENROLLMENT_SQL = "LOCK TABLE actor_subject_bindings, actors, project_membership_events, project_memberships, project_role_assignments IN SHARE ROW EXCLUSIVE MODE"
VERSION_SQL = "LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, project_membership_events, project_memberships, project_role_assignments, projects IN SHARE MODE"
TABLES = frozenset(
    {
        "agent_versions",
        "agent_availability",
        "agent_command_receipts",
        "agent_availability_events",
        "actors",
        "actor_subject_bindings",
        "actor_subject_binding_events",
        "project_memberships",
        "project_membership_events",
        "project_role_assignments",
        "project_role_events",
    }
)


class SqlAlchemyAgentRepository:
    def __init__(self, session):
        self._session = session
        self._authority = SqlAlchemyLiteratureSearchPlanRepository(session, protected_reads=True)

    def many(self, sql, **params):
        return [
            {k: to_utc(v) if isinstance(v, datetime) else v for k, v in r.items()}
            for r in self._session.execute(text(sql), params).mappings()
        ]

    def one(self, sql, **params):
        rows = self.many(sql, **params)
        return rows[0] if rows else None

    def advisory(self, key):
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": key}
        )

    def lock_write(self, command):
        enrollment = command.operation == "provision_project_agent"
        self._session.execute(text(ENROLLMENT_SQL if enrollment else VERSION_SQL))
        if enrollment:
            self._session.execute(text("LOCK TABLE projects IN SHARE MODE"))
        self._session.execute(
            text("SELECT rb_phase2_lock_project(:id)"), {"id": command.project_id}
        )
        self.advisory(
            f"pr302:command:{command.project_id}:{command.caller.actor_id}:{command.command_id}"
        )
        args = command.arguments
        if enrollment:
            self.advisory(f"researchbase-deployment:{args.subject.deployment_id}")
            self.advisory(
                f"pr302:subject:{args.subject.deployment_id}:MTLS_URI:{args.subject.subject_value}"
            )
            actor = args.actor_id
        elif command.operation == "register_agent_version":
            actor = args.actor_id
        else:
            row = self.version(args.agent_version_id)
            actor = row["actor_id"] if row else None
        if actor is not None:
            self.advisory(f"pr302:actor:{actor}")
        if not enrollment:
            self.advisory(f"pr302:version:{args.agent_version_id}")
        identities = {command.caller.actor_id, actor}
        if enrollment:
            identities.add(args.attestation.operator.actor_id)
        for identity in sorted((i for i in identities if i is not None), key=str):
            self.many("SELECT id FROM actors WHERE id=:id FOR UPDATE", id=identity)
        if command.operation == "change_agent_availability":
            self.many(
                "SELECT agent_version_id FROM agent_availability WHERE agent_version_id=:id FOR UPDATE",
                id=args.agent_version_id,
            )

    def authority(self, principal, project):
        return self._authority.authorize(principal, project)

    def at(self):
        return to_utc(self._authority.at())

    def project_active(self, project):
        return self._authority.project_active(project)

    def actor_exists(self, identity):
        return self.one("SELECT id FROM actors WHERE id=:id", id=identity) is not None

    def human(self, actor):
        return (
            self.one("SELECT id FROM actors WHERE id=:id AND actor_type='HUMAN'", id=actor)
            is not None
        )

    def receipt(self, command):
        return self.one(
            "SELECT * FROM agent_command_receipts WHERE project_id=:p AND caller_actor_id=:a AND command_id=:c",
            p=command.project_id,
            a=command.caller.actor_id,
            c=command.command_id,
        )

    def version(self, identity):
        return version(self._session, identity)

    def availability(self, identity):
        return self.one("SELECT * FROM agent_availability WHERE agent_version_id=:id", id=identity)

    def configuration(self, identity):
        return self.one(
            "SELECT av.*,a.project_id FROM artifact_versions av JOIN artifacts a ON a.id=av.artifact_id WHERE av.id=:id",
            id=identity,
        )

    def live_agent(self, actor, project):
        return (
            self.one(
                """SELECT a.id FROM actors a JOIN agent_command_receipts r ON r.result_actor_id=a.id
         JOIN actor_subject_bindings b ON b.id=r.result_binding_id
         JOIN project_memberships m ON m.actor_id=a.id AND m.project_id=r.project_id
         JOIN project_role_assignments ro ON ro.membership_id=m.id
         WHERE a.id=:a AND r.project_id=:p AND r.operation='provision_project_agent'
         AND a.actor_type='AGENT' AND a.retired_at IS NULL AND b.status='ACTIVE'
         AND b.subject_kind='MTLS_URI' AND b.proof_kind='MTLS_CHALLENGE' AND b.bound_at<=clock_timestamp()
         AND (b.revoked_at IS NULL OR b.revoked_at>clock_timestamp()) AND m.status='ACTIVE'
         AND m.started_at<=clock_timestamp() AND ro.role='RESEARCHER'
         AND ro.effective_from<=clock_timestamp() AND (ro.effective_until IS NULL OR ro.effective_until>clock_timestamp())""",
                a=actor,
                p=project,
            )
            is not None
        )

    def insert(self, table, row):
        if table not in TABLES:
            raise ValueError("unknown S1 table")
        result = self._session.execute(
            text(
                f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join(':' + k for k in row)}) RETURNING *"
            ),
            row,
        )
        return {
            k: to_utc(v) if isinstance(v, datetime) else v
            for k, v in result.mappings().one().items()
        }

    def change(self, identity, status, revision, actor, at):
        self._session.execute(
            text(
                "UPDATE agent_availability SET status=:s,revision=:r,changed_by=:a,changed_at=:t WHERE agent_version_id=:id"
            ),
            {"s": status, "r": revision, "a": actor, "t": at, "id": identity},
        )

    def force_constraints(self):
        self._session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

    @staticmethod
    def result(receipt, *, replayed):
        data = {k: v for k, v in receipt.items() if k not in {"request_hash", "hash_scheme", "id"}}
        return AgentCommandResult(receipt_id=receipt["id"], replayed=replayed, **data)
