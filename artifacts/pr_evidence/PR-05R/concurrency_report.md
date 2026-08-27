# Concurrency report

Two independent PostgreSQL transactions are synchronized at `get_for_update`. Exactly one revision commits and one returns `CONCURRENT_MODIFICATION`. A fresh independent connection asserts the exact two version IDs/rows (`v1 SUPERSEDED`, `v2 DRAFT`), current pointer equals v2 and belongs to the same ExperimentSpec, identity row_version is 3, and no extra/partial row exists. No raw expected IntegrityError leaks.
