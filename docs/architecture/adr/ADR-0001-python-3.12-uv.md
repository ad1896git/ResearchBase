# ADR-0001: Python 3.12 / uv

- Status: Accepted
- Context: Phase 1 requires a reproducible Python runtime and dependency lock.
- Decision: Use Python 3.12.x with `uv`; commit `pyproject.toml` and `uv.lock`.
- Consequences: Local and CI environments use the same resolver contract.
- Rejected alternatives: Python 3.9/3.13 baseline, Poetry, Pipenv, and parallel requirements files.
- Upstream authority: TDG-1
- Scope: Phase 1

