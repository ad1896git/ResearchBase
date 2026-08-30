# Test report

F-003 unit oracle tests: 30 passed after the remediation changes, including the literal mixed/NULL/empty vectors and semantic/excluded metadata differentials.

F-004 closure tests: 5 passed, including the new three-input later-input attack.

F-005 application/guard tests: the expanded frozen matrix and SUPERSEDED/ABANDONED representatives passed in the 66-test targeted suite.

Final full regression Run A: 483 passed, 1 warning. Final full regression Run C: 483 passed, 1 warning. The only warning is Alembic's existing `path_separator` deprecation warning emitted by the migration subprocess test.
