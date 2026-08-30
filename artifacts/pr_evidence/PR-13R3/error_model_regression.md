# Error-model regression

The targeted state tests expose no `UnboundLocalError`, `KeyError`, `AttributeError`, SQLAlchemy,
DBAPI, or psycopg exception after remediation. MISSING remains `NOT_FOUND`; NEVER_REQUESTED
remains `PROVENANCE_CONTEXT_INCOMPLETE`. Repository fallback methods are assertion-raising and
were called zero times.

