# Broken-Descendant Closure Report

The corrected negative case creates a valid frozen Claim graph, then uses a controlled raw PostgreSQL setup to
make the original MetricDefinitionVersion descendant invalid while keeping the root and descendant rows present.
The Claim closure validator is called three times through fresh accepted reads.

Each run returns exactly three ordered `VERSION_NOT_FROZEN` violations, all with message
`metric definition version is not finalized`, `visited_count=14`, and `complete=false`. The paths are stable and
identify the two StatisticalResult input Measurements followed by the direct Measurement evidence relation:

1. `claim_version/evidence/<statistical-result-evidence>/statistical_result/inputs/<measurement-0>/measurement/metric_definition_version/status`
2. `claim_version/evidence/<statistical-result-evidence>/statistical_result/inputs/<measurement-1>/measurement/metric_definition_version/status`
3. `claim_version/evidence/<measurement-evidence>/measurement/metric_definition_version/status`

The positive Claim and Run closure cases still pass. No raw exception is returned, and the repeated violation code,
paths, visited count, and ordering are identical.
