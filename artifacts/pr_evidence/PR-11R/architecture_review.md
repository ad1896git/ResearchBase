# Architecture review

The remediation diff was checked against the frozen layering rules. Domain
and Application boundaries remain free of SQLAlchemy Session leakage; the
repository remains narrow and does not commit; the duplicate translation is a
local expected-conflict mapping, not a transaction framework.

Migration `0012_statistical_result_input_guard` contains only one PostgreSQL
function and one deferred constraint trigger. It adds no table, generic
cardinality framework, generic Version ORM/table, StatisticalResultVersion,
Claim, EvidenceRelation, PR-12, Phase 2+, or SQLite implementation.

The `0011_statistical_result` migration remains byte-for-byte unchanged from
the reviewed baseline.
