# Repeated Run Report

The corrected GSAS was replayed on independent fresh PostgreSQL schemas. The acceptance also replayed adapter
orders `CLI -> Application -> HTTP` and `HTTP -> CLI -> Application` on independent fresh fixtures. Observed
semantic projections remained equal across Application, HTTP, and CLI; the anti-cheat test proves the projection
would change for a changed observed status, input, or path.

The combined corrected E2E and architecture selection passed `66 passed in 29.14s`.
