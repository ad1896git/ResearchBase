# Content hash report

The real Application path was verified against an independent test oracle using the
exact six-field material payload. Differential/domain tests cover changes to material
fields, canonical key-order equivalence, numeric-vs-structured distinction, and
metadata exclusion. Repeating identical material is allowed and produces the same
hash with distinct Measurement IDs; no uniqueness constraint is present.

Result: PASS. Scheme: sha256-cjson-v1; canonical serializer: canonical-json-v1.
