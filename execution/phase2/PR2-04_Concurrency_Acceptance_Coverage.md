# PR2-04 concurrency acceptance coverage

No product, migration, policy or dependency changes. This group adds 940 test cases and rebinds 37 existing exact/changed outcome-reapplication cases without changing their assertions. FULL describes authored and bound dimensions, never a passing runtime result.

## Cancellation and recovery races

50 cases cover same-key C1 admission with winner commit/rollback, expired RESERVED recovery/recovery, saved original outcome/recovery, and C1/TX C. Each ordering has five repetitions. Independent transactions, backend PIDs, XIDs, observed lock blockers, commit barriers, SQLSTATEs, receipts, events, complete durable snapshots and provider counts establish causality. Existing first-reservation races remain bound. Exact sealed-response replay assertions are additionally bound to CONC-03.

## Direct SQL child serialization

20 cases cover query/result append versus terminalization in both orderings, five times. The barrier confirms the losing backend waits for the winner's execution lock. The added query-first cases reveal a real inverse-seal-link defect: an extra query can commit for an already sealed attempt. Their expected P17D5 and no-append assertions remain intact. `PR2-04_Query_Inverse_Seal_Defect.json` records the exploratory reproduction; the committed candidate checkpoint must provide fresh binding and traces. DB-04 can therefore be FULL with FAIL. No repair is authorized here.

## Fresh authorization after waits

240 cases cover receipt/execution/role waits in the required command, outcome, finalization, recovery, allocation and read phases. A further 630 cases cover project waits, initial owner preparation, CREATE receipt/role waits, joined plan identity/version locks, and actor/membership/binding locks. Each actual phase/lock pair has role and credential expiry, repeated five times. Existing ten CREATE/project temporal races remain bound. Immutable closure reads are not represented as locks they do not acquire.

The worker's first mutating attempt genuinely authorizes, then receives injected SQLSTATE40001 before its effect. Its fresh retry begins before expiry and blocks on the exact independently held row. The controller releases only after PostgreSQL time crosses the finite deadline. The assertions require FORBIDDEN after the wait, no denied-phase effects or provider calls, closed transactions, and exact fresh authorization/retry observations. Read phases use their actual single-attempt behavior.

The exploratory credential recorder initially attributed a controller-thread positive check to the waiting worker. Thread-local attribution fixes that instrumentation error; all original assertion ASTs are preserved. The original interrupted log/XML and two-thread reproducer remain historical diagnostic evidence. The exact failing credential node passed after correction. No product behavior or denial assertion was changed.

## Evidence disposition

Exploratory races: 65 passed, five query-first failures; separate complete child-race reproduction: 15 passed, same five failures. The corrected 870-case temporal exploratory run continues separately; no unexecuted repetition is claimed PASS. Every candidate requirement result is generated from the subsequent full current-candidate execution and factual traces, not this authoring summary. The external host checkout prerequisite failure is documented separately and is not a product defect. Closure Review and PR2-05 remain unstarted.
