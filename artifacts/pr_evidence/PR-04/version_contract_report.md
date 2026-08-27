# PR-04 Version Contract Report

Both concrete version types reuse the PR-03 `VersionStatus`, `require_transition`, and `freeze_material` contract. The reusable contract harness was applied independently to both adapters.

Allowed transitions are `DRAFT -> FROZEN`, `DRAFT -> ABANDONED`, and `FROZEN -> SUPERSEDED`. All other matrix transitions are rejected with `INVALID_STATE_TRANSITION`. Material edit attempts after freeze/supersede/abandon are rejected with `IMMUTABLE_RECORD`.

ResearchQuestion material payload is exactly `question_text`, `scope`, and `rationale`. Hypothesis material payload is exactly `statement`, `expected_direction`, `success_criteria`, and `rationale`. Identity, timestamps, and row versions are excluded. Hashes therefore remain deterministic for equal material and differ when material differs; the accepted `sha256-cjson-v1` scheme is bound on freeze. Frozen objects retain UTC `frozen_at` and cannot be edited in place.
