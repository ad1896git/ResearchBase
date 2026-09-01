# FK/RESTRICT behavioral report

All eight real PostgreSQL DELETE attacks were rejected, followed by fresh reads proving preservation and no partial deletion.

| Governance record | Delete attack | Result | Fresh-read preservation | Partial deletion |
| --- | --- | --- | --- | --- |
| AuditFinding | Project DELETE | rejected | PASS | NO |
| AuditFinding | Actor DELETE | rejected | PASS | NO |
| ImpactAssessment | Project DELETE | rejected | PASS | NO |
| ImpactAssessment | AuditFinding DELETE | rejected | PASS | NO |
| ImpactAssessment | Actor DELETE | rejected | PASS | NO |
| ImpactTarget | parent ImpactAssessment DELETE | rejected | PASS | NO |
| CorrectionRecord | Project DELETE | rejected | PASS | NO |
| CorrectionRecord | Actor DELETE | rejected | PASS | NO |

Fresh reads confirmed the governance row, parent row, and child/target rows remained intact in every applicable case.
