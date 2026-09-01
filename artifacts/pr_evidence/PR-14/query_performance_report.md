# Query performance report

Downstream traversal uses fixed typed stage queries and no repository call inside path traversal loops. A fresh evidence probe recorded 6 `SELECT`s for a 4-target chain and 6 `SELECT`s for a 28-target graph after adding 12 Runs and 12 Measurements. Impact-target resolution recorded 4 `SELECT`s for one target and 4 for 16 targets; both cases used exactly one `FROM runs` batch read. No persistent graph/impact cache exists.
