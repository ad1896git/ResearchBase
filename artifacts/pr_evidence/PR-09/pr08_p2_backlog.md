# Inherited PR-08 P2 backlog

The following accepted PR-08 P2 findings remain recorded and were not silently changed by PR-09:

1. `MetricDefinitionModel.current_version_id` lacks explicit ORM ForeignKey metadata although the migration FK exists.
2. PR-08 evidence reported an imprecise range/count.

Neither blocks Run Core correctness.

