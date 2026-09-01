# AuditFinding report

Exact severity/status enums and the controlled lifecycle are frozen. Material fields are Python-frozen and protected by a PostgreSQL trigger. Status writes use `WHERE row_version=:expected`; the real thread/barrier test gives one winner and one `CONCURRENT_MODIFICATION` stale writer. Create rollback/retry is proven after a real flush and fresh-connection check.
