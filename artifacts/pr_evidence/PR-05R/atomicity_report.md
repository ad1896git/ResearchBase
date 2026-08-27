# Atomicity report

Post-flush/pre-commit failure injection was run against real PostgreSQL. Fresh UoW/session reads prove:

- create: identity and v1 rows are absent;
- freeze: exact status, content hash, frozen_at, version row_version, current pointer, and identity row_version equal pre-state;
- revise: no child row remains, current pointer and identity row_version are unchanged, and a frozen base remains FROZEN with its original row_version/hash.

No repository performs commit, and no persistent migration downgrade was used for this proof.
