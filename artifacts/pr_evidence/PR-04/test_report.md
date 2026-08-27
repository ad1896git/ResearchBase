# PR-04 Test Report

Final post-commit verification:

- full pytest: PASS, 141 passed;
- integration pytest: PASS, 24 passed, 117 deselected;
- PR-04 application tests: PASS, including create/freeze/revise/history, same-project link validation, stale DRAFT update, independent-UoW pointer races for both domains, and atomic rollback;
- PR-04 schema test: PASS against PostgreSQL;
- reusable PR-03 version contract: PASS for ResearchQuestionVersion and HypothesisVersion;
- architecture tests: included in the full 141-test pass;
- Ruff: PASS;
- Pyright: PASS.
