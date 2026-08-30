# SQL scaling report

Old reviewed observations: 13, 53, and 231 SELECTs.

| fixture | evidence | stat results | measurements | runs | paths | dataset inputs | artifact inputs | SELECT | Run closure | Claim closure |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| canonical | 2 | 1 | 3 | 1 | 3 | 0 | 0 | 15 | 1 | 1 |
| scaled | 2 | 1 | 12 | 9 | 12 | 0 | 0 | 15 | 9 | 1 |
| larger | 2 | 1 | 24 | 15 | 24 | 0 | 0 | 15 | 15 | 1 |

The identical count proves stage-bounded growth and fails if per-path reads return.
