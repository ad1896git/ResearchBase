# Migration report

Disposable/test PostgreSQL database: `researchbase_pr05r_20260827`.

Results: empty database `upgrade head` PASS; `0004_experiment_spec -> 0003_research_question_hypothesis -> 0004_experiment_spec` PASS; final disposable head `0004_experiment_spec (head)` PASS. The disposable database was dropped after verification. Persistent development database was not downgraded and remained `0004_experiment_spec (head)`. No new migration was introduced by PR-05R.
