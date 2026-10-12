# PR2-10 exact transcript binding — feasibility gate

Accepted base `daa2e72f7ea12cf723cf97fbfe68c89cf4f5ad19`. This document
precedes production code. Rejected `4aacb86` is diagnostic only.

| Frozen authority | Required invariant | Existing representation | Database enforcement / test |
|---|---|---|---|
| Phase 2 spec §14, lines 553–569; §26, lines 970–985; PR2-10, lines 1707–1711 | A CLOSED discussion yields a transcript ArtifactVersion; a generated candidate is not a scientific promotion | Sealed session, typed ordered input/turn/citation rows; ArtifactVersion | Exact byte hash must match those rows; promotion stays explicitly denied. Valid bind and no-promotion tests. |
| Phase 2 field contract §Shared physical rules, lines 8–10, §Discussion line 40 | Only `transcript_artifact_version_id UUID NULL` may add binding semantics to `discussion_sessions`; exact FK RESTRICT, same-project/frozen checks | Existing `discussion_sessions`, `artifact_versions`, `artifacts` | Add only the authorized nullable FK and index. No persisted digest, metadata reference or other semantic field. Schema inventory test. |
| Accepted deterministic candidate `discussion_artifacts.py` lines 125–174 and canonical JSON v1 | Bound version's `content_hash` must equal SHA-256 of the exact canonical transcript bytes derived from this session, not merely any same-project transcript | Existing `artifact_versions.content_hash`, sealed discussion rows | A PostgreSQL trigger recomputes the exact canonical bytes from existing rows and compares `encode(sha256(convert_to(payload,'UTF8')),'hex')` with the referenced immutable content hash. Invalid direct SQL update must roll back. |
| Artifact migration 0006, lines 34–95; Phase 2 field contract line 74 | Referenced version is FROZEN at binding, `discussion_transcript` kind, same project, JSON media type; frozen material and history are retained | `artifact_versions` and parent `artifacts` | Trigger locks both rows `FOR SHARE`, checks status/kind/project/hash; FK RESTRICT and frozen-version guard prevent later material substitution/deletion. Wrong type/project/version and delete/update tests. |
| Phase 2 field contract line 74; accepted PR2-10 persistence | One authenticated Application command/transaction, idempotent request receipt; concurrent bind cannot replace pointer | Existing receipt table, project/session locks, row version | Extend existing receipt CHECK to BIND_TRANSCRIPT, serialize under session row lock; trigger accepts only CLOSED NULL→one exact version. Replay/concurrency/rollback/restart tests. |

The SQL payload must use the fixed Python `sort_keys=True`, compact UTF-8
field order, ordered typed relations and `format_utc` timestamp spelling.
PostgreSQL 18's core `sha256(bytea)` is available on the approved 55442 test
instance. Read-only synthetic checks confirmed `to_json(text)::text` matches
Python `json.dumps(..., ensure_ascii=False, separators=(',',':'))` for
database-storable ASCII escapes, Unicode, line controls and emoji. The test
suite must compare full SQL and Python candidate hashes for adversarial
storable text and microsecond timestamps; unsupported states fail closed.

**Decision:** CONTRACT_COMPLIANT design is feasible with one contract-listed
FK column plus database constraints/functions; no new persisted hash field.
Direct SQL with an arbitrary reference fails because the trigger derives the
hash independently from sealed rows. A direct write of the *correct* exact
version is referentially valid but does not grant Application authorization or
promotion authority. The database cannot inspect CAS bytes; existing
ArtifactVersion creation and Application readback verify the CAS against the
immutable stored hash. In-scope tests must prove this distinction.

Downgrade must refuse whenever any binding pointer or BIND_TRANSCRIPT receipt
exists, before dropping the authorized FK; no session history is rewritten.
