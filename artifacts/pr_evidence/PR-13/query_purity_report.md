# Query purity report

SQLAlchemy execution-event observation covered `trace_run_to_inputs` and `get_run_provenance`.
Observed SQL classes: SELECT only. INSERT = 0, UPDATE = 0, DELETE = 0. A fresh SQL read before and
after showed identical Run status, row_version, and inputs_sealed_at. The service source contains no
`commit()` call and the UoW rolls back its read transaction on exit.

