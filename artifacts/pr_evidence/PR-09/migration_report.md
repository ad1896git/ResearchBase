# Migration report

- Persistent database: `0008_run_core (head)`.
- PostgreSQL: 18.6 on aarch64 Alpine.
- Disposable empty database: upgrade through `0008_run_core` passed.
- Disposable roundtrip `0008 -> 0007 -> 0008`: passed; final revision `0008_run_core (head)`.
- The disposable database was removed after the roundtrip. The persistent database was never downgraded.

