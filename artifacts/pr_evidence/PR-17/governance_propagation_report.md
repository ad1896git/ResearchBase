# Governance Propagation Report

The GSAS-01 finding targets the exact original Run and stores its target content hash. Downstream impact retains
multi-path topology: the shared Run is deduplicated, while direct Measurement and StatisticalResult input paths
remain distinct. Validity precedence reports `invalid` for the active assessment.

The acceptance then transitions the finding to `dismissed` and verifies the validity projection becomes
`not_assessed` for that target. It verifies the ImpactAssessment target set, deterministic paths, CorrectionRecord
target identity, and preservation of original Measurement and StatisticalResult hashes.
