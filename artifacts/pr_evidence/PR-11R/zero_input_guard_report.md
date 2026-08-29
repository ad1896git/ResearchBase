# Zero-input guard report

Migration `0012_statistical_result_input_guard` adds the PostgreSQL function
`enforce_statistical_result_has_input()` and the
`statistical_result_requires_input` `CONSTRAINT TRIGGER` on
`statistical_results`. It is `AFTER INSERT DEFERRABLE INITIALLY DEFERRED`, so
the legitimate transaction sequence parent INSERT → input INSERT(s) → COMMIT
remains valid while a parent-only transaction fails at commit.

Observed in real PostgreSQL:

- direct repository/UoW parent-only commit: rejected;
- raw SQL parent-only transaction: rejected;
- normal Application one-input creation: passed;
- normal Application multi-input creation: passed;
- fresh project query after each rejected commit: zero StatisticalResults.

The original `0011_statistical_result` migration was not modified.
