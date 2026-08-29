# Atomicity report

The existing PR-11 atomicity test continued to observe real SQLAlchemy
`INSERT INTO statistical_results` and real
`INSERT INTO statistical_result_inputs` statements before late failure. The
same transaction saw the parent and all input edges; a fresh UoW saw zero
parents and zero edges after rollback; retry persisted exactly one parent and
the exact input identity set.

The deferred zero-input guard was exercised on both the failed parent-only
repository transaction and the normal parent-plus-input Application
transaction, proving the guard is transaction-safe.
