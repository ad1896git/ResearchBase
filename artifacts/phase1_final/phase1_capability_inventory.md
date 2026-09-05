# Phase 1 capability inventory

Observed at accepted HEAD `5fe5dd90310d68d6df1683307f0d24dd2233c3dd`. This is a repository surface inventory, not a design-conformance review. Counts below are the accepted adapter inventories, corroborated by the full fresh suite.

| Surface | Present capability | Repository evidence / location |
|---|---|---|
| Foundation / Domain | Typed IDs, execution context, canonical JSON/hashes, version lifecycle contracts, repository/UoW ports; actors/projects/workspaces. | src/researchbase/foundation/; src/researchbase/domain/; src/researchbase/application/ports.py |
| Scientific entities | ResearchQuestion, Hypothesis, ExperimentSpec and MetricDefinition version lifecycle; DatasetSnapshot and ArtifactVersion identities; local content-addressed artifact storage. | src/researchbase/domain/research.py; experiment.py; metric.py; artifact.py; src/researchbase/foundation/artifact_store.py |
| Application | Scientific command/query handlers, frozen DTO read models and transaction orchestration. | src/researchbase/application/commands.py; dto.py; ports.py |
| Runs and results | Run input sealing, lifecycle and closure; immutable Measurements, StatisticalResult and typed ordered inputs; frozen ClaimVersion and EvidenceRelation. | src/researchbase/domain/run.py; measurement.py; statistical_result.py; claim.py; evidence.py; src/researchbase/application/closure.py |
| Infrastructure / PostgreSQL | Synchronous SQLAlchemy/psycopg persistence, repositories, UoW, DB constraints/triggers and migrations 0001 through 0015. | src/researchbase/persistence/; migrations/versions/ |
| Provenance query service | Run provenance/input traces, Claim-to-Run traces and closure reports, historical frozen references and bounded batched reads. | src/researchbase/application/provenance_queries.py; tests/architecture/test_pr13r_batched_reads.py |
| Governance | AuditFinding, ImpactAssessment/ImpactTarget, CorrectionRecord, downstream impact and validity projections. | src/researchbase/domain/governance.py; src/researchbase/application/governance.py; governance_queries.py |
| FastAPI adapter | 35 accepted /v1 operations, request context, strict DTO validation, finite error mapping and read serialization; direct Application calls. | src/researchbase/api/; artifacts/pr_evidence/PR-15/route_inventory.md; artifacts/pr_evidence/PR-15R/ |
| Typer CLI adapter | 14 groups and 35 accepted commands, JSON output/error contracts, direct Application calls and execution context propagation. | src/researchbase/cli/; artifacts/pr_evidence/PR-16/command_inventory.md |
| Golden Scientific Acceptance Suite | Golden scientific workflow; cross-adapter projections; historical exactness; immutability, governance propagation, closure, concurrency, atomicity, failure recovery and SQL shape. | tests/e2e/; artifacts/pr_evidence/PR-17R/ |
| Agent-ready architecture guards | Transport-independent Domain/Application, adapter independence, frozen ORM-free DTOs, controlled persistence boundary and absence of agent/workflow implementation. | tests/architecture/test_pr17_agent_ready_architecture.py; tests/architecture/ |
| Phase 1 exit evidence | Final remediation subject/evidence protocol, closed P0/P1/P2 findings, clean-install and repeated-run historical evidence, exit summary. | artifacts/pr_evidence/PR-17R/phase1_exit_summary.md; clean_install_report.md; repeated_run_report.md; finding_disposition.md |

Source and migration inspection found no DecisionRecord, Approval*, Agent runtime, workflow engine, background worker, PR-18 implementation or Phase 2+ implementation. Negative strings in architecture tests are guards, not implementations. Future architecture/execution documents do not count as implemented capability.

All tracked architecture/e2e paths and all 15 migration paths are recorded in [raw/architecture_surface.json](raw/architecture_surface.json). Full-suite collection contains all those tests. No capability or schema was added by consolidation.
