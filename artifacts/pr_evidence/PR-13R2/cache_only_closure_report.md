# Cache-only closure report

| Traversal loop | Lookup source | DB-capable call in contextual branch | Missing behavior |
|---|---|---:|---|
| Claim EvidenceRelation → Measurement | `context.measurements.resolve` | NO | requested missing → `NOT_FOUND`; never requested → `PROVENANCE_CONTEXT_INCOMPLETE` |
| Claim EvidenceRelation → StatisticalResult | `context.statistical_results.resolve` | NO | same deterministic distinction |
| StatisticalResultInput → Measurement | `context.statistical_inputs` + `context.measurements` | NO | no omission from closure diagnostics |
| Measurement → Run / MetricDefinitionVersion | `context.runs` + `context.metric_versions` | NO | deterministic violation, no fallback |
| Run → ExperimentSpecVersion | `context.spec_versions` | NO | deterministic violation, no fallback |
| Run Dataset input → DatasetSnapshot | `context.dataset_inputs` + `context.dataset_snapshots` | NO | `NOT_FOUND` or context-incomplete violation |
| Run Artifact input → ArtifactVersion | `context.artifact_inputs` + `context.artifact_versions` | NO | `NOT_FOUND` or context-incomplete violation |

The legacy no-context validator entry points retain their existing repository behavior. Supplying
`ClosureEvaluationContext` makes every descendant lookup strictly cache-only.
