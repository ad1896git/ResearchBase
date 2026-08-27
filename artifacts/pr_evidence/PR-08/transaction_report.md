# Transaction report

Application commands use one UnitOfWork transaction. The PostgreSQL integration suite verifies create rollback with a failure after flush, and fresh-UoW state after the rollback; lifecycle writes are issued before the single commit and are covered by the same transaction pattern.
