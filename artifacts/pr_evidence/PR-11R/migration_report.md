# PR-11R migration report

Migration `0012_statistical_result_input_guard` is a single narrow follow-up
from `0011_statistical_result`; it creates no table. The persistent integration
database ended at:

```text
0012_statistical_result_input_guard (head)
```

On disposable PostgreSQL database `researchbase_pr11r_disposable`:

1. clean base → head succeeded through `0012`;
2. zero-input repository and raw-SQL tests passed at the clean head;
3. `0012 → 0011` succeeded;
4. `0011 → 0012` succeeded;
5. current again reported `0012_statistical_result_input_guard (head)`.

The deferred trigger metadata query returned `tgdeferrable=true` and
`tginitdeferred=true`. The disposable database was removed after verification.
No SQLite path was used and `0011_statistical_result` was not rewritten.
