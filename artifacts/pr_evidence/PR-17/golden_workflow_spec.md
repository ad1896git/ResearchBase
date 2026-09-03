# GSAS-01 Golden Scientific Acceptance Specification

GSAS-01 is the non-trivial chain:

`Project → ResearchQuestion → Hypothesis → ExperimentSpec → DatasetSnapshot + ArtifactVersion + MetricDefinitionVersion → Run → Measurement ×2 → StatisticalResult ×2 inputs → ClaimVersion + mixed Evidence → AuditFinding → ImpactAssessment → CorrectionRecord`.

The positive run freezes the research, hypothesis, experiment specification, artifact version, metric definition
version, and claim version. The run is started and finished successfully, then two Measurements are recorded.
The StatisticalResult has ordered `primary` and `replicate` inputs. Claim evidence contains one direct Measurement
relation and one StatisticalResult relation. The trace therefore traverses the StatisticalResult input edges,
deduplicates the shared Run, and retains each evidence path.

The workflow also queries run provenance, claim trace, claim closure, downstream impact, and validity projection.
It records a governance finding targeting the Run, an ImpactAssessment with direct and downstream targets, and a
CorrectionRecord whose target is the original Measurement.

The same semantic workflow is executed through direct Application, FastAPI, and Typer on independent fresh
PostgreSQL fixtures. Only transport metadata and independently generated transport request IDs are outside the
semantic projection.
