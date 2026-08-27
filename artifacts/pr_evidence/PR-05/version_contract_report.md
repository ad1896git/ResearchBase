# Version contract report

`ExperimentSpecVersion` passes the reusable PR-03 version contract. DRAFT is editable; allowed transitions are DRAFT→FROZEN, DRAFT→ABANDONED, and FROZEN→SUPERSEDED. Reverse/terminal transitions and edits after freeze are rejected with stable errors. Frozen and superseded objects require hash, scheme, and UTC frozen timestamp.
