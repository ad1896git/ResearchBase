# Query Purity Report

The three GET routes call only accepted query services. The real PostgreSQL provenance test records only `SELECT` statements. Route source contains no persistence imports, Session, flush, rollback, or commit calls.
