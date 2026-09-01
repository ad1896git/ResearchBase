# FK/RESTRICT report

Behavioral PostgreSQL delete attacks passed for project, actor, AuditFinding, ImpactAssessment, and ImpactTarget dependencies. Foreign keys are `ON DELETE RESTRICT`; no scientific or governance cascade was added. Soft governance target locators intentionally have no FK and are validated at the Application boundary.
