# Command Inventory

| Group | Commands | Count |
|---|---|---:|
| project | create | 1 |
| rq | create, revise, freeze | 3 |
| hypothesis | create, revise, freeze | 3 |
| spec | create, revise, freeze | 3 |
| dataset | create, snapshot | 2 |
| artifact | create, revise, freeze | 3 |
| metric | create, revise, freeze | 3 |
| run | create, add-dataset, add-artifact, start, finish, provenance | 6 |
| measurement | create | 1 |
| stats | create | 1 |
| claim | create, revise, add-evidence, freeze, trace | 5 |
| audit | create | 1 |
| impact | assess, show | 2 |
| correction | create | 1 |
| **Total** |  | **35** |

Every command accepts the shared root context options. Every structured command accepts `--json`; complex
values accept `--json-input`/`--payload` or `--json-file` in addition to scalar options.

Missing mandatory families: none. Unauthorized commands: none. DecisionRecord/Approval and PR-17 commands:
none.
