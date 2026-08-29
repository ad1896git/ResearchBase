# Atomicity report

The PR-11 integration test installed a SQLAlchemy `after_cursor_execute`
observer and recorded the actual SQL statements. It observed exactly one real
`INSERT INTO statistical_results` and two real
`INSERT INTO statistical_result_inputs` statements before a late injected
failure.

The failing UoW then reported same-transaction visibility `(parent=1,
inputs=2)`. A fresh UoW after rollback observed zero parents and zero inputs.
A retry persisted exactly one parent and exactly two edges with the original
Measurement IDs, roles, and ordinals. The repository never commits; the
Application Service owns the single transaction.
