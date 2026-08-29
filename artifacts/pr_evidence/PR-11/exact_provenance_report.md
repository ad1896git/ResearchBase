# Exact provenance report

The input table stores the exact `measurement_id` supplied to the command.
After a StatisticalResult was created against Measurement M1, a later
Measurement M2 was created for the same project. A fresh query still returned
only M1, and the StatisticalResult row and content hash were unchanged.

No current/latest Measurement lookup is used by the read path. The persisted
foreign key is the historical provenance edge.
