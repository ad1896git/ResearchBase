# Migration report

Migration: `0004_experiment_spec`, down revision `0003_research_question_hypothesis`.

Verified on the local PostgreSQL service: current head, upgrade from 0003, downgrade 0004→0003, and re-upgrade 0003→0004. The migration creates exactly the two PR-05 tables and uses RESTRICT foreign keys and database checks for status, positive version number, uniqueness, and parent references.
