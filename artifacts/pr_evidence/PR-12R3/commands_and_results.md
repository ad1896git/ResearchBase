# Commands and results

- Baseline `git rev-parse HEAD`: `b973356f494bb75a2f324be8455a9f54934e9f5d`.
- `git rev-parse 3564361 e95fee5 0d9f78c 16228b9 b973356`: all resolved as commits.
- `git diff --name-only 16228b9..b973356`: 3 evidence files.
- `git diff --name-status 16228b9..b973356`: 3 modified evidence files.
- `git diff --stat 16228b9..b973356`: 3 files changed, 14 insertions, 1 deletion.
- Range set equality: PASS.
- Source/test/migration files in range: 0.

Final post-edit verification is executed directly against Git and PostgreSQL after the evidence commits are created. The historical R2 HEAD values above are self-contained in this evidence.
