# Application / CLI Equivalence Report

The CLI contract tests assert exact command DTO and `ExecutionContext` construction through the injected
Application interface. The real PostgreSQL write chain is verified with fresh Application reads for project,
frozen experiment-spec version, completed run, measurement, statistical result, frozen claim, and governance
state.

For all three query commands, the real-stack test compares CLI JSON directly with the recursive JSON form of
the direct Application query result:

- run provenance: exact DTO structure and closure;
- claim trace: exact paths, historical references, and closure;
- downstream impact: exact target/path structure.

Representative NOT_FOUND, validation, state, and internal-error behavior is covered by the mapper and recovery
tests. No CLI-only scientific side effect or rule exists.
