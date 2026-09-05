# Projection Integrity Report

`tests/e2e/support.py` now records actual command outputs from the Application, HTTP JSON, and CLI JSON paths.
Fresh accepted Application reads supply only query material unavailable from the command response. The projection
observes research statuses, Run status and exact dataset/artifact input IDs, Measurement IDs/count, ordered
StatisticalResult input roles, ClaimVersion status, exact EvidenceRelation rows and semantics, support-set/content
hashes, provenance IDs, trace paths, closure, and governance target/result/validity/correction data.

`normalized_projection()` performs real structural normalization. It strips transport metadata and generated IDs
only where they are explicitly mapped to semantic roles; it preserves semantic statuses, inputs, evidence,
paths, hashes, and governance values. Expected values are asserted separately in the golden test.

The anti-cheat test mutates an observed status, exact input ID, and trace path and requires each projection to
change. The corrected GSAS selection passed with three independent projections and the equality assertions
Application == HTTP == CLI.
