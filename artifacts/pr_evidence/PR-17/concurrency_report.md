# Concurrency Report

Real independent PostgreSQL UoWs/connections are used through the shared session factory.

The acceptance covers concurrent version revise, concurrent freeze, concurrent Run transition, Claim
evidence-link versus freeze, and concurrent AuditFinding row-version transition. Each race has one successful
winner and one handled ResearchBase loser (`CONCURRENT_MODIFICATION` or the frozen-state error where the domain
contract requires it). Historical version count, final frozen state, final Run state, and final finding row
version prove no partial overwrite.

Claim evidence/freeze locking and duplicate-link race semantics remain covered by the accepted PR-12 concurrency
regression, which passed in the explicit baseline bundle.
