# PR-12 architecture decisions

The implementation follows the existing Caller -> Application -> Repository Port/UoW -> SQLAlchemy -> PostgreSQL path. Domain objects are immutable dataclasses and do not import SQLAlchemy, FastAPI, Typer, or persistence adapters. The Claim repository exposes only Claim/ClaimVersion/evidence operations and does not commit.

The frozen specification does not impose a minimum EvidenceRelation cardinality. An evidence-free ClaimVersion therefore remains a valid deterministic boundary: its support-set hash is the hash of an empty canonical list. No deferred minimum-evidence trigger or invented freeze requirement was added.

Evidence sources remain explicit typed foreign keys. No generic Version ORM, polymorphic evidence repository, soft provenance reference, scientific cascade, or PR-13/later schema was introduced.
