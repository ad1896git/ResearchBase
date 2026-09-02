# Output Contract Report

JSON mode writes exactly one compact, sorted JSON document to stdout on success and nothing to stderr. UUIDs
are canonical strings, enum values use their stable values, timestamps are UTC ISO-8601 strings, bytes use
base64, and nested closure/trace/impact dataclass structures are retained. Human mode is deterministic,
concise `key=value` output with recursively stable key ordering.

Output serialization operates on accepted dataclasses and primitive values only. ORM reprs, lazy ORM values,
SQLAlchemy objects, and persistence diagnostics are not serializable through this boundary.
