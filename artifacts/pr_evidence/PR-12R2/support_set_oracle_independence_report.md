# Independent support-set oracle report

Oracle module: `tests/oracles/pr12_support_set_oracle.py`.

- Oracle imports observed by AST test: `collections`, `hashlib`, `json`.
- Production support helper imported by oracle: NO.
- `semantic_row` imported/called by oracle: NO.
- Production support-set material builder/sorter/wrapper imported by oracle: NO.
- Production `calculate_support_set_hash` called by test as SUT: YES.
- Semantic rows: literal dictionaries containing exactly `source_type`, `source_id`, `relation_type`, `qualification`.
- Sort: test-local source type, source ID, relation type, explicit NULL-first qualification.
- Canonicalization: test-local stdlib JSON with sorted keys and compact separators.
- Hash: test-local `hashlib.sha256`.

Vectors passed: Measurement-only, StatisticalResult-only, mixed, empty, NULL qualification, non-NULL qualification, reverse insertion order, and same-prefix ties. Single-variable changes to source type, source ID, relation type, and qualification changed both oracle and SUT hashes. Changes only to relation ID, creator, timestamp, and insertion order remained stable.

Focused unit result: 33 passed.
