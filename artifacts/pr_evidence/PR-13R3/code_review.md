# Code review

The production diff adds one initialization immediately before the SpecVersion context split in
`validate_run_in_uow`. Tests independently omit batched SpecVersion results, make fallback methods
raise, repeat results, assert every stable violation field, count SQL, exercise NEVER_REQUESTED,
and run the normal repository-backed validator. No unrelated refactor is present.

