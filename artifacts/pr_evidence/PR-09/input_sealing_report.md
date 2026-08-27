# Input sealing report

Reconciled by PR-09R: the original trigger checked only `NEW.run_id` for UPDATE, so a sealed-to-unsealed retarget could bypass protection. New migration `0009_run_input_seal_fix` checks OLD and NEW rows for UPDATE and requires PLANNED plus unsealed status for INSERT/UPDATE/DELETE. Direct retarget, role, ordinal, delete, and insert attacks now fail in isolated PostgreSQL transactions, with fresh reads proving unchanged rows.
