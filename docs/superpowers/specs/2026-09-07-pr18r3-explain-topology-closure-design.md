# PR-18R3 EXPLAIN Topology Closure Design

## Goal

Close the PR-18R2 P1 in `scripts/pr18_evidence.py`: the frozen query-contract validator must fail closed for unauthorized relations, Cartesian/disconnected joins, wrong join edges, and insufficient topology evidence while preserving the real production SQL capture path.

## Scope and invariants

- Audited production paths remain `get_run_provenance`, `trace_claim_to_runs`, `downstream_impact`, and `list_audit_findings`.
- The frozen manifest, not an observed plan, defines required and allowed relations, predicates, join edges, single-relation allowances, and read-only/lock constraints.
- The three staged-read paths have closed allowed relation sets equal to their required sets, no authorized joins, and one relation per captured SELECT.
- `downstream_impact` has a closed allowed relation set and explicit logical join edges for each production JOIN family. Planner order is not part of the contract.
- Positive evidence continues to call the real application query services, capture SQL through SQLAlchemy, and run PostgreSQL EXPLAIN against that SQL.
- No production semantic code, migration, dependency, PR-19, Phase 2, Agent runtime, DecisionRecord, Approval, or unrelated refactor is in scope.

## Validator design

`validate_query_contract` will compute an independent projection before deciding readiness:

1. Validate every captured statement shape and extract observed relations from both the plan relation list and SQL relation clauses; absence or disagreement is `NOT_VERIFIED`/an exception, never PASS.
2. Compute `missing_relations = required - observed` and `unexpected_relations = observed - allowed`; enforce the latter when the contract declares a closed relation set.
3. Evaluate required predicates independently from relation checks and retain separate verdict data.
4. For each statement, parse JOIN clauses into normalized relation-pair/predicate edges. `ON true`, `CROSS JOIN`, missing join predicates, disconnected components, or an edge not present in the frozen graph are topology failures unless explicitly allowed.
5. Require each frozen join edge for multi-relation paths to be observed at least once, without requiring a planner join order.
6. Enforce single-relation modes as closed one-relation reads with no join edges and reject unexpected expansion.
7. Enforce SELECT-only and no-write/no-lock constraints independently.

The returned projection records expected and observed relations, missing/unexpected relations, predicate verdicts, expected/observed join graph, Cartesian verdict, lock/write verdict, and overall verification data. It will never hard-code observed PASS values.

## Test design

The unit suite will use synthetic/mutated captured statements only for validator tests. It will include isolated missing relation and predicate cases, plus:

- an extra relation with all required relations and predicates intact;
- a Cartesian `JOIN ... ON true` with all required relations/predicates intact;
- a wrong relation edge with the same relation set and valid predicates;
- a legal topology control built from the frozen production contract;
- missing/ambiguous topology metadata that fails closed.

The existing wrong-topology test will be rewritten so it reaches topology validation rather than failing on required relations or predicates.

## Verification and chronology

Implementation and tests will be frozen at a non-self-referential subject HEAD. The authoritative generator will then run from a clean disposable checkout, and evidence will be committed separately. The final report will distinguish implementation subject and evidence HEAD and will explicitly keep self-approval, final Phase 1 review, and Phase 2 authorization at NO.
