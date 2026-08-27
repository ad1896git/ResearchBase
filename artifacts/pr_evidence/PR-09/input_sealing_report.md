# Input sealing report

Start locks the Run row, validates the closure, then seals and transitions the Run in the same transaction. PostgreSQL trigger `reject_sealed_run_input_mutation()` rejects insert/update/delete on both input tables after `inputs_sealed_at` is set. Application checks and the database trigger therefore protect supported and direct SQL paths.

