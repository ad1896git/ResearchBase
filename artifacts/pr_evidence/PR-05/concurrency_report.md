# Concurrency report

Identity pointer updates and DRAFT version updates use conditional `row_version` updates and translate zero-row updates to `CONCURRENT_MODIFICATION`. Two independent PostgreSQL sessions synchronized at repository entry produce one successful revision and one deterministic concurrency failure; history remains `[1, 2]`.
