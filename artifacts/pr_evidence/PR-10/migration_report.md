# Migration report

Migration chain: 0009_run_input_seal_fix -> 0010_measurement (head).

Fresh persistent database verification reached 0010_measurement (head). A separate
disposable PostgreSQL database upgraded empty through head, downgraded to
0009_run_input_seal_fix, upgraded back to head, and ended at
0010_measurement (head). The disposable database was removed after verification.

PostgreSQL version: 18.6.
