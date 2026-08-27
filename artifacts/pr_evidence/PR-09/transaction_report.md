# Transaction report

The synchronous UoW owns one database transaction per application command. PR-09 tests inject a failure after flush for dataset attach, start, and finish; fresh UoWs observe no partial edge, unchanged PLANNED/seal state, and unchanged RUNNING/finish state respectively. The existing cross-repository rollback suite remains green. PostgreSQL trigger and FK failures also roll back their statements/transactions.
