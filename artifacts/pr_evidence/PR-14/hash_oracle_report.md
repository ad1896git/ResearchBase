# Hash oracle report

`tests/oracles/pr14_governance_hash_oracle.py` independently uses hashlib and canonical JSON, with no production material/hash-builder imports. Tests prove exact expected hashes, single-variable material-field sensitivity, insertion-order independence, excluded-metadata stability, and canonical key-order equivalence for ImpactAssessment and CorrectionRecord.
