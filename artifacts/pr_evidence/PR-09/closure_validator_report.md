# Closure validator report

Reconciled by PR-09R: the validator contract and sort key were present in PR-09, but the original evidence lacked multiple-invalid-closure DTO coverage and repeated-order assertions. PR-09R adds those checks, including `code`, `object_type`, `object_id`, `path`, `message`, `complete`, `visited_count`, and repeated deterministic ordering. The documented sort is `(path, object_type, object_id, code)`; a complete fixture visits 4 objects.
