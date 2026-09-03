# Query Purity Report

Across Application, FastAPI, and Typer, Run provenance, Claim trace, and downstream impact are read-only. The
E2E SQL instrumentation observed only `SELECT`; no `INSERT`, `UPDATE`, or `DELETE` occurred.

HTTP serialization and Typer JSON output use the returned DTOs and add zero SELECT statements. Adapter SQL
sequences match direct Application query sequences for all three query families.
