# Concurrency Report

This report retains the historical PR-17 summary. The corrected PR-17R proof is recorded in
`artifacts/pr_evidence/PR-17R/claim_concurrency_report.md`.

Real independent PostgreSQL UoWs/connections are used through the shared session factory.

The acceptance covers concurrent version revise, concurrent freeze, concurrent Run transition, Claim
evidence-link versus freeze, and concurrent AuditFinding row-version transition. Each race has one successful
winner and one handled ResearchBase loser (`CONCURRENT_MODIFICATION` or the frozen-state error where the domain
contract requires it). Historical version count, final frozen state, final Run state, and final finding row
version prove no partial overwrite.

PR-17R now proves the Claim evidence-link versus freeze interleaving with independent backend PIDs, explicit
lock-boundary events, an accepted freeze winner, a stable `CONCURRENT_MODIFICATION` loser, and an unchanged final
evidence set. The representative revise, freeze, Run transition, and AuditFinding row-version races also pass.
