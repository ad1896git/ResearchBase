# PR-04 Implementation Summary

PR-04 implements the ResearchQuestion and Hypothesis identity/version slice on top of the accepted PR-03/PR-03R foundation.

- Concrete domain objects: `ResearchQuestion`, `ResearchQuestionVersion`, `Hypothesis`, and `HypothesisVersion`.
- Application commands: create, revise, DRAFT material update, freeze, get, and history query for both owning domains.
- Persistence: explicit SQLAlchemy models, narrow repositories, and the existing synchronous one-session UnitOfWork.
- Version behavior: parent-local numbering, immutable frozen/superseded material, current pointers, and PR-03 `VersionStatus`/`freeze_material` reuse.
- Scope guard: no generic Version ORM/table, business tables for later PRs, or PR-05 behavior.

Implementation commits are `def1361` and `4c73866`, both descendants of the accepted PR-03R evidence commit `4dfffd8`.
