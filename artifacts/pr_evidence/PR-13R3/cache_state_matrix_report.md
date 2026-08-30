# Cache-state matrix

| Object | FOUND | MISSING | NEVER_REQUESTED | Fallback |
|---|---|---|---|---|
| ExperimentSpecVersion | normal validation | stable `NOT_FOUND` | `PROVENANCE_CONTEXT_INCOMPLETE` | 0 |
| Measurement | normal validation | stable `NOT_FOUND` | `PROVENANCE_CONTEXT_INCOMPLETE` | 0 |
| MetricDefinitionVersion | normal validation | stable missing descendant result | context incomplete when unrequested | 0 |
| ArtifactVersion input | normal validation | stable `NOT_FOUND` | context incomplete when unrequested | 0 |
| StatisticalResult | normal validation | stable `NOT_FOUND` | context incomplete when unrequested | 0 |

The non-contextual validator remains repository-backed and completes on a valid Run.

