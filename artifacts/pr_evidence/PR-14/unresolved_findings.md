# Unresolved findings

- P1: Repository-wide `ruff format --check .` fails on eight files inherited unchanged from the accepted PR-13 baseline. PR-14-owned format passes; those unrelated files were not rewritten under PR-14-only scope.

Gate result: BLOCKED. Open P0: 0. Open P1: 1.
