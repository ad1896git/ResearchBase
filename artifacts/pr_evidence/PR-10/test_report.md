# Test report

The original PR-10 suite passed with 356 passed and its 20 PR-10 schema/application
tests passed, but three proof claims were not strong enough for independent review:
the hash oracle imported production code, closure invalidity was monkeypatched, and
historical provenance was not compared as a complete row. PR-10R strengthens those
tests without changing production semantics. The post-remediation full suite remains
356 passed; PR-10 schema/application tests remain 20 passed and PR-10 domain tests
pass 17 passed. PostgreSQL integration used PostgreSQL 18.6; SQLite was not used for
persistence or migration proof.
