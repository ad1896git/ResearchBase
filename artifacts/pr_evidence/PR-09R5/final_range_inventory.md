# Final range inventory

The required ranges were run with `git diff --name-only`,
`git diff --name-status`, and `git diff --stat`.

| Range | Files | Classification |
|---|---:|---|
| `9c47381..9e1bb85` | 31 | production 1; tests 1; migration 0; evidence 29 |
| `9e1bb85..0feba30` | 2 | production 0; tests 0; migration 0; evidence 2 |
| `0feba30..8a57413` | 1 | production 0; tests 1; migration 0; evidence 0 |
| `8a57413..044c72a` | 20 | production 0; tests 0; migration 0; evidence 20 |
| `044c72a..602f224` | 5 | production 0; tests 0; migration 0; evidence 5 |
| `0feba30..602f224` | 21 | production 0; tests 1; migration 0; evidence 20 |
| `9c47381..602f224` | 45 | production 1; tests 2; migration 0; evidence 42 |

The exact name/status blocks and command outputs are in
`changed_files.txt` and `commands_and_results.md`. The cumulative counts are
set-equal to the corresponding direct Git output.
