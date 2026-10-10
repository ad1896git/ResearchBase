# PR2-04 restart acceptance coverage

Product remains frozen at `25b6994d218f221aa5b2c38e03af768d9d9b8de0`.

The new process module contains five scenarios, each repeated five times. Each worker uses multiprocessing spawn and reconstructs its engine, UoW and service graph. The accepted persisted HUMAN principal is reauthorized through real PostgreSQL. An fsynced external fake-provider journal survives forced termination; it is never treated as canonical response evidence.

The parent observes a committed RESERVED attempt, zero checked-out connections and the exact process identity at a causal barrier. A fresh contender replays the original request and admits a new key without taking over or invoking. Fresh-process early recovery is rejected with unchanged durable rows. Lost-owner scenarios wait for the actual database recovery deadline and recover UNKNOWN without invented timestamps, queries or results. A surviving owner alone persists its saved response after current authorization; credential loss denies persistence, and a separately provisioned current writer recovers later.

CONC-02 retains its existing ten A/B lock-wait races; the process cases supply the missing reconstruction/no-takeover dimension. CRASH-04 receives paired response-loss, surviving-response and authority-loss cases. CRASH-03 also binds the existing `test_pg_replacement_writer_recovers_expired_reservation_without_unproved_response[lost_response]` node, whose unchanged assertions reject late original-response persistence after recovery and preserve rows/call count. Only its parameter marker changed.

Authoring run: 25 executed, 25 passed, zero failures/errors/skips. This is diagnostic execution, not a substitute for the subsequent committed-candidate checkpoint. Candidate-bound results, PostgreSQL observations, exact nodes and trace hashes live in each immutable candidate-checks run directory. No production or migration files changed. This document makes no closure verdict.
