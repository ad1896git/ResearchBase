# Test report

No tests were modified or added by PR-14R2. The accepted PR-14R verification evidence is preserved:

- full PostgreSQL pytest: 527 passed, 2 skipped;
- PR-14 targeted PostgreSQL: 13 passed;
- architecture tests: 34 passed;
- PR-13 trace/query: 15 passed;
- PR-12 Claim/closure: 71 passed;
- PR-11 StatisticalResult: 50 passed;
- PR-10 Measurement: 39 passed;
- PR-09 Run: 32 passed.

The two full-suite skips are the explicitly gated legacy migration tests requiring a separate disposable migration database variable.
