# Test report

The final full suite passed with 356 passed. PR-10 schema/application integration
tests passed with 20 passed, including value XOR, eligibility, unit compatibility,
hash oracle, exact provenance, real SQL atomicity, direct-column immutability, FK
restriction, and database constraint checks. The focused unit/domain/contracts and architecture
tests are included in the full suite. PostgreSQL integration used PostgreSQL 18.6;
SQLite was not used for persistence or migration proof.
