# Test report

Full suite completed against `postgresql+psycopg` PostgreSQL 18.6: 504 passed, 2 inherited skips.
The focused cache suite covers membership states, source boundary, valid scaling, one/multiple
missing Measurements, missing StatisticalResult, missing Run ArtifactVersion, never-requested ID,
fallback assertions, SELECT-only purity, exact diagnostics, and closure reuse.

The small fixture (one direct Measurement path, one StatisticalResult path, one unique Run) is an
explicit member of the SQL-count matrix and observed 15 SELECTs.

No SQLite result was used.
