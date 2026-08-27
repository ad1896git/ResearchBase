# Material hash report

Freeze hashes the explicit three-key material payload with `sha256_canonical_json`, yielding `sha256-cjson-v1`. Unit and aggregation sensitivity, independent expected-hash calculation, and exclusion of identity/operational metadata are covered by PR-08 unit tests and the application freeze test.
