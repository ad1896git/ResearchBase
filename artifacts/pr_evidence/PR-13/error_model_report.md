# Error model report

Missing Run and ClaimVersion roots raise stable `ResearchBaseError` with `NOT_FOUND`. Query DTOs do
not expose SQLAlchemy exceptions, ORM models, Session, or lazy-loader handles. A missing descendant
is represented by the reused closure report rather than being conflated with a missing root.

