# Historical Exactness Report

The historical acceptance completes GSAS-01, records the original material rows and hashes, creates later legal
ResearchQuestion, ExperimentSpec, DatasetSnapshot, ArtifactVersion, MetricDefinitionVersion, Run, Measurement,
and StatisticalResult state, then re-reads the original provenance, trace, closure, and impact through fresh
Application reads.

The exact original ExperimentSpecVersion, DatasetSnapshot, ArtifactVersion, MetricDefinitionVersion, Measurement
IDs, StatisticalResult input set with roles and ordinals, and ClaimVersion EvidenceRelation set remain unchanged.
Measurement `content_hash`, StatisticalResult `content_hash`, Claim `support_set_hash`, and Claim `content_hash`
remain unchanged. The original references are returned after later versions exist; no latest/current substitution
occurs.
