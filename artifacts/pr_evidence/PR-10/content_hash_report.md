# Content hash report

The original PR-10 evidence overstated the independence of its integration oracle:
the test imported the production `sha256_canonical_json` helper. PR-10R replaces that
assertion with test-owned stdlib `json.dumps` plus `hashlib.sha256` logic and verifies
both numeric and structured records through the real Application path, including
returned and freshly persisted hashes. Differential tests now use a deterministic
shared baseline, change exactly one material field at a time, and independently vary
each excluded metadata field. Repeating identical material remains allowed and
produces the same hash with distinct Measurement IDs; no uniqueness constraint is
present.

Result after PR-10R: PASS. Scheme: sha256-cjson-v1; canonical serializer:
canonical-json-v1.
