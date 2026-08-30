# Closure reuse regression

The accepted request-local `run_reports` memo remains non-global and non-persistent.

- 3 paths / 1 Run: Claim closure 1; Run closure 1.
- 12 paths / 9 Runs: Claim closure 1; Run closure 9.
- 24 paths / 15 Runs: Claim closure 1; Run closure 15.

Increasing path count without increasing unique Runs does not increase Run closure evaluation.
