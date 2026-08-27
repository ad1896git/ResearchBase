# Test report

PR-05R3 reconciles the R2 tests to one deterministic fixed baseline and one-field `dataclasses.replace` mutations. The six material-field sensitivity cases and ten excluded/context-field stability cases prove isolation before comparing hashes.

Fresh PR-05R3 totals: 193 pytest, 47 PostgreSQL integration, 27 architecture, 29 PR-05 domain tests, and 19 targeted material/hash tests.
