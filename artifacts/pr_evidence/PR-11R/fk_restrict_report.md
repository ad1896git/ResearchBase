# FK / RESTRICT report

The PostgreSQL behavioral FK tests attempted deletes against Project, Actor,
Measurement, and StatisticalResult with input rows. Every delete failed at the
database boundary. Fresh application reads verified the targeted parents,
StatisticalResult row, and exact input edges survived. No scientific FK was
changed to `ON DELETE CASCADE`.
