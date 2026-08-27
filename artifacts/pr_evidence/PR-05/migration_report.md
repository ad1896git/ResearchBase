# Migration report (reconciled by PR-05R)

Migration: `0004_experiment_spec`, down revision `0003_research_question_hypothesis`.

PR-05R used disposable/test PostgreSQL database `researchbase_pr05r_20260827`: empty database upgrade to head passed, then `0004→0003→0004` passed and ended at `0004_experiment_spec (head)`. The disposable database was removed. The persistent development database was never downgraded and remains at `0004_experiment_spec (head)`. The migration creates exactly the two PR-05 tables with RESTRICT foreign keys and database checks.
