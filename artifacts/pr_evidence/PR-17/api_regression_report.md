# HTTP/API Regression Report

The full PostgreSQL pytest run and explicit PR-09..16 baseline bundle passed. PR-15 HTTP tests remain unchanged
and verify the frozen 35-route surface, operation IDs, request identity behavior, error envelopes, read-only
queries, and OpenAPI contract.

No HTTP route or OpenAPI source file is changed by the PR-17 subject. Architecture tests therefore prove new
HTTP business routes: 0.
