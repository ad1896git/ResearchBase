# M1 local implementation plan

Single primary executor; approved scope M1-AUTH-002. Starting checkpoint ed0f00ddd26132ed99b61578a606f05c4453949a.

- [x] Add protected host/installation OS adapter and fail-closed credential revalidation, bootstrap proof and secret invalidation; test real process identity plus negative privilege/configuration branches.
- [x] Resolve canonical OS bindings through the Application/UoW/repository boundary. Compose bootstrap and existing literature services with the real verifier. Expose local init/bootstrap/whoami/project/workspace/question commands; deny unsafe legacy groups and actor overrides.
- [x] Enforce fresh in-transaction project authorization for the exposed Phase 1 research commands; keep existing scientific semantics and HTTP fail-closed behavior.
- [x] Exercise subprocess CLI onboarding, concurrent bootstrap, persistent restart readback and negative authorization on isolated PostgreSQL 18; run focused temporal and M0 regressions.
- [x] Review security boundary, run modified-path Ruff/formatter/Pyright and baseline diagnostic comparison, commit, update completion report, verify clean branch and milestone bundle. Stop before M2.
