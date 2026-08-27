# Concurrency report

Identity pointer changes and DRAFT edits use row-version predicates. Identity rows are locked for revision/freeze; parent-local version numbers are allocated under that lock. A real PostgreSQL two-thread revision test produced one success and one `CONCURRENT_MODIFICATION`, with no duplicate or partial version row.
