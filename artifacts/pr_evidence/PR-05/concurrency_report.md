# Concurrency report (reconciled by PR-05R)

Identity pointer updates and DRAFT version updates use conditional `row_version` updates and translate zero-row updates to `CONCURRENT_MODIFICATION`. Two independent PostgreSQL sessions synchronized at repository entry produce exactly one successful revision and one `ResearchBaseError(CONCURRENT_MODIFICATION)`. A fresh connection asserts exactly the v1/v2 IDs and statuses, current pointer ownership, identity row_version 3, and no extra/partial row; no expected raw IntegrityError escapes.
