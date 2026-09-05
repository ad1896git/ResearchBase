# Immutability and Hash Invariance Report

The historical acceptance captures and compares fresh-read rows for Run, both Measurements, StatisticalResult,
frozen ClaimVersion, EvidenceRelation set, DatasetSnapshot, frozen ArtifactVersion, frozen MetricDefinitionVersion,
and historical ExperimentSpec/ResearchQuestion versions.

The original Run, Measurements, StatisticalResult, ClaimVersion, EvidenceRelation set, and DatasetSnapshot are
identical before and after later scientific advancement. Original ArtifactVersion, MetricDefinitionVersion, and
ExperimentSpec/ResearchQuestion historical IDs and content hashes remain present in history; only the legal
historical status transition to `SUPERSEDED` occurs where the domain requires it. No scientific row is updated by
CorrectionRecord creation.

PR-17R captures full material snapshots before and after later state for Run, Measurement, StatisticalResult,
ClaimVersion, EvidenceRelation, DatasetSnapshot, ArtifactVersion, MetricDefinitionVersion, and
ExperimentSpecVersion. The corrected test compares those rows through fresh reads and separately asserts exact
Measurement/StatisticalResult/Claim hashes and original reference IDs.
