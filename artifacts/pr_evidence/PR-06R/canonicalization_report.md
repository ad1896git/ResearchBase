# Canonicalization report

`test_application_key_order_equivalence_is_idempotent` calls the real Application twice with semantically identical `selection_definition` objects whose insertion/key order differs. Both calls produce the same `content_hash` and snapshot ID; a fresh database read reports one physical row. A different locator on the retry does not mutate the stored snapshot.

This closes PR06-REV-006 while preserving `canonical-json-v1` behavior.
