# Git commit resolution

The following values were resolved directly with `git rev-parse` from the
ResearchBase repository during PR-10R2:

| Reference | Resolved SHA | Semantic role |
|---|---|---|
| `41a8863` | `41a886344f277e84c7d63891c5b4351262329e30` | PR-10 reviewed implementation baseline |
| `35efe3d` | `35efe3dcc5970d0668c75863ce0dbea20560a480` | PR-10R remediation commit 1 |
| `9c5a87a` | `9c5a87a4567f4fb1c09b4dcd1d3c337f3d827e7d` | PR-10R remediation commit 2 / reviewed implementation head |
| `7db0696` | `7db0696f4e687fe07c2f603ab37a24f620fd1281` | PR-10R evidence payload commit |
| `bffb95c` | `bffb95c3dc239219ec4c288eaa3c9991f7733f6c` | PR-10R final/current reviewed HEAD |

The `7db0696` result is the Git-resolved value used to correct the PR-10R
fingerprint. The `bffb95c` result is the value used for PR-10R
`current_head_at_review`.
