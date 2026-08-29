# Concurrency report

The PostgreSQL concurrency suite passed 7 tests. Identity stale revise, DRAFT stale writers, genuine concurrent revise, link-vs-freeze in both lock orders, unlink-vs-freeze in both orders, duplicate evidence linking, and concurrent freeze were exercised with independent UoWs.

The concurrent-revise proof synchronizes after the first `SELECT ... FOR UPDATE` returns (the first transaction holds the row lock), observes the second transaction issuing the same lock SQL while blocked, then releases the first transaction. The final state contains one committed revision and one stable `CONCURRENT_MODIFICATION`; no raw DB error leaked. Link/freeze and unlink/freeze tests similarly observe real SQL lock boundaries and final evidence sets.
