# Closure reuse report

Instrumentation of accepted validators observed 3 paths/1 Run = Claim 1, Run 1; 12 paths/9 Runs =
Claim 1, Run 9; 24 paths/15 Runs = Claim 1, Run 15. Extra paths sharing a Run do not add Run closure
calls. `ClosureEvaluationContext` is transaction/request-local memory only.
