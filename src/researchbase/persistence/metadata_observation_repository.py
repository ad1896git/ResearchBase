"""Narrow PostgreSQL adapter for the M2 dependent relations."""

from __future__ import annotations

from sqlalchemy import text


class SqlAlchemyMetadataObservationRepository:
    def __init__(self, session):
        self._session = session

    def result(self, result_id, project_id):
        row = (
            self._session.execute(
                text("""SELECT r.*, e.id AS execution_id,
          e.search_plan_version_id FROM search_result_records r
          JOIN search_query_records q ON q.id=r.search_query_record_id
          JOIN literature_search_executions e ON e.id=q.literature_search_execution_id
          WHERE r.id=:id AND e.project_id=:project"""),
                {"id": result_id, "project": project_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def prior(self, principal, project_id, invocation_id):
        row = (
            self._session.execute(
                text("""SELECT * FROM metadata_observations
          WHERE deployment_id=:deployment AND project_id=:project
          AND observed_by=:actor AND invocation_id=:invocation"""),
                {
                    "deployment": principal.deployment_id,
                    "project": project_id,
                    "actor": principal.actor_id,
                    "invocation": invocation_id,
                },
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def get(self, observation_id, project_id):
        row = (
            self._session.execute(
                text("""SELECT * FROM metadata_observations
                    WHERE id=:id AND project_id=:project"""),
                {"id": observation_id, "project": project_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def list_for_result(self, result_id):
        return [
            dict(row)
            for row in self._session.execute(
                text(
                    "SELECT * FROM metadata_observations WHERE result_id=:id "
                    "ORDER BY observed_at,id"
                ),
                {"id": result_id},
            ).mappings()
        ]

    def insert(self, values):
        self._session.flush()
        columns = tuple(values)
        # Internal Application-generated closed schema; no caller-controlled identifiers.
        allowed = {
            "id",
            "project_id",
            "result_id",
            "deployment_id",
            "invocation_id",
            "request_fingerprint",
            "provider_id",
            "provider_version",
            "adapter_version",
            "endpoint",
            "request_started_at",
            "observed_at",
            "observed_by",
            "outcome",
            "failure_code",
            "http_status",
            "artifact_version_id",
            "source_id",
            "source_version_id",
            "content_hash",
            "hash_scheme",
        }
        if set(columns) != allowed:
            raise ValueError("invalid observation columns")
        self._session.execute(
            text(
                "INSERT INTO metadata_observations ("
                + ",".join(columns)
                + ") VALUES ("
                + ",".join(":" + c for c in columns)
                + ")"
            ),
            values,
        )

    def resolution(self, result_id, source_id, version_id):
        row = (
            self._session.execute(
                text(
                    """SELECT * FROM search_result_resolutions
                    WHERE search_result_record_id=:result AND source_id=:source
                    AND source_version_id IS NOT DISTINCT FROM :version"""
                ),
                {"result": result_id, "source": source_id, "version": version_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def resolutions(self, result_id):
        return [
            dict(row)
            for row in self._session.execute(
                text(
                    """SELECT * FROM search_result_resolutions
                    WHERE search_result_record_id=:id ORDER BY resolved_at,id"""
                ),
                {"id": result_id},
            ).mappings()
        ]

    def insert_resolution(self, values):
        self._session.execute(
            text("""INSERT INTO search_result_resolutions
          (id,search_result_record_id,source_id,source_version_id,resolved_by,
          resolved_at,basis,content_hash,hash_scheme)
          VALUES (:id,:search_result_record_id,:source_id,:source_version_id,
          :resolved_by,:resolved_at,:basis,:content_hash,:hash_scheme)"""),
            values,
        )
