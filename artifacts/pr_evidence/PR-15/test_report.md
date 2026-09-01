# Test Report

Fresh full and targeted verification used PostgreSQL at `postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase`.

PR-15 targeted coverage includes exact route inventory, OpenAPI reproducibility and operation-ID uniqueness, response/error schema references, exact context forwarding, all frozen error statuses, malformed transport rejection before handler invocation, request-ID concurrency, exception recovery, real-stack equivalence, query purity, and serialization SQL count.
