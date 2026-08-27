# PR-04R2 Concurrency Overlap Proof

Both revision tests use the existing application service, independent UoW sessions/connections, and the unchanged domain-specific repository locking path.

| Domain | Synchronization and overlap indicator | Outcomes and final invariants |
|---|---|---|
| ResearchQuestion | `threading.Barrier(2)` is entered by a wrapper around `SqlAlchemyResearchQuestionRepository.get_for_update()`, after each UoW has entered but before the original parent-lock call. A `Lock` protects an `entered` counter; the test requires `entered == 2` after both workers complete. | One revision commits v2; the other returns stable `CONCURRENT_MODIFICATION`. History is `[1, 2]`; direct SQL confirms version numbers `[1, 2]` and the current pointer's version belongs to the same parent. |
| Hypothesis | Equivalent `threading.Barrier(2)` wrapper around `SqlAlchemyHypothesisRepository.get_for_update()`, with the same two-worker entry assertion. | One revision commits v2; the other returns stable `CONCURRENT_MODIFICATION`. History is `[1, 2]`; direct SQL confirms version numbers `[1, 2]` and the current pointer's version belongs to the same parent. |

The barrier proves both transactions reached the controlled synchronization point before either entered the parent-lock critical section. The original `get_for_update() -> max(version_number) -> add version -> update pointer -> commit` path remains unchanged. No duplicate version number, pointer corruption, partial version row, or raw expected `IntegrityError` was observed.
