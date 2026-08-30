# Cache membership report

`BatchLookup[T]` stores `values` and `requested_ids`; `missing_ids` is derived as the exact set
difference. `resolve()` returns `FOUND`, `MISSING`, or `NEVER_REQUESTED`.

- Requested + found: returns the typed object/list.
- Requested + missing: returns `MISSING`; accepted missing-descendant closure semantics apply.
- Never requested: returns `NEVER_REQUESTED`; validator emits stable
  `PROVENANCE_CONTEXT_INCOMPLETE` and never queries persistence.

Construction rejects any value whose key is not declared requested. Therefore `None` is not used
to choose a repository fallback.
