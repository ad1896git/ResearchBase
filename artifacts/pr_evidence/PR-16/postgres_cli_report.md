# PostgreSQL CLI Report

The real-stack PR-16 integration suite used PostgreSQL 18 through the repository's synchronous SQLAlchemy UoW
composition. SQLite was not used.

The passing chain covered:

`project create` → versioned experiment-spec create/freeze → run create/start/finish → measurement → statistical
result → claim/evidence/freeze → audit finding → impact assessment.

Fresh Application reads verified persisted project, run status, measurement structured value, statistical result,
and frozen claim state. Query invocations then verified provenance, trace, and impact semantics.
