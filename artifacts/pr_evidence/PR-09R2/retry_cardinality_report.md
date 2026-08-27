# Retry cardinality report

Rollback/retry cardinality is asserted from fresh PostgreSQL reads:

- failed `create_run` leaves no visible Run; the retry is counted by its exact id and equals `1`;
- failed dataset attach leaves no edge and the retry leaves exactly `1` dataset edge;
- failed artifact attach leaves no edge and the retry leaves exactly `1` artifact edge.

The edge retries also compare the complete Run pre-state after the injected
rollback, including timestamps, status, outcome fields, row version, and both
input sets. No `flush(); observed_insert=True` flag is used as proof.
