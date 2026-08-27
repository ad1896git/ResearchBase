# PR-04 Test Report (updated by PR-04R)

Final post-commit verification:

- full pytest: PASS, 147 passed;
- integration pytest: PASS, 30 passed, 117 deselected;
- PR-04 application tests: PASS, including create/freeze/revise/history, same-project link validation, stale DRAFT updates for both domains, independent-UoW pointer races for both domains, cross-parent pointer attacks, concurrent revisions for both domains, and atomic rollback for both domains;
- PR-04 schema test: PASS against PostgreSQL;
- reusable PR-03 version contract: PASS for ResearchQuestionVersion and HypothesisVersion;
- architecture tests: included in the full 147-test pass;
- Ruff: PASS;
- Pyright: PASS.
