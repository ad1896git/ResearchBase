# Evidence reconciliation

The original PR-09 evidence is retained and explicitly corrected rather than erased:

- race evidence now states the original tests lacked deterministic synchronization;
- transaction evidence now states create/artifact rollback was not originally proven;
- input-sealing evidence now records the OLD/NEW retarget bypass and its 0009 fix;
- closure evidence now distinguishes the original single complete case from the new multiple-invalid-closure test;
- FK evidence now distinguishes the original Run-only behavior from the complete six-target matrix;
- formatting ownership is corrected from 13 to 14 baseline Python files;
- `changed_files.txt` and command/result counts are identified by explicit Git ranges.
