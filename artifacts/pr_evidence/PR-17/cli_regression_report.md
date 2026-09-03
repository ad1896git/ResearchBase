# CLI Regression Report

The full pytest run and explicit PR-09..PR-16 baseline bundle passed. Existing PR-16 tests cover the frozen 14
groups and 35 commands, command-handler map, root/group/command help, JSON/human output, transport attack matrix,
ExecutionContext forwarding, request-ID isolation, error exits, PostgreSQL CLI writes/reads, query purity, and
recovery.

The PR-17 subject adds no production CLI command and has zero HTTP loopback, ORM, Session, commit, or shell
business orchestration imports.
