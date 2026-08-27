# Version contract

MetricDefinitionVersion is directly adapted to `tests.contracts.version_contract.assert_version_contract`. The shared lifecycle permits DRAFT→FROZEN/ABANDONED and FROZEN→SUPERSEDED, rejects reverse/same-state transitions, and protects frozen/superseded material.
