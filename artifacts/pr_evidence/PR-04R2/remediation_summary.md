# PR-04R2 Remediation Summary

PR-04R2 closes PR04R-001, PR04R-002, and PR04R-003 on top of the preserved PR-04R ending HEAD `0573fa5`.

- PR04R-001: all four real-PostgreSQL rollback tests now verify direct row absence or exact field-by-field pre-state restoration through independent verification contexts.
- PR04R-002: ResearchQuestion and Hypothesis revision tests now use deterministic `threading.Barrier` synchronization immediately before the domain-specific parent lock.
- PR04R-003: stale 141-test evidence was corrected to the freshly verified 147-test total, and prior overstatements were reconciled in PR-04 and PR-04R evidence.

The remediation changes only integration tests and evidence. No production source, migration, schema, dependency, transaction framework, PR-05 domain, or Phase 2+ implementation was added.

Implementation commit: `8dd77d3`; baseline `0573fa5` remains an ancestor.
