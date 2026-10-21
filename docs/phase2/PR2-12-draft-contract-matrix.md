# PR2-12 conditional draft slice — frozen scope

Base `088bb8868648c853e8c321321f7aba799ef23c12`.

| Authority | Requirement | Slice test |
| --- | --- | --- |
| Phase 2 spec §§16, 48 PR2-12; field contract §Publication | Publication is project-owned identity with typed publication kind, DRAFTING lifecycle, optional same-parent current manuscript pointer and version counter | Create/read, wrong project and unauthorized write rejection; direct SQL wrong-parent pointer rejected. |
| Phase 2 spec §16.2; field contract `manuscript_versions` | ManuscriptVersion belongs to one Publication, has a unique positive version number, typed DRAFT state and exact document ArtifactVersion FK | Create/read/restart; missing, foreign, wrong-kind and unfrozen document rejected. |
| Phase 2 field contract §Shared physical rules | Every row with `content_hash`, including a DRAFT row with a NULL digest, stores the constrained `hash_scheme='sha256-cjson-v1'` physical column | Fresh and 0018 upgrade schema inventory; no extra semantic digest. |
| Phase 2 spec §40; Cross-Phase frozen provenance | A draft cannot claim scientific closure or READY status; frozen version material and placement hashes are a later explicit transition | Hashes and `frozen_at` remain NULL; no implicit freeze, placement, promotion, review, decision or approval. |
| Phase 2 R2 hash contract, R3 targeted vectors | Frozen manuscript hashes have exact literal payloads and placement closure | **Out of this slice**: no freeze command or material hash is produced. PR2-13 placement implementation and a later reviewed freeze slice must implement these before formal PR2-12 acceptance. |
| Phase 2 spec §47 dependency graph and PR2-09 | PR2-09 official STORM adapter is SHOULD and may be deferred; PR2-11 accepted conditional ScientificConclusion is in ancestry | Development independent of PR2-09; formal milestone admission remains blocked by M3 Human Gate and downstream review gates. |

Only the frozen contract's `publications`, `publication_lifecycle_events` and
`manuscript_versions` tables/fields may be added. The draft command accepts
an existing exact FROZEN manuscript document ArtifactVersion in the same
Project. It does not produce a scientific placement or formal manuscript.
Request replay uses a deterministic UUID derived from the verified deployment,
project, actor, command, parent and request UUID; a changed payload under the
same identity conflicts. A transaction-scoped advisory lock serializes exact
replays. No separate receipt table or unlisted semantic column is persisted.
The command returns its result from the same Unit of Work that commits the
draft; no post-commit read can turn a successful write into a reported failure.
Empty-table downgrade locks all new tables before testing for retained rows.
All write tests use only newly created disposable PostgreSQL 55442 databases.
