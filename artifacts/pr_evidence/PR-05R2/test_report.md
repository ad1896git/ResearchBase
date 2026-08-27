# Test report

PR-05R2 adds three independent domain tests: status changes from FROZEN to SUPERSEDED without changing the material hash, two aware UTC frozen_at values produce the same hash, and two ExperimentSpec identities with different current pointers produce the same hash for equivalent version material. Existing six-field sensitivity and all prior regression tests remain green.

Fresh totals: 185 pytest, 47 PostgreSQL integration, 27 architecture.
