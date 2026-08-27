# Sealed input trigger report

Migration `0009_run_input_seal_fix` replaces the 0008 function without rewriting accepted migration history. For INSERT it checks NEW; for DELETE it checks OLD; for UPDATE it checks both OLD and NEW. Each referenced Run must be `PLANNED` with `inputs_sealed_at IS NULL`.

Real PostgreSQL attacks all failed in isolated transactions: sealed→unsealed retarget, unsealed→sealed retarget, sealed→sealed retarget, role update, ordinal update, delete, and insert into a sealed Run. Fresh reads confirmed the original Run statuses and input rows remained unchanged.
