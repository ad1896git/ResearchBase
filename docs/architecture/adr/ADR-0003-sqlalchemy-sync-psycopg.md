# ADR-0003: SQLAlchemy 2.0 and synchronous psycopg

- Status: Accepted
- Context: The repository needs a typed persistence adapter without coupling domain code to ORM sessions.
- Decision: Use SQLAlchemy 2.0.x with the synchronous psycopg 3 driver.
- Consequences: Database I/O remains synchronous in Phase 1.
- Rejected alternatives: Django ORM, SQLModel, Active Record, and async core database I/O.
- Upstream authority: TDG-1
- Scope: Phase 1

