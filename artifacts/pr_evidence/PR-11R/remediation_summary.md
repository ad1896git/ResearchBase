# PR-11R remediation summary

PR-11R closes exactly F-001 through F-007 on top of the reviewed PR-11 HEAD
`9592b66dc3372fae18fdd66555203f0788e407e2`.

Implementation/test commits:

- `6319fda` — deferred PostgreSQL zero-input guard, duplicate-edge translation,
  and regression coverage;
- `1330419` — corrected PR-11R regression import/type details;
- `4aa969e` — strengthened fresh rollback counts and independent hash-order proof.

The accepted PR-11 implementation and evidence history were preserved. The
only production change is the narrow repository error translation and the only
new schema migration is `0012_statistical_result_input_guard`; `0011` was not
rewritten. No PR-12 or later implementation was added.
