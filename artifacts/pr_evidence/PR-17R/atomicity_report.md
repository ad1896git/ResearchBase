# Atomicity Report

The corrected acceptance exercises fresh-UoW failure and exact retry for four transaction families:

| Transaction | Fresh-UoW failure | Retry |
|---|---|---|
| StatisticalResult plus input edges | no parent or input edge remains | exactly one result and its complete input set |
| Claim evidence link and freeze | no partial evidence link and no partial freeze | exact accepted final evidence/status |
| ImpactAssessment plus targets | no parent or target rows remain | exactly one assessment and exact target set |
| Run plus dataset input | no Run or input edge remains | exactly one Run and exact sealed input |

Every check re-reads through a fresh UoW. Existing lower-level transaction and concurrency checks are reported as
baseline regression where they predate PR-17R; the four rows above are the PR-17R acceptance proof.
