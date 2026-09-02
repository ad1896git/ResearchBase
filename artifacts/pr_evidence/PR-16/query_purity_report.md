# Query Purity Report

`run provenance`, `claim trace`, and `impact show` call only accepted query services. Real PostgreSQL SQL
instrumentation found no INSERT, UPDATE, or DELETE. CLI SQL statement sequences matched direct Application query
sequences, and the output layer added no SELECTs.

The inherited PR-13/PR-14 stage-bounded trace/impact fixtures remain green (`141` PR-09–PR-14 regression tests
passed), while the PR-16 real CLI test verifies that adapter invocation and formatting preserve the same query
boundary.
