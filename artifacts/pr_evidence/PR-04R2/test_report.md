# PR-04R2 Test Report

Fresh verification recorded 147 passing tests, including 30 real-PostgreSQL integration tests and 27 architecture tests. The six targeted PR-04R2 atomicity and overlap tests also passed.

The targeted cases cover:

- ResearchQuestion create rollback with direct generated identity/version row checks;
- Hypothesis create rollback with direct generated identity/version row checks;
- ResearchQuestion freeze rollback with exact six-field pre/post comparison;
- Hypothesis freeze rollback with exact six-field pre/post comparison;
- deterministic overlapping ResearchQuestion revisions;
- deterministic overlapping Hypothesis revisions.

The reusable PR-03 version contract tests passed without modification. No raw expected database error escaped the application paths.
