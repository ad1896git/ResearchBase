# Atomicity Report

The E2E atomicity test injects failure only through the accepted failing-UoW seam and verifies fresh PostgreSQL
reads after rollback. Representative StatisticalResult plus inputs, Claim evidence/freeze, ImpactAssessment,
and Run creation commands leave no partial rows. Retrying through the normal Application service produces exactly
the expected row/input count.

The test does not add a production fault hook, manual SQL repair, or persistence orchestration path.
