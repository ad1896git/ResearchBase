# PR-04 History Query Report

`ResearchQuestionRepository.list_history` and `HypothesisRepository.list_history` return all versions for one parent, ordered deterministically by `version_number`. Application methods map them to read DTOs rather than ORM objects.

History includes status, version number, material, content hash, frozen timestamp, and row version. Superseded versions remain visible; DRAFT versions remain visible; versions from another parent are excluded by the parent predicate. The integration flow verified v1 `SUPERSEDED` plus v2 `DRAFT` after a freeze/revise sequence for both domains.
