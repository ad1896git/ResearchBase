# PR2-04 commit and context-exit acceptance coverage

Product remains exactly frozen at25b6994d218f221aa5b2c38e03af768d9d9b8de0. This group adds52 real-PostgreSQL test cases through test-owned service/UoW/Session seams. No production hooks are introduced.

The original20 cases cover lost reservation acknowledgement without dispatch, lost TX B acknowledgement with exact/changed sealed tuple reapplication, TX B rollback once/exhaustion, and TX C/C2 rollback/ambiguous acknowledgement. The additional32 cover post-commit role/credential loss before retry/disclosure (12), actual Session.close failures once/exhaustion (12), and execute/C1 precommit rollback once/exhaustion (8). Both40001 and40P01 are exercised. Injected SQLSTATEs are actual PostgreSQL errors, explicitly identified as test-induced; they are not claimed to be naturally occurring network loss/deadlock.

Every fault records the phase, real phase/cleanup transaction IDs, authorization reads and database times, independent durable snapshot at the boundary, rollback/commit state, resource closure, provider attempt IDs and invocation counts. Saved admission replay and legitimate earlier commits remain intact; no test claims whole-operation rollback after a committed phase. Fresh replay/recovery instances are included in accounting. Authority loss denies the original principal while a separately accepted entitled owner recovers through its own receipt scope.

Exploratory execution:52 passed, zero failures/errors/skips after correcting only the CLOSED role-event fixture subject. The original46-pass/six-failure run is retained: the database correctly rejected an event using the operator ID instead of the assignment subject ID, before fault execution. Migration0019 requires the assignee. All164 assertions, including93 original draft assertions, remain unchanged.

BOUND-03, IDEM-06, CONC-05/06, CRASH-05/07 are now fully authored and bound together with the retained existing tests. FULL is not acceptance: the final candidate must execute every bound node and validate its factual traces; preserved product failures still produce FAIL. AUTH-01 remains PARTIAL because accepted authenticated AGENT provisioning is unavailable. No fabricated identity is used.

The final immutable checkpoint, not the exploratory run or this note, supplies current candidate acceptance. No Closure Review or PR2-05 work is authorized here.
