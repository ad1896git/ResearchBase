# Architecture review

PASS for PR-13-owned boundaries: no persistence/framework imports in query DTO/service, no generic
GraphNode/GraphEdge, no NetworkX, no commit, no migration 0015, no API/CLI, and no PR-14 symbols.
The only modified prior architecture test removes the obsolete PR-12 prohibition on the now-authorized
`trace_claim_to_runs`; all PR-14+ guards remain.
