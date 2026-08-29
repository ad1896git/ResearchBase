# Immutability report

The PR-11 immutability triggers were preserved. The existing direct PostgreSQL
matrix continued to reject every StatisticalResult field UPDATE and every
post-create input INSERT/UPDATE/DELETE attack, with fresh reads preserving the
original row and input set.

The new zero-input guard is deferred and therefore does not reject the
legitimate parent-plus-input creation sequence. It rejects parent-only commits
at transaction end.
