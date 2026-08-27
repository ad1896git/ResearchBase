# Exact provenance and closure report

The regression binds exact immutable references and then advances their
owners. It reads the final Run and input edges through fresh application
UoWs; it never resolves an identity current pointer while validating the Run.

- ExperimentSpec: V1 is frozen and bound to the Run. Revising the identity
  creates V2 and makes V1 `SUPERSEDED`; the Run still references the exact
  `spec_v1.id`, and closure remains complete.
- Artifact: A1 is frozen and attached. Creating and freezing A2 advances the
  identity and makes A1 `SUPERSEDED`; the Run still references exact
  `artifact_a1.id`, and closure remains complete.
- Dataset: D1 is attached. Creating later D2 for the same Dataset does not
  alter the Run edge, which remains exact `dataset_d1.id`.

The same Run is checked while PLANNED, after successful start as RUNNING, and
after successful finish as terminal; all closure checks remain complete after
spec/artifact supersession. Separate negative tests prove DRAFT and ABANDONED
exact references are invalid and that new authoring remains FROZEN-only.

Test: `test_finalized_superseded_exact_refs_remain_closure_valid_and_startable`
plus the adjacent superseded-authoring and abandoned-reference tests in
`tests/integration/test_pr09r2_proof.py`.
