# Closure Report

This report is retained as the historical PR-17 closure record. PR-17R extends it with a real broken-descendant
case; the corrected evidence is in `artifacts/pr_evidence/PR-17R/broken_descendant_closure_report.md`.

Positive closure passed for both the original Run and ClaimVersion. The positive Claim closure traverses direct
Measurement evidence and every StatisticalResult input.

Controlled negative cases use the accepted closure validator with missing Run and ClaimVersion references. They
produce deterministic `NOT_FOUND` diagnostics, zero visited objects, exact object type, exact path, and stable
ordering across repeated evaluation. No raw persistence exception is exposed.

The full repository PR-12 closure regression also passed in the explicit PR-09..16 baseline bundle.

PR-17R additionally makes the original MetricDefinitionVersion descendant invalid in a controlled raw-database
setup. Three repeated Claim closure reads returned the same `VERSION_NOT_FROZEN` violations, exact descendant
paths, `visited_count=14`, and stable ordering, without exposing a raw persistence exception.
