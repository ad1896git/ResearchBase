# Real SQL atomicity regression report

The exact target SQL for `create_run`, dataset attach, artifact attach, start,
and finish is observed through SQLAlchemy execution events. For each injected
failure, a same-connection query proves the mutation was visible inside the
current transaction before the failure is raised. A new UoW then compares the
complete pre-state.

Results:

- create failure: no Run remains; exact retry cardinality is `1`;
- dataset attach failure: no edge remains and the complete Run state and both
  input sets are unchanged; exact retry edge count is `1`;
- artifact attach failure: no edge remains and the complete Run state and both
  input sets are unchanged; exact retry edge count is `1`;
- start failure: status, timestamps, row version, outcome fields, and both
  input sets are unchanged;
- finish failure: seal/start/finish timestamps, outcome fields, row version,
  and both input sets are unchanged.

The proof does not use `flush(); observed_insert=True` as an atomicity claim.
The targeted proof and full suite passed on PostgreSQL 18.6.
