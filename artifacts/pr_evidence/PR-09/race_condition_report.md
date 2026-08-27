# Race-condition report

Real PostgreSQL tests used independent sessions and concurrent futures. Concurrent starts produced exactly one success and one `CONCURRENT_MODIFICATION`; concurrent finishes produced exactly one success and one stale-writer error. The Run row lock serializes attach-vs-start decisions, and the sealing trigger rejects any post-seal edge mutation.

